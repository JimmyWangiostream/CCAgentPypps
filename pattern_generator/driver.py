"""Stage 1->2 gate driver — chains validate (Stage 1) and review->repair (Stage 2)
into one loop the generating model drives to convergence.

Each `finish` run is one turn of the loop:
  * validate the file (structural/dataflow/api gate);
  * if it FAILS, emit a repair prompt = the validator's concrete findings PLUS the
    Stage-2 review prompt (checkpoints + rule pack + code) — the model rewrites the
    whole file and re-runs `finish` (bounded by --max-rounds);
  * if it PASSES, emit the Stage-2 review prompt for one rule-level pass (a structural
    pass is not rule-clean — see the cc.py demo where 5 volatile-flag checks only
    logged), then the model can accept or do one more pass.

Deterministic + stdlib; the rewrite itself is the LLM step (like the rest of the
pipeline). Round state persists in <stem>_gate_state.json.
"""
from __future__ import annotations

from pattern_generator.validator import validate
from pattern_generator.review import build_review_prompt

_GATE_KEYS = ("syntax", "structure", "dataflow", "api_grounding")


def gate_failures(report: dict) -> dict:
    """The gate dimensions that did NOT pass (skipped / pass are fine)."""
    fails = {}
    for k in _GATE_KEYS:
        v = report.get(k)
        if v not in ("pass", "skipped", None):
            fails[k] = v
    return fails


def _findings_block(fails: dict) -> str:
    lines = ["## Validator findings — FIX EVERY ONE (deterministic gate; non-negotiable)"]
    for k, v in fails.items():
        if isinstance(v, list):
            for m in v:
                lines.append(f"- [{k}] {m}")
        else:
            lines.append(f"- [{k}] {v}")
    return "\n".join(lines)


def build_repair_prompt(pattern_src: str, ir: dict, report: dict, defaults: str = "") -> str:
    """Repair prompt = concrete validator findings + the Stage-2 review prompt."""
    fails = gate_failures(report)
    parts = []
    if fails:
        parts.append(_findings_block(fails))
    parts.append(build_review_prompt(pattern_src, ir, defaults=defaults))
    return "\n\n".join(parts)


def run_gate(pattern_src: str, ir: dict, script_root=None) -> dict:
    """Validate and return (report, failures)."""
    report = validate(pattern_src, ir, script_root=script_root)
    return {"report": report, "failures": gate_failures(report)}
