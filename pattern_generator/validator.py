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

from pattern_generator.api_grounding import (
    build_script_index, check_api_calls, format_issues,
)


def validate(py_source: str, ir: dict, script_root=None) -> dict:
    """Validate syntax, IR structure, data flow, and (if script_root given) API reality.

    `script_root` points at the Script/ library. When omitted or not a valid
    Script root, the api_grounding check reports "skipped" rather than failing —
    the pure-stdlib path (no Script available) still works."""
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

    # API reality check (best-effort; needs the Script library)
    result["api_grounding"] = _check_api_grounding(py_source, script_root)
    return result


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
    for m in _expected_methods(ir):
        if m not in class_methods:
            issues.append(f"planned method '{m}' is missing from the pattern class")

    # (4) The class must contain at least one stepN method.
    if not any(re_step(m) for m in class_methods):
        issues.append("pattern class contains no stepN method (nothing for process() to run)")

    # (5) Existing check: every count-loop's loop_count literal must appear.
    for phase in ir.get("phases", []):
        if phase.get("type") == "loop" and phase.get("loop_type") == "count":
            lc = phase.get("loop_count")
            if lc is not None and str(lc) not in py_source:
                issues.append(f"{phase['phase_id']}: loop_count {lc} not found in source")

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


def _check_api_grounding(py_source: str, script_root):
    if not script_root:
        return "skipped"
    index = build_script_index(script_root)
    if not index:
        return "skipped"
    issues = check_api_calls(py_source, index)
    return "pass" if not issues else format_issues(issues)
