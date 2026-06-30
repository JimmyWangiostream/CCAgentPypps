"""Per-unit deterministic gate — the SAME checks `finish` runs on the whole file, run
on ONE unit's methods right after it is generated.

The pipeline generates each unit independently (Step 5), but the deterministic checks
(api_grounding / semantic / citation) historically ran only at `finish`, on the assembled
file — so a unit's bug was caught a whole file later, with the cheapest, most-local context
already gone. `check_unit` shifts those exact checks left to the unit, so the workflow can
rewrite just that unit before moving on. Pure reuse — no new check logic.
"""
from __future__ import annotations

from pattern_generator.api_grounding import (
    check_api_calls, check_citations, check_struct_fields, format_issues,
)
from pattern_generator.semantic_checks import check_semantics


def check_unit(methods_text: str, code_refs=None, script_root=None, index=None) -> dict:
    """Run the per-unit checks on one unit's `=== METHODS ===` body + its `=== CODE REFS ===`.

    Returns {api, semantic, citation} -> list[str] findings (empty list = clean for that
    dimension). `methods_text` is the class-body-indented method source; it is wrapped in a
    dummy class so the AST parses. `index` (a prebuilt api_grounding index) may be passed to
    avoid rebuilding it per unit; otherwise it is built from `script_root` when given.
    api/citation need the Script library (skipped when unavailable); semantic is pure AST."""
    wrapped = "class _W:\n" + (methods_text or "")
    out: dict = {"api": [], "semantic": [], "citation": []}

    if index is None and script_root:
        from pattern_generator.api_grounding import build_script_index
        index = build_script_index(script_root)
    if index:
        out["api"] = format_issues(
            check_api_calls(wrapped, index) + check_struct_fields(wrapped, index))
    if script_root:
        out["citation"] = format_issues(check_citations(code_refs or [], script_root))
    out["semantic"] = format_issues(check_semantics(wrapped))
    return out


def unit_findings(result: dict) -> list:
    """Flatten a check_unit result into `[dim] message` lines (empty = clean)."""
    lines: list = []
    for dim in ("api", "semantic", "citation"):
        for msg in result.get(dim, []):
            lines.append(f"[{dim}] {msg}")
    return lines
