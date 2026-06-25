"""Validate a generated pattern: syntax, structural fidelity to the IR, and
API reality (do the api./ExecuteCMD./lib. calls hit real Script symbols?).

Code grounding is done at generation time via the gitnexus MCP server; the
api-grounding check here is a deterministic, post-hoc AST reality check against
the Script/ library (see pattern_generator.api_grounding)."""
import ast

from pattern_generator.api_grounding import (
    build_script_index, check_api_calls, format_issues,
)


def validate(py_source: str, ir: dict, script_root=None) -> dict:
    """Validate syntax, IR structural fidelity, and (if script_root given) API reality.

    `script_root` points at the Script/ library. When omitted or not a valid
    Script root, the api_grounding check reports "skipped" rather than failing —
    the pure-stdlib path (no Script available) still works."""
    result = {"syntax": "pass", "structure": "pass"}

    try:
        tree = ast.parse(py_source)
    except SyntaxError as e:
        result["syntax"] = f"SyntaxError: {e}"
        return result  # can't go further without a parse

    # Structure: every count-loop's loop_count literal must appear in source
    struct_issues = []
    for phase in ir.get("phases", []):
        if phase.get("type") == "loop" and phase.get("loop_type") == "count":
            lc = phase.get("loop_count")
            if lc is not None and str(lc) not in py_source:
                struct_issues.append(f"{phase['phase_id']}: loop_count {lc} not found")
    if struct_issues:
        result["structure"] = struct_issues

    # API reality check (best-effort; needs the Script library)
    result["api_grounding"] = _check_api_grounding(py_source, script_root)
    return result


def _check_api_grounding(py_source: str, script_root):
    if not script_root:
        return "skipped"
    index = build_script_index(script_root)
    if not index:
        return "skipped"
    issues = check_api_calls(py_source, index)
    return "pass" if not issues else format_issues(issues)
