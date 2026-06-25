"""API reality check — does the generated pattern call real Script symbols?

Pure stdlib (ast + difflib). No imports are executed; the Script library is
indexed by static AST analysis. We resolve the three namespaces the scaffold
exposes (see pattern_generator.stepwise.STANDARD_IMPORTS):

    from Script import api                       ->  alias "api"
    import Script.api.cmd_seq as ExecuteCMD      ->  alias "ExecuteCMD"
    from Script.lib import sdk_lib as lib        ->  alias "lib"

For each `api.X(...)` / `ExecuteCMD.X(...)` / `lib.X(...)` call in a generated
.py we check:
  * X resolves to a real symbol in that namespace (else: unknown symbol,
    with a difflib near-name suggestion);
  * every keyword argument name belongs to X's signature (unless X takes
    **kwargs);
  * the positional-argument count does not exceed X's capacity (unless *args).

Scope (intentional): only the three module namespaces above. Instance-method
calls (`cmd.assign(...)`) and attribute access (`dev_desc.l85_...`) are NOT
checked — they need type inference. We prefer false negatives over false
positives: when name resolution is incomplete we fall back to "exists somewhere
in the package" and skip the signature check rather than cry wolf.
"""
from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass, field
from pathlib import Path

# Aliases the scaffold binds; only calls on these are checked.
NAMESPACE_ALIASES = ("api", "ExecuteCMD", "lib")


@dataclass
class SigSpec:
    """A callable symbol's signature, captured statically."""
    kind: str                       # "func" | "class" | "name"
    params: set = field(default_factory=set)   # named params (excl. self/*args/**kwargs)
    has_kwargs: bool = False        # **kwargs present -> any kwarg accepted
    has_varargs: bool = False       # *args present  -> any positional count accepted
    max_positional: int = 0         # positional-or-keyword + positional-only count


@dataclass
class Namespace:
    """A resolved namespace: precise symbol table + a conservative fallback set."""
    symbols: dict = field(default_factory=dict)   # name -> SigSpec
    all_names: set = field(default_factory=set)    # every def/class name in the package


# ---------------------------------------------------------------------------
# Module file resolution
# ---------------------------------------------------------------------------

def _resolve_relative(module_file: Path, level: int, parts: list) -> Path | None:
    """Resolve a relative import target to a module file path.

    `level` is the number of leading dots; for level 1 the base is the directory
    containing `module_file` (true for both __init__.py and regular modules)."""
    base = module_file.parent
    for _ in range(level - 1):
        base = base.parent
    target = base
    for p in parts:
        target = target / p
    if (target.with_suffix(".py")).is_file():
        return target.with_suffix(".py")
    init = target / "__init__.py"
    if init.is_file():
        return init
    return None


# ---------------------------------------------------------------------------
# Per-module export collection (transitive `import *` aware)
# ---------------------------------------------------------------------------

def _sig_from_args(args: ast.arguments, skip_self: bool) -> SigSpec:
    posonly = list(getattr(args, "posonlyargs", []))
    regular = list(args.args)
    names = [a.arg for a in posonly + regular]
    if skip_self and names:
        names = names[1:]
    kwonly = [a.arg for a in args.kwonlyargs]
    params = set(names) | set(kwonly)
    return SigSpec(
        kind="func",
        params=params,
        has_kwargs=args.kwarg is not None,
        has_varargs=args.vararg is not None,
        max_positional=len(names),
    )


def _class_sig(node: ast.ClassDef) -> SigSpec:
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
            s = _sig_from_args(item.args, skip_self=True)
            s.kind = "class"
            return s
    # No __init__ found — accept any construction (avoid false positives).
    return SigSpec(kind="class", has_kwargs=True, has_varargs=True)


