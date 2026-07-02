"""Validate a generated pattern: syntax, structural fidelity to the IR, data flow
between steps, and API reality (do the api./ExecuteCMD./lib. calls hit real Script
symbols, with the right arguments?).

The structure check enforces that every generation unit's method is a real member
of the pattern class — catching the catastrophic "methods land outside the class
(after `if __name__`)" bug, which parses fine but makes process() run nothing
(a silent false PASS). The dataflow check enforces that a step which consumes
upstream state actually reads self.* it didn't produce itself (catching e.g. a
read step that re-randomises an LBA instead of reading the one just written).

Code grounding is done at generation time (gitnexus MCP, or direct Script
retrieval); the checks here are deterministic, post-hoc AST reality checks against
the IR + the Script/ library (see pattern_generator.api_grounding)."""
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

from pattern_generator.api_grounding import (
    build_script_index, check_api_calls, check_bare_names, check_struct_fields,
    format_issues, resolve_bare_name,
)
from pattern_generator.semantic_checks import check_semantics


def validate(py_source: str, ir: dict, script_root=None,
             py_path=None, run_mypy: bool = False) -> dict:
    """Validate syntax, IR structure, data flow, API reality, semantics, and (opt-in) mypy.

    The `semantic` key holds deterministic domain-invariant findings (pure AST, no
    Script library needed) — the meaning-level checks api_grounding deliberately skips;
    see pattern_generator.semantic_checks.

    `script_root` points at the Script/ library. When omitted or not a valid
    Script root, the api_grounding check reports "skipped" rather than failing —
    the pure-stdlib path (no Script available) still works.

    `run_mypy=True` (needs `py_path` on disk + the GitNexusMCP mypy config) adds a
    `mypy` key — type errors that api_grounding's name-only check cannot catch.
    Gracefully "skipped" when mypy / the config / the file is unavailable."""
    result = {"syntax": "pass", "structure": "pass", "dataflow": "pass"}

    try:
        tree = ast.parse(py_source)
    except SyntaxError as e:
        result["syntax"] = f"SyntaxError: {e}"
        return result  # can't go further without a parse

    struct_issues = _check_structure(tree, py_source, ir)
    if struct_issues:
        result["structure"] = struct_issues

    flow_issues = _check_dataflow(tree, ir)
    if flow_issues:
        result["dataflow"] = flow_issues

    # API reality check (best-effort; needs the Script library). Includes the target-UFS
    # version CATCH — a used accessor whose return struct is unavailable on the target version.
    result["api_grounding"] = _check_api_grounding(py_source, script_root, ir)

    # Semantic check (deterministic, pure AST — no Script library needed)
    sem_issues = check_semantics(py_source, ir)
    result["semantic"] = format_issues(sem_issues) if sem_issues else "pass"

    if run_mypy:
        result["mypy"] = _check_mypy(py_path, script_root)
    return result


def _check_mypy(py_path, script_root):
    """Run mypy on the generated .py (per-file, from GitNexusMCP/ with its config).

    Returns "pass" | "skipped" | [error lines]. "skipped" whenever mypy / the config
    / the file is missing or mypy hits a fatal error — never blocks on infra issues."""
    if not py_path or script_root is None:
        return "skipped"
    py = Path(py_path)
    gitnexus = Path(script_root).parent          # GitNexusMCP/  (script_root = .../Script)
    ini = gitnexus / "mypy_skip_known_issue.ini"
    if not py.is_file() or not ini.is_file():
        return "skipped"
    # Path arg relative to GitNexusMCP when possible (cleanest module inference); else abs.
    try:
        arg = str(py.resolve().relative_to(gitnexus.resolve()))
    except ValueError:
        arg = str(py.resolve())
    env = dict(os.environ, MYPYPATH=str(gitnexus.resolve()))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "mypy", "--config-file", str(ini.resolve()),
             "--follow-imports=silent", "--no-error-summary", "--no-color-output", arg],
            cwd=str(gitnexus), env=env, capture_output=True, text=True, timeout=300,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "skipped"
    if proc.returncode == 0:
        return "pass"
    if proc.returncode >= 2:
        return "skipped"                         # mypy fatal/config error — don't block
    name = py.name
    errs = [ln.strip() for ln in proc.stdout.splitlines()
            if ": error:" in ln and name in ln]
    return _enrich_mypy_names(errs, script_root) or "pass"


_MYPY_NAME_RE = re.compile(r'Name "([^"]+)" is not defined')


