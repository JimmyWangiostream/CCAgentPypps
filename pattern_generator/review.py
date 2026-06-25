"""Stage 2 — internalised review→repair pass.

Builds the deterministic prompt that drives an LLM review of an assembled pattern
against (a) the IR checkpoints (every step's expected / fail_condition must be
implemented AND asserted) and (b) the prescriptive rule pack (rules.py). The LLM
then emits a corrected full file, which is re-run through the Stage-1 validate()
gate. This is the single highest-leverage fix (plan RC5): the pipeline finally
reviews its own output with global context instead of relying on an external agent.

Deterministic + stdlib; the review itself is the LLM step (like the other LLM
steps in this pipeline).
"""
from __future__ import annotations

import json

from pattern_generator.rules import select_rules, format_rules


def _checkpoints(ir: dict) -> list:
    """(step_id, name, expected, fail_condition, on_fail) for steps that assert
    something — these are the checkpoints the code MUST implement and enforce."""
    rows = []
    for phase in ir.get("phases", []):
        for st in phase.get("steps", []):
            exp = (st.get("expected") or "").strip()
            fc = (st.get("fail_condition") or "")
            if exp or fc:
                rows.append((st.get("step_id"), st.get("name", ""), exp,
                             (fc or "").strip(), st.get("on_fail")))
    return rows


def _ir_terms(ir: dict) -> tuple:
    """Lower-cased operation tokens from the IR, for rule selection."""
    terms: list = []
    for phase in ir.get("phases", []):
        for st in phase.get("steps", []):
            for key in ("scsi_cmd", "ufs_query", "name", "idn"):
                v = st.get(key)
                if v:
                    terms.append(str(v).lower())
    return tuple(terms)


REVIEW_INSTRUCTIONS = """\
You are reviewing a generated UFS test pattern for CORRECTNESS, with the WHOLE
file in view. Two obligations:

1. CHECKPOINT COMPLIANCE — for EVERY checkpoint below, the code must (a) implement
   the step and (b) ENFORCE its expected/fail_condition with `raise api.PATTERN_ASSERT_*`
   (or assert). A checkpoint that is only logged, or missing, is a defect.
2. RULE PACK — fix every violation of the prescriptive rules below (protocol path,
   volatile-flag asserts, exception naming, write/read lba reuse, reset helper, …).

Also apply global refactors the per-method generator could not: factor duplicated
reset blocks into one `_perform_reset` helper, thread shared state via self.*,
keep every stepN/helper INSIDE the class.

OUTPUT: emit the COMPLETE corrected file in one ```python block, ready to write
over the original. If nothing needs changing, re-emit it unchanged and add a final
comment `# REVIEW: no defects found`. Do not output a diff or partial methods."""


def build_review_prompt(pattern_src: str, ir: dict, rules=None) -> str:
    """Assemble the review prompt: instructions + checkpoints + rules + the code."""
    rules = rules if rules is not None else select_rules(pattern_src, _ir_terms(ir))

    parts = [REVIEW_INSTRUCTIONS,
             f"Pattern: {ir.get('pattern_id')} — {ir.get('title', '')}"]

    cps = _checkpoints(ir)
    if cps:
        lines = ["## Checkpoints (must be implemented AND asserted)"]
        for sid, name, exp, fc, on_fail in cps:
            row = f"- {sid} ({name}): expected = {exp or '—'}"
            if fc:
                row += f"; fail_condition = {fc}"
            if on_fail:
                row += f"; on_fail = {on_fail}"
            lines.append(row)
        parts.append("\n".join(lines))

    parts.append("## Prescriptive rules (fix every violation)\n" + format_rules(rules))
    parts.append("## Current pattern source (review & correct the WHOLE file)\n"
                 "```python\n" + pattern_src.rstrip() + "\n```")
    return "\n\n".join(parts)