def _module_exports(module_file: Path, cache: dict, visiting: set) -> dict:
    """Return {name: SigSpec} exported by a module, resolving `import *` chains.

    Respects `__all__` when present. Cycle-safe via `visiting`."""
    key = str(module_file)
    if key in cache:
        return cache[key]
    if key in visiting:
        return {}            # cycle — break
    visiting.add(key)

    exports: dict = {}
    dunder_all: set | None = None
    try:
        tree = ast.parse(module_file.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        visiting.discard(key)
        cache[key] = {}
        return {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            exports[node.name] = _sig_from_args(node.args, skip_self=False)
        elif isinstance(node, ast.ClassDef):
            exports[node.name] = _class_sig(node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    if t.id == "__all__":
                        dunder_all = _literal_str_set(node.value)
                    else:
                        exports.setdefault(t.id, SigSpec(kind="name"))
        elif isinstance(node, ast.ImportFrom) and node.level > 0:
            parts = node.module.split(".") if node.module else []
            target = _resolve_relative(module_file, node.level, parts)
            if target is None:
                continue
            if any(a.name == "*" for a in node.names):
                exports.update(_module_exports(target, cache, visiting))
            else:
                sub = _module_exports(target, cache, visiting)
                for a in node.names:
                    bound = a.asname or a.name
                    if a.name in sub:
                        exports[bound] = sub[a.name]
                    else:
                        # importing a submodule or unresolved name; record existence
                        exports.setdefault(bound, SigSpec(kind="name"))

    if dunder_all is not None:
        exports = {n: s for n, s in exports.items() if n in dunder_all}

    visiting.discard(key)
    cache[key] = exports
    return exports


def _literal_str_set(value: ast.AST) -> set:
    out = set()
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.add(elt.value)
    return out


def _walk_all_names(package_dir: Path) -> set:
    """Every top-level def/class name anywhere under a package (fallback set)."""
    names: set = set()
    if not package_dir.exists():
        return names
    for py in package_dir.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
    return names


# ---------------------------------------------------------------------------
# Public: build the index
# ---------------------------------------------------------------------------

def build_script_index(script_root) -> dict | None:
    """Build {alias: Namespace} for api / ExecuteCMD / lib.

    Returns None if `script_root` does not look like a Script library root."""
    root = Path(script_root)
    api_init = root / "api" / "__init__.py"
    cmdseq_init = root / "api" / "cmd_seq" / "__init__.py"
    # `from Script.lib import sdk_lib as lib` — sdk_lib may be a module or a package.
    lib_mod = root / "lib" / "sdk_lib.py"
    lib_pkg = root / "lib" / "sdk_lib" / "__init__.py"
    lib_file = lib_mod if lib_mod.is_file() else lib_pkg
    if not api_init.is_file():
        return None

    cache: dict = {}
    index: dict = {}
    if api_init.is_file():
        index["api"] = Namespace(
            symbols=_module_exports(api_init, cache, set()),
            all_names=_walk_all_names(root / "api"),
        )
    if cmdseq_init.is_file():
        index["ExecuteCMD"] = Namespace(
            symbols=_module_exports(cmdseq_init, cache, set()),
            all_names=_walk_all_names(root / "api" / "cmd_seq"),
        )
    if lib_file.is_file():
        index["lib"] = Namespace(
            symbols=_module_exports(lib_file, cache, set()),
            all_names=_walk_all_names(root / "lib"),
        )
    return index


# ---------------------------------------------------------------------------
# Public: check a generated source against the index
# ---------------------------------------------------------------------------

def check_api_calls(py_source: str, index: dict) -> list:
    """Return a list of issue dicts for namespace calls that don't match Script.

    Each issue: {alias, symbol, kind, detail, line, [suggestion]}.
    kind in {"unknown_symbol", "unknown_kwarg", "too_many_positional"}."""
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []          # syntax errors are reported separately by validate()

    issues: list = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
            continue
        alias = func.value.id
        if alias not in NAMESPACE_ALIASES or alias not in index:
            continue
        ns = index[alias]
        name = func.attr

        if name not in ns.symbols:
            if name in ns.all_names:
                continue   # exists somewhere; resolver just didn't reach it — skip
            issue = {"alias": alias, "symbol": name, "kind": "unknown_symbol",
                     "detail": f"{alias}.{name} not found in Script", "line": node.lineno}
            near = difflib.get_close_matches(name, ns.symbols.keys(), n=1, cutoff=0.7)
            if near:
                issue["suggestion"] = near[0]
            issues.append(issue)
            continue

        spec = ns.symbols[name]
        if spec.kind == "name":
            continue       # not a func/class we can signature-check

        # keyword arguments must be known (unless **kwargs)
        if not spec.has_kwargs:
            for kw in node.keywords:
                if kw.arg is None:
                    continue          # **d splat — give up on strictness
                if kw.arg not in spec.params:
                    issues.append({
                        "alias": alias, "symbol": name, "kind": "unknown_kwarg",
                        "detail": f"{alias}.{name}() has no parameter '{kw.arg}'",
                        "line": node.lineno,
                    })

        # positional argument count must fit (unless *args)
        if not spec.has_varargs:
            has_star = any(isinstance(a, ast.Starred) for a in node.args)
            n_pos = len(node.args)
            if not has_star and n_pos > spec.max_positional:
                issues.append({
                    "alias": alias, "symbol": name, "kind": "too_many_positional",
                    "detail": (f"{alias}.{name}() takes at most {spec.max_positional} "
                               f"positional args, got {n_pos}"),
                    "line": node.lineno,
                })
    return issues


def format_issues(issues: list) -> list:
    """Render issue dicts as human-readable strings (for validate/retrieval_debug)."""
    out = []
    for i in issues:
        line = f"L{i['line']}: {i['detail']}"
        if i.get("suggestion"):
            line += f" (did you mean '{i['suggestion']}'?)"
        out.append(line)
    return out