def _enrich_mypy_names(errs: list, script_root) -> list:
    """Append the deterministic RESOLUTION to mypy name-defined errors, so a repair
    prompt carries the fix (write api.X / use logger / import time) — not just the
    error. Round 1's bare `init_tester_to_unit_ready` got "fixed" to `lib.` exactly
    because the repair prompt named the error but not the correct namespace."""
    if not errs:
        return errs
    index = None
    if script_root:
        from pattern_generator.api_grounding import _cached_index
        index = _cached_index(str(script_root))
    out: list = []
    for ln in errs:
        m = _MYPY_NAME_RE.search(ln)
        if m:
            nm = m.group(1)
            alias = resolve_bare_name(nm, index) if index else None
            if nm in ("_log", "log"):
                ln += "  [hint: use the scaffold's 'logger']"
            elif alias:
                ln += f"  [hint: write {alias}.{nm} — see the namespace rule]"
            elif nm in sys.stdlib_module_names:
                ln += f"  [hint: add 'import {nm}']"
        out.append(ln)
    return out


# ---------------------------------------------------------------------------
# Structure: every unit's method must be a real method of the pattern class
# ---------------------------------------------------------------------------

def _find_pattern_class(tree: ast.Module) -> ast.ClassDef | None:
    """The generated pattern class — a UFSTC subclass at module level."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(
            isinstance(b, ast.Name) and b.id == "UFSTC" for b in node.bases
        ):
            return node
    # Fallback: first top-level class.
    return next((n for n in tree.body if isinstance(n, ast.ClassDef)), None)


def _expected_methods(ir: dict) -> list:
    """Method names the generation plan would produce (reuses the real splitter)."""
    try:
        from pattern_generator.stepwise import generation_units
        return [u["method"] for u in generation_units(ir) if u.get("method")]
    except Exception:
        return []


def _check_structure(tree: ast.Module, py_source: str, ir: dict) -> list:
    issues: list = []

    cls = _find_pattern_class(tree)
    if cls is None:
        issues.append("no pattern class (UFSTC subclass) found")
        return issues
    class_method_nodes = [n for n in cls.body
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    class_methods = {n.name for n in class_method_nodes}
    class_method_ids = {id(n) for n in class_method_nodes}

    # (1) Every stepN / loop-helper def must be a DIRECT member of the pattern class.
    #     The #1 catastrophic bug indents them outside the class (e.g. nested inside
    #     the `if __name__` block) — they parse fine but process() never runs them.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                re_step(node.name) or node.name.startswith("_loop")):
            if id(node) not in class_method_ids:
                issues.append(
                    f"method '{node.name}' is defined OUTSIDE the pattern class "
                    f"(process() will never run it)")

    # (2) No function/class def after the `if __name__ == '__main__'` guard.
    guard_idx = None
    for i, node in enumerate(tree.body):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"):
            guard_idx = i
            break
    if guard_idx is not None:
        for node in tree.body[guard_idx + 1:]:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                issues.append(
                    f"'{getattr(node, 'name', '?')}' is defined AFTER the "
                    f"`if __name__ == '__main__'` guard (dead / outside the class)")

    # (3) Every planned unit method must exist as a class method.
    expected = _expected_methods(ir)
    for m in expected:
        if m not in class_methods:
            issues.append(f"planned method '{m}' is missing from the pattern class")

    # (3b) No UNPLANNED stepN method — an extra auto-run method beyond the unit plan is drift
    #      (renumbered / duplicated step; process() runs it out of plan). Non-stepN helpers
    #      are allowed (a planned stepN may decompose into them), so this is FP-safe.
    if expected:
        planned_steps = {m for m in expected if re_step(m)}
        for m in sorted(class_methods):
            if re_step(m) and m not in planned_steps:
                issues.append(f"unplanned stepN method '{m}' not in the unit plan "
                              f"(planned: {sorted(planned_steps)}) — process() would run it "
                              "out of plan")

    # (4) The class must contain at least one stepN method.
    if not any(re_step(m) for m in class_methods):
        issues.append("pattern class contains no stepN method (nothing for process() to run)")

    # (5) Existing check: every count-loop's loop_count literal must appear.
    for phase in ir.get("phases", []):
        if phase.get("type") == "loop" and phase.get("loop_type") == "count":
            lc = phase.get("loop_count")
            if lc is not None and str(lc) not in py_source:
                issues.append(f"{phase['phase_id']}: loop_count {lc} not found in source")

    # (6) Duplicate class-member defs (e.g. a unit-provided post_process merged next to
    #     the scaffold stub) — Python silently keeps the LAST def; the earlier is dead.
    by_name: dict = {}
    for n in class_method_nodes:
        by_name.setdefault(n.name, []).append(n.lineno)
    for name, linenos in sorted(by_name.items()):
        if len(linenos) > 1:
            issues.append(f"method '{name}' defined more than once in the pattern class "
                          f"(lines {', '.join(map(str, linenos))}) — keep ONE")

    # (7) Loop sub-step helpers must accept (self, loop_idx) — the deterministic
    #     wrapper calls self._<slug>_<id>(loop_idx); a (self)-only def = TypeError.
    try:
        from pattern_generator.stepwise import generation_units
        loop_helpers = [u["method"] for u in generation_units(ir)
                        if u.get("loop_idx_param")]
    except Exception:
        loop_helpers = []
    fns = {n.name: n for n in class_method_nodes}
    for m in loop_helpers:
        fn = fns.get(m)
        if fn is None:
            continue          # (3) already reports the missing method
        a = fn.args
        pos = [x.arg for x in list(getattr(a, "posonlyargs", [])) + list(a.args)]
        if (len(pos) < 2 or pos[1] != "loop_idx") and not a.vararg:
            issues.append(f"method '{m}' must have signature (self, loop_idx) — the "
                          f"loop wrapper calls self.{m}(loop_idx)")

    return issues


def re_step(name: str) -> bool:
    return name.startswith("step") and name[4:].isdigit()


# ---------------------------------------------------------------------------
# Data flow: a consuming unit must read upstream self.* state (not re-derive it)
# ---------------------------------------------------------------------------

def _self_assigned_names(fn: ast.AST) -> set:
    """`self.X` that this function ASSIGNS (Store)."""
    out: set = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                        and t.value.id == "self"):
                    out.add(t.attr)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == "self":
                out.add(node.target.attr)
    return out


def _self_read_names(fn: ast.AST) -> set:
    """`self.X` that this function READS (Load)."""
    out: set = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
                and isinstance(node.value, ast.Name) and node.value.id == "self"):
            out.add(node.attr)
    return out


def _check_dataflow(tree: ast.Module, ir: dict) -> list:
    """Precise, low-false-positive dependency lint targeting the re-derivation trap.

    Flags a unit that OVERWRITES `self.<V>` for a var V it is supposed to *consume*
    WITHOUT ever reading the inherited value — i.e. it re-derives X locally (e.g. a
    read step that does `self.write_lba = random(...)` instead of reading the LBA
    the write step produced). We do NOT require the IR var name to be the attribute
    name elsewhere, so correct aliasing (a write record `self.write_data` carrying
    write_lba/len/pattern) is not flagged; only a literal overwrite-without-read of
    the consumed name is."""
    try:
        from pattern_generator.stepwise import generation_units
        units = generation_units(ir)
    except Exception:
        return []

    cls = _find_pattern_class(tree)
    if cls is None:
        return []
    fns = {n.name: n for n in cls.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    issues: list = []
    for u in units:
        consumes = u.get("consumes") or []
        if not consumes or u.get("kind") == "loop_wrapper":
            continue  # wrappers delegate reads to their sub-step helpers
        fn = fns.get(u.get("method"))
        if fn is None:
            continue  # structure check already reports a missing method
        writes = _self_assigned_names(fn)
        reads = _self_read_names(fn)
        # A consumed var that this method WRITES but never READS = re-derived.
        re_derived = [v for v in consumes if v in writes and v not in reads]
        if re_derived:
            issues.append(
                f"{u.get('method')} overwrites consumed var(s) {re_derived} without "
                f"reading the upstream value (re-derived locally — dependency broken?)")
    return issues


def _check_api_grounding(py_source: str, script_root, ir: dict | None = None):
    if not script_root:
        return "skipped"
    index = build_script_index(script_root)
    if not index:
        return "skipped"
    issues = (check_api_calls(py_source, index) + check_struct_fields(py_source, index)
              + check_bare_names(py_source, index))
    # Target-UFS-version CATCH: a used accessor whose return struct has no variant for the
    # resolved target version (TC frontmatter ufs_version / wiki/target.md).
    from pattern_generator.capability_resolver import check_version_availability
    from pattern_generator.ufs_version import resolve as _resolve_version
    version = _resolve_version(ir or {})
    if version:
        issues += check_version_availability(py_source, index, version)
    return "pass" if not issues else format_issues(issues)
