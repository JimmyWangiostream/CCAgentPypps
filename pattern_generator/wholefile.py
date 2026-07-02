"""Stage 3 — whole-file (coherent) authoring prompt.

Replaces per-unit fragment generation + blind text-assembly with ONE prompt that
asks the model to author the COMPLETE pattern in a single coherent pass: it sees
every step, the self.* data-flow contract, a worked idiom per operation, and the
rule pack. This restores global coherence (helper extraction, cross-step asserts,
consistent threading) that the fragmented pipeline could not achieve — while the
Stage-1 gate + Stage-2 review back it up.

Granularity note (plan): method STRUCTURE stays fine (loop = deterministic wrapper +
small per-substep helpers); only the AUTHORING PASS is coarse. For very large
patterns, `units` can be sliced into sub-phase batches (build_wholefile_prompt over
a subset, sharing already-written upstream) — the file is still validated as a whole.

Deterministic + stdlib; the authoring itself is the LLM step.
"""
from __future__ import annotations

import json

from pattern_generator.api_grounding import NAMESPACE_RULE
from pattern_generator.stepwise import generation_units, build_scaffold
from pattern_generator.rules import select_refs, format_refs
from pattern_generator.idioms import find_idiom, format_idiom
from pattern_generator.review import _ir_terms
from pattern_generator.prepare import _unit_query


WHOLEFILE_INSTRUCTIONS = """\
You are a UFS pattern generator. Author the COMPLETE pattern file in ONE coherent
pass — every method, in one class, consistent throughout.

HARD RULES (the validator + review gate enforce these):
- EVERY stepN / helper MUST be a method INSIDE the pattern class. Never put a method
  at module level or after the `if __name__` guard (process() would never run it).
- Fill the scaffold markers; emit the COMPLETE file in one ```python block.
- Thread data between steps via self.<var> per the DATA-FLOW CONTRACT. A step that
  CONSUMES a var must READ self.<var>, not re-derive it (e.g. never re-random an LBA
  that an earlier write produced — reuse self.write_lba / self.write_record).
- A loop phase = a deterministic wrapper stepN containing the `for` loop, calling one
  small helper per sub-step (`_loopN_step_x_y(self, loop_idx)`); do NOT inline a 150-
  line method. Factor duplicated reset logic into ONE `_perform_reset` helper.
- For EVERY step, implement it AND enforce its expected/fail_condition with
  `raise api.PATTERN_ASSERT_*` — never just log (logging a check = silent false pass).
- Ground each API call on the worked IDIOMS below; confirm exact signatures by reading
  GitNexusMCP/Script source if unsure. Follow the RULE PACK.

""" + NAMESPACE_RULE


def _dataflow_contract(units: list) -> str:
    rows = ["## Data-flow contract (thread via self.*)"]
    for u in units:
        prod = u.get("set_vars") or []
        cons = u.get("consumes") or []
        if not prod and not cons:
            continue
        parts = []
        if prod:
            parts.append("produces self." + ", self.".join(prod))
        if cons:
            parts.append("consumes self." + ", self.".join(cons))
        rows.append(f"- {u.get('method')}: " + "; ".join(parts))
    return "\n".join(rows) if len(rows) > 1 else ""


def _unit_plan(units: list) -> str:
    rows = ["## Unit plan (one method each, in order)"]
    for u in units:
        kind = u.get("kind")
        note = {"loop_wrapper": "  [the for-loop wrapper; calls the sub-step helpers]",
                "loop_substep": "  [one loop sub-step helper (self, loop_idx)]"}.get(kind, "")
        steps = u.get("steps") or []
        name = steps[0].get("name", "") if steps else ""
        rows.append(f"- {u.get('method')} — {name}{note}")
    return "\n".join(rows)


def _idiom_anchors(units: list, script_root) -> str:
    """One worked idiom per DISTINCT operation across the pattern."""
    seen: set = set()
    blocks: list = []
    for u in units:
        q = _unit_query(u).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        idiom = find_idiom(q, script_root)
        if idiom:
            blocks.append(f"### {q}\n{format_idiom(idiom)}")
    if not blocks:
        return ""
    return "## Worked idioms (anchor each call here; confirm signatures in source)\n" + \
        "\n\n".join(blocks)


def build_wholefile_prompt(ir: dict, script_root, scaffold: str | None = None,
                           defaults: str = "") -> str:
    units = generation_units(ir)
    scaffold = scaffold if scaffold is not None else build_scaffold(ir)
    refs = select_refs("", _ir_terms(ir))

    parts = [WHOLEFILE_INSTRUCTIONS,
             f"Pattern: {ir.get('pattern_id')} — {ir.get('title', '')}",
             _unit_plan(units)]

    if defaults.strip():
        parts.append(
            "## Project defaults (default.md) — when the TC OMITS a detail, FOLLOW these "
            "(UserPrompt > ModelDefault). Do NOT hardcode a value these resolve (e.g. lun=0). "
            "Tag any use as `# src[wiki]: default.md`.\n" + defaults.strip())

    contract = _dataflow_contract(units)
    if contract:
        parts.append(contract)

    anchors = _idiom_anchors(units, script_root)
    if anchors:
        parts.append(anchors)

    parts.append("## Review references (obey)\n" + format_refs(refs))
    parts.append("## Scaffold — fill the markers, output the COMPLETE file\n"
                 "```python\n" + scaffold.rstrip() + "\n```")
    parts.append("## Full IR (for reference)\n```json\n"
                 + json.dumps(ir, ensure_ascii=False, indent=2) + "\n```")
    return "\n\n".join(parts)
