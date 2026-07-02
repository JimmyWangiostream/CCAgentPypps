"""Per-unit deterministic gate — the SAME checks `finish` runs on the whole file, run
on ONE unit's methods right after it is generated.

The pipeline generates each unit independently (Step 5), but the deterministic checks
(api_grounding / semantic / citation) historically ran only at `finish`, on the assembled
file — so a unit's bug was caught a whole file later, with the cheapest, most-local context
already gone. `check_unit` shifts those exact checks left to the unit, so the workflow can
rewrite just that unit before moving on. Pure reuse — no new check logic.
"""
from __future__ import annotations

import ast

from pattern_generator.api_grounding import (
    check_api_calls, check_bare_names, check_citations, check_struct_fields,
    format_issues,
)
from pattern_generator.semantic_checks import check_semantics

_DIMENSIONS = ("api", "semantic", "citation", "structure")


def _check_unit_structure(wrapped_src: str, expected_methods,
                          loop_idx_required: bool = False) -> list:
    """Shift-left naming/structure enforcement: the emitted defs must be EXACTLY the unit's
    planned method name(s). Catches naming drift (loop→unit renames, split-into-helpers) at
    the unit where it happens, instead of presence-only at the final gate — a wrong/extra
    name is dead code (`process()` only auto-runs the planned stepN)."""
    expected = set(expected_methods or ())
    if not expected:
        return []
    try:
        tree = ast.parse(wrapped_src)
    except SyntaxError:
        return []
    def_nodes = [n for cls in tree.body if isinstance(cls, ast.ClassDef)
                 for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    defs = [n.name for n in def_nodes]
    findings: list = []
    for m in sorted(expected):
        if m not in defs:
            findings.append(f"missing planned method '{m}' — name it EXACTLY '{m}' "
                            "(a wrong name = dead code; process() only runs the planned stepN)")
    for d in defs:
        if d not in expected:
            findings.append(f"unplanned method '{d}' — this unit must define ONLY "
                            f"{sorted(expected)}; rename/remove it (extra methods are dead code)")
    if loop_idx_required:
        # A loop sub-step helper is called `self._<slug>_<id>(loop_idx)` by the
        # deterministic wrapper — a (self)-only def is a TypeError at runtime.
        for n in def_nodes:
            if n.name not in expected:
                continue
            pos = [x.arg for x in list(getattr(n.args, "posonlyargs", [])) + list(n.args.args)]
            if (len(pos) < 2 or pos[1] != "loop_idx") and not n.args.vararg:
                findings.append(f"method '{n.name}' must have signature (self, loop_idx) "
                                f"— the loop wrapper calls self.{n.name}(loop_idx)")
    return findings


def check_unit(methods_text: str, code_refs=None, script_root=None, index=None,
               expected_methods=None, extra_imports=None,
               loop_idx_required: bool = False) -> dict:
    """Run the per-unit checks on one unit's `=== METHODS ===` body + its `=== CODE REFS ===`.

    Returns {api, semantic, citation, structure} -> list[str] findings (empty list = clean
    for that dimension). `methods_text` is the class-body-indented method source; it is
    wrapped in a dummy class so the AST parses. `index` (a prebuilt api_grounding index) may
    be passed to avoid rebuilding it per unit; otherwise it is built from `script_root` when
    given. api/citation need the Script library (skipped when unavailable); semantic +
    structure are pure AST. `expected_methods` (the unit's pinned method name[s]) activates
    the shift-left naming/structure check; omit it to skip that dimension (back-compat).
    `extra_imports` = the import lines available to this unit (its own EXTRA IMPORTS —
    ideally the union across generated units, since assemble merges them all) so the
    bare-name check doesn't flag legitimately-imported names. `loop_idx_required` = the
    unit is a loop sub-step helper and must accept (self, loop_idx)."""
    wrapped = "class _W:\n" + (methods_text or "")
    out: dict = {d: [] for d in _DIMENSIONS}

    if index is None and script_root:
        from pattern_generator.api_grounding import build_script_index
        index = build_script_index(script_root)
    if index:
        out["api"] = format_issues(
            check_api_calls(wrapped, index) + check_struct_fields(wrapped, index)
            + check_bare_names(wrapped, index, extra_imports=extra_imports or ()))
    if script_root:
        out["citation"] = format_issues(check_citations(code_refs or [], script_root))
    out["semantic"] = format_issues(check_semantics(wrapped))
    out["structure"] = _check_unit_structure(wrapped, expected_methods,
                                             loop_idx_required=loop_idx_required)
    return out


def unit_findings(result: dict) -> list:
    """Flatten a check_unit result into `[dim] message` lines (empty = clean)."""
    lines: list = []
    for dim in _DIMENSIONS:
        for msg in result.get(dim, []):
            lines.append(f"[{dim}] {msg}")
    return lines
