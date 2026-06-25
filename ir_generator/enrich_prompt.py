"""Agent-driven IR enrichment: build the prompt (deterministic) and apply the
model's annotations back into the IR. No LLM SDK call — the current Claude Code
model reads the prompt and returns annotations."""

ENRICH_INSTRUCTIONS = """You are a UFS test architecture expert. Given a UFS test
pattern skeleton and relevant UFS spec excerpts, identify the data flow at BOTH
the phase level and the individual step level.

1. Phase level:
   a. What data variables each phase produces as outputs
   b. What data variables each phase needs as inputs
   c. The data_flow on each sequential edge between phases
2. Step level (CRITICAL — used to generate each step independently):
   For EVERY step, list:
   a. produces: variables this step computes/reads that a LATER step (or downstream
      phase) will need (e.g. step reads READ CAPACITY -> produces ["max_lba"]).
   b. consumes: variables this step needs that an EARLIER step produced
      (e.g. WRITE DESCRIPTOR consumes ["max_alloc_units", "config_descriptor_data"]).

Rules:
- Variables are snake_case (e.g. boot_lun_id, max_lba, write_pattern).
- A step that neither passes data forward nor needs upstream data has produces: []
  and consumes: [] (e.g. TEST UNIT READY is usually independent).
- Be precise: only list a variable in consumes if some earlier step actually
  produces it. Phase outputs must be the union of their steps' produces that cross
  the phase boundary.
- Respond with ONLY valid JSON of this exact shape:
{
  "phases": [
    {"phase_id": "...", "inputs": [...], "outputs": [...],
     "steps": [{"step_id": "...", "produces": [...], "consumes": [...]}]}
  ],
  "edges": [{"from": "...", "to": "...", "type": "sequential", "data_flow": [...]}]
}"""


def build_enrich_prompt(skeleton: dict, wiki_refs: dict) -> str:
    lines = [ENRICH_INSTRUCTIONS, "",
             f"Pattern: {skeleton['pattern_id']} — {skeleton['title']}", ""]
    # Conflict-resolved overrides from the ingested llm-wiki (highest authority), shown once.
    for ref in wiki_refs.get("__conflicts__", []):
        lines += [f"## {ref['title']}", ref["excerpt"], ""]
    lines += ["## Phase Skeleton", ""]
    for phase in skeleton["phases"]:
        lines.append(f"### {phase['phase_id']}: {phase['name']} (type={phase['type']})")
        if phase.get("loop_count"):
            lines.append(f"  loop_count: {phase['loop_count']}")
        for step in phase["steps"]:
            cmd = step.get("scsi_cmd") or step.get("ufs_query") or "—"
            lines.append(f"  - {step['step_id']}: {step['name']} [{cmd}]")
            lines.append(f"    expected: {step['expected']}")
        refs = wiki_refs.get(phase["phase_id"], [])
        if refs:
            lines.append(f"\n  ## Relevant Wiki ({len(refs)} ingested pages)")
            for ref in refs[:3]:
                lines.append(f"  ### {ref['title']}")
                lines.append(ref["excerpt"][:800])
        lines.append("")
    return "\n".join(lines)


def _merge_step_dataflow(phase: dict, annotated_phase: dict) -> list[dict]:
    """Merge step-level produces/consumes from the annotation onto each step dict.
    Steps absent from the annotation keep their existing (default []) values."""
    step_ann = {s.get("step_id"): s for s in annotated_phase.get("steps", [])}
    merged = []
    for step in phase.get("steps", []):
        ann = step_ann.get(step.get("step_id"), {})
        merged.append({
            **step,
            "produces": ann.get("produces", step.get("produces", [])),
            "consumes": ann.get("consumes", step.get("consumes", [])),
        })
    return merged


def apply_annotations(skeleton: dict, annotations: dict, wiki_refs: dict) -> dict:
    annotated = {p["phase_id"]: p for p in annotations.get("phases", [])}
    phases = [
        {**phase,
         "inputs":  annotated.get(phase["phase_id"], {}).get("inputs", []),
         "outputs": annotated.get(phase["phase_id"], {}).get("outputs", []),
         "steps":   _merge_step_dataflow(phase, annotated.get(phase["phase_id"], {}))}
        for phase in skeleton["phases"]
    ]
    return {
        **skeleton,
        "phases": phases,
        "dependency_graph": {
            "nodes": [p["phase_id"] for p in phases],
            "edges": annotations.get("edges", []),
        },
        "_wiki_refs": wiki_refs,
    }
