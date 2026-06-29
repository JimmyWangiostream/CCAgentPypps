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
import functools
import re
import warnings
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
    pos_params: list = field(default_factory=list)   # ordered positional param names
    num_pos_required: int = 0       # leading positional params WITHOUT a default
    required_kwonly: set = field(default_factory=set)  # kw-only params without a default


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
    # Defaults bind to the TAIL of the positional list, so the leading
    # (len(names) - num_defaults) positional params are required.
    num_pos_required = max(0, len(names) - len(args.defaults))
    required_kwonly = {
        a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is None
    }
    return SigSpec(
        kind="func",
        params=params,
        has_kwargs=args.kwarg is not None,
        has_varargs=args.vararg is not None,
        max_positional=len(names),
        pos_params=names,
        num_pos_required=num_pos_required,
        required_kwonly=required_kwonly,
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
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
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
    return names


# ---------------------------------------------------------------------------
# Deterministic API facts: real signatures + enum-member whitelist (the arbiter).
# These exist so neither the model NOR a reviewer has to GUESS param names
# (index= vs lun=) or enum members (IDLE vs Idle) — the answer is read straight
# from the Script source, which never lags the code.
# ---------------------------------------------------------------------------

_ENUM_BASES = {"IntEnum", "IntFlag", "Enum", "Flag", "StrEnum"}


def render_sig(name: str, spec: "SigSpec") -> str:
    """Readable real signature, e.g. `set_flag(idn, index=..., selector=...)`."""
    parts = [p if i < spec.num_pos_required else f"{p}=..."
             for i, p in enumerate(spec.pos_params)]
    for k in sorted(spec.params - set(spec.pos_params)):     # keyword-only params
        parts.append(k if k in spec.required_kwonly else f"{k}=...")
    if spec.has_varargs:
        parts.append("*args")
    if spec.has_kwargs:
        parts.append("**kwargs")
    return f"{name}({', '.join(parts)})"


def _build_enum_index(root: Path) -> dict:
    """{EnumClassName: {member names}} for every IntEnum/Enum/... under api/."""
    enums: dict = {}
    base = root / "api"
    if not base.is_dir():
        return enums
    for py in base.rglob("*.py"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if not (isinstance(node, ast.ClassDef) and any(
                    isinstance(b, ast.Name) and b.id in _ENUM_BASES for b in node.bases)):
                continue
            members: set = set()
            for item in node.body:
                if isinstance(item, ast.Assign):
                    members |= {t.id for t in item.targets if isinstance(t, ast.Name)}
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    members.add(item.target.id)
            if members:
                enums.setdefault(node.name, set()).update(members)
    return enums


# ---------------------------------------------------------------------------
# Public: build the index
# ---------------------------------------------------------------------------

def build_script_index(script_root) -> dict | None:
    """Build {alias: Namespace} for api / ExecuteCMD / lib, plus `_enums`.

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
    index["_enums"] = _build_enum_index(root)   # not a namespace alias; see check_api_calls
    return index


# ---------------------------------------------------------------------------
# Public: inject deterministic facts AT GENERATION (Phase B — prevent guessing)
#
# The gate (check_api_calls) CATCHES guesses after the fact; this FEEDS the exact
# form before the fact, from the SAME AST index, so the model copies `index=` /
# `IDLE` instead of guessing. It is additive — wiki (flow meaning) and the model's
# gitnexus/code-candidate discovery still run; this only nails the exact signature
# + enum members for the symbols the unit is likely to use.
# ---------------------------------------------------------------------------

_TOKEN_SPLIT = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+")
# enum class-name tokens too generic to be a relevance signal on their own
_GENERIC_ENUM_TOKENS = {"idn", "id", "type", "status", "mode", "state", "code", "value"}


def _tokens(text: str) -> set:
    return {m.group(0).lower() for m in _TOKEN_SPLIT.finditer(text or "")}


@functools.lru_cache(maxsize=8)
def _cached_index(script_root_str: str):
    return build_script_index(script_root_str)


def api_facts(script_root, symbol_names=(), query: str = "", max_enums: int = 8) -> list:
    """Authoritative facts to inject into a unit prompt (possibly empty).

    * exact signature for each candidate `symbol_names` found in api/ExecuteCMD/lib;
    * valid members of every enum whose class-name shares a (non-generic) token with
      the unit query or a candidate symbol — so the model copies the real member.

    Deterministic, read straight from Script; cached per root. Returns [] if the
    root is not a Script library (graceful — generation proceeds without it)."""
    index = _cached_index(str(script_root))
    if not index:
        return []

    facts: list = []
    seen: set = set()
    for alias in NAMESPACE_ALIASES:
        ns = index.get(alias)
        if not ns:
            continue
        for n in symbol_names:
            if n in seen:
                continue
            spec = ns.symbols.get(n)
            if spec and spec.kind in ("func", "class"):
                # skip uninformative "(*args, **kwargs)" shells (class w/o __init__):
                # no real param names to anchor on, and enum classes are covered below.
                if spec.params or spec.pos_params:
                    facts.append(f"{alias}.{render_sig(n, spec)}")
                seen.add(n)

    enums = index.get("_enums", {})
    if enums:
        qtok = _tokens(query)
        for n in symbol_names:
            qtok |= _tokens(n)
        scored: list = []
        for ename, members in enums.items():
            overlap = (_tokens(ename) & qtok) - _GENERIC_ENUM_TOKENS
            if overlap:
                scored.append((len(overlap), ename, members))
        scored.sort(key=lambda x: (-x[0], x[1]))
        for _, ename, members in scored[:max_enums]:
            facts.append(f"{ename} valid members: {', '.join(sorted(members))}")
    return facts


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
        realsig = f"  [real signature: {render_sig(name, spec)}]"   # the correct form

        # keyword arguments must be known (unless **kwargs)
        if not spec.has_kwargs:
            for kw in node.keywords:
                if kw.arg is None:
                    continue          # **d splat — give up on strictness
                if kw.arg not in spec.params:
                    issues.append({
                        "alias": alias, "symbol": name, "kind": "unknown_kwarg",
                        "detail": f"{alias}.{name}() has no parameter '{kw.arg}'" + realsig,
                        "line": node.lineno,
                    })

        # positional argument count must fit (unless *args)
        has_star = any(isinstance(a, ast.Starred) for a in node.args)
        n_pos = len(node.args)
        if not spec.has_varargs:
            if not has_star and n_pos > spec.max_positional:
                issues.append({
                    "alias": alias, "symbol": name, "kind": "too_many_positional",
                    "detail": (f"{alias}.{name}() takes at most {spec.max_positional} "
                               f"positional args, got {n_pos}" + realsig),
                    "line": node.lineno,
                })

        # required arguments must all be supplied. Only checked when the call
        # site is unambiguous (no *args / **kwargs splat) — we prefer false
        # negatives over crying wolf.
        has_dsplat = any(kw.arg is None for kw in node.keywords)
        if not has_star and not has_dsplat:
            provided_kw = {kw.arg for kw in node.keywords if kw.arg}
            # positional args fill the first n_pos positional params
            missing = [p for p in spec.pos_params[n_pos:spec.num_pos_required]
                       if p not in provided_kw]
            missing += [k for k in spec.required_kwonly if k not in provided_kw]
            if missing:
                issues.append({
                    "alias": alias, "symbol": name, "kind": "missing_required_arg",
                    "detail": (f"{alias}.{name}() missing required argument(s): "
                               f"{', '.join(missing)}" + realsig),
                    "line": node.lineno,
                })

    issues += _check_enum_usage(tree, index.get("_enums", {}))
    return issues


def _check_enum_usage(tree: ast.AST, enums: dict) -> list:
    """Flag `<Enum>.<MEMBER>` where MEMBER is not a real member of that enum —
    catches IDLE vs Idle, IN_PROGRESS vs In_Progress, wrong enum class. Lists the
    valid members so the fix is copy-paste."""
    if not enums:
        return []
    issues: list = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        member = node.attr
        if member in ("value", "name") or member.startswith("__"):
            continue                       # enum builtins / dunders, not members
        v = node.value
        enum_name = v.attr if isinstance(v, ast.Attribute) else (
            v.id if isinstance(v, ast.Name) else None)
        if enum_name not in enums or member in enums[enum_name]:
            continue
        valid = sorted(enums[enum_name])
        detail = (f"{enum_name} has no member '{member}'  "
                  f"[valid: {', '.join(valid[:12])}{' …' if len(valid) > 12 else ''}]")
        issue = {"alias": enum_name, "symbol": member, "kind": "unknown_enum_member",
                 "detail": detail, "line": node.lineno}
        near = difflib.get_close_matches(member, valid, n=1, cutoff=0.6)
        if near:
            issue["suggestion"] = near[0]
        issues.append(issue)
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
