# Agent Workflow — TC → IR → Pattern (.py)

The deterministic stages are Python; the LLM steps are performed by the current
model (no API key). Every artifact for one pattern lands in `generated/<PATTERN_ID>/`.

1. `python generate_pattern.py prepare-ir TC/<file>.md`
   → writes `generated/<ID>/ir_skeleton.json` + `enrich_prompt.txt`.

2. **LLM step A — annotate data flow.** Read `enrich_prompt.txt`, write the
   annotations to `generated/<ID>/annotations.json`:
   `{"phases":[{phase_id,inputs,outputs}],"edges":[{from,to,type,data_flow}]}`.

3. `python generate_pattern.py finalize-ir generated/<ID>/ir_skeleton.json generated/<ID>/annotations.json`
   → writes `<id>-ir.json` + `<id>-ir-debug.md` in the folder.

4. `python generate_pattern.py prepare generated/<ID>/<id>-ir.json`
   → writes `scaffold.py` (class skeleton + markers), `1_units.json` (the ordered
   generation **unit** plan — one stepN per step, a loop phase → wrapper + per-substep
   helpers), `_run_meta.json`, and only the FIRST unit's `unit_01_*_prompt.txt`.

5. **LLM step B — generate, one UNIT at a time.** For each unit k:
   `python generate_pattern.py prepare-unit generated/<ID>/ k` builds
   `unit_kk_*_prompt.txt` (embeds upstream units for continuity). Read it and write
   `unit_kk_*_methods.py` (sections `=== WIKI REFS / CODE REFS / REVIEW FLAGS /
   EXTRA IMPORTS / METHODS ===`, exactly one `stepN`/helper). Loop-wrapper units are
   deterministic — `prepare-unit` reports "skip"; do NOT hand-write them. Ground each
   call against code (gitnexus `query`/`context`, or `--grounding direct`) + the
   injected wiki essence; tag inline `# src[code]:` / `# src[wiki]:`.

6. `python generate_pattern.py assemble generated/<ID>/ <PatternName>`
   → injects the `unit_*_methods.py` into the scaffold → `<PatternName>.py` (+ `retrieval_debug.md`).

7. `python generate_pattern.py finish generated/<ID>/<PatternName>.py generated/<ID>/<id>-ir.json`
   → the **gate loop**: validates (`syntax`/`structure`/`dataflow`/`api_grounding`).
   On **FAIL** it writes `<id>_repair_prompt.txt` (the validator's concrete findings +
   the review prompt) — read it, rewrite the WHOLE `.py`, re-run `finish` (bounded by
   `--max-rounds`). On **PASS** it writes `<id>_review_prompt.txt` for one rule-level
   pass (a structural pass is NOT rule-clean). All gate by-products + the append-only
   history live in `gate_logs/` (`<id>.gate_log.md`).

`generated/<ID>/` holds the pattern artifacts (ir_skeleton, annotations, IR (+debug),
`1_units.json`, scaffold, per-unit prompts/methods, the `.py`); `gate_logs/<id>.gate_log.md`
holds the run-by-run fail-point history. `python generate_pattern.py rules` lists the
pitfall checklist.

## Output files — order, producer, meaning

Files in `generated/<PATTERN_ID>/`, in creation order. Steps alternate between
deterministic Python (CLI) and LLM (current model):

| # | File | Produced by | Kind | What it is |
|---|------|-------------|------|-----------|
| 1 | `ir_skeleton.json` | `prepare-ir` | Python | Parsed TC skeleton (phases/steps) + wiki chapter refs. No data flow yet. |
| 2 | `enrich_prompt.txt` | `prepare-ir` | Python | Prompt asking the model for each phase's inputs/outputs/data_flow. |
| 3 | `annotations.json` | **LLM step A** | LLM | Data-flow annotation the model produces from (2). |
| 4 | `<id>-ir.json` | `finalize-ir` | Python | **Final IR** = skeleton (1) + annotations (3). The input to generation. |
| 5 | `<id>-ir-debug.md` | `finalize-ir` | Python | Human-readable IR report (phase table, loop/fail_condition, data flow). |
| 6 | `scaffold.py` + `1_units.json` | `prepare` | Python | Class skeleton (markers) + the ordered generation **unit** plan (topological; loop → wrapper + per-substep helpers). |
| 7 | `unit_NN_*_prompt.txt` | `prepare` / `prepare-unit` | Python | Per-unit generation prompt (wiki essence + `self.*` contract + upstream continuity). |
| 8 | `unit_NN_*_methods.py` | **LLM step B** | LLM | Per-unit output: one `stepN`/helper + `=== CODE/WIKI REFS ===` provenance. |
| 9 | `<PatternName>.py` + `retrieval_debug.md` | `assemble` | Python | The merged pattern + per-unit grounding/flag report. |
| 10 | `gate_logs/<id>.gate_log.md` (+ `_repair/_review_prompt.txt`) | `finish`/`validate` | mixed | Append-only fail-point history + the gate loop's prompts. |

Three groups: **IR stage** (1-5, "what the pattern must do") · **generation stage**
(6-9, "how to build it from real code, unit by unit") · **gate/traceability** (5 debug,
9 retrieval_debug, 10 gate log — "what failed, where grounding came from").

Debug entry points: wrong API in a step → inline `# src[...]` in the .py +
`retrieval_debug.md`; IR data-flow/loop wrong → `<id>-ir-debug.md`; unit order/phase
deps → `1_units.json`; what the model saw → `unit_NN_*_prompt.txt`; why a gate failed →
`gate_logs/<id>.gate_log.md`.
