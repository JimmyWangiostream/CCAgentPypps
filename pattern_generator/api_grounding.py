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
import builtins
import difflib
import functools
import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

# Aliases the scaffold binds; only calls on these are checked.
NAMESPACE_ALIASES = ("api", "ExecuteCMD", "lib")

# ONE source of truth: defining-module path -> scaffold alias (first match wins).
# Mirrors stepwise.STANDARD_IMPORTS (consistency enforced by a test).
ALIAS_RULES = (("api/cmd_seq/", "ExecuteCMD"), ("api/", "api"), ("lib/", "lib"))
# Names the scaffold itself binds (STANDARD_IMPORTS) — always-known in generated code.
SCAFFOLD_NAMES = frozenset({"package_root", "api", "lib", "UFSTC", "logger", "ExecuteCMD"})
# Deterministic bare-name resolution priority. Sound because api is a superset of the
# api/ExecuteCMD overlap (cmd_seq is re-exported into api) and api/lib are disjoint.
ALIAS_PRIORITY = ("api", "ExecuteCMD", "lib")
# Where each alias's symbols live (used in finding messages so the fix is copy-paste).
_ALIAS_HOME = {"api": "Script/api/**", "ExecuteCMD": "Script/api/cmd_seq/**",
               "lib": "Script/lib/**"}


def alias_for_path(rel_path) -> str | None:
    """Scaffold alias for a Script-relative module path (None = not scaffold-bound).

    Accepts 'api/ufs_api/initial_device.py', 'Script/api/...', backslashes, etc."""
    p = str(rel_path).replace("\\", "/").lstrip("./")
    if p.startswith("Script/"):
        p = p[len("Script/"):]
    for prefix, alias in ALIAS_RULES:
        if p.startswith(prefix):
            return alias
    return None


def resolve_bare_name(name: str, index: dict) -> str | None:
    """Alias whose symbol table contains `name`, by ALIAS_PRIORITY; None if nowhere.

    Only the re-export-reachable `symbols` tables count (a name buried in `all_names`
    is not callable via the alias, so suggesting it would be wrong)."""
    for alias in ALIAS_PRIORITY:
        ns = index.get(alias)
        if ns is not None and name in ns.symbols:
            return alias
    return None


# Injected into every unit/wholefile prompt (stepwise/wholefile import it) AND enforced
# by check_api_calls/check_bare_names — PREVENT and CATCH from this one table.
NAMESPACE_RULE = """\
## Namespace rule (AUTHORITATIVE — deterministic; the gate enforces it)
The scaffold binds EXACTLY three Script namespaces. Prefix every Script symbol by
where its `def`/`class` LIVES (its defining file path):
  - Script/api/cmd_seq/**            -> ExecuteCMD.<name>
  - Script/api/** (everything else)  -> api.<name>   (enums too: api.FlagIDN, api.Dcmd5ResetType)
  - Script/lib/**                    -> lib.<name>
Reference patterns/idioms use `from Script.api.ufs_api import *`, so they show BARE
names (e.g. `init_tester_to_unit_ready(...)`). The scaffold has NO star import — you
MUST re-prefix every bare symbol per its defining path (-> `api.init_tester_to_unit_ready(...)`).
Never write a bare Script symbol and never guess a different prefix.
Script/project_api/** and Script/pattern/** are NOT bound by the scaffold — to use one,
add an explicit import in === EXTRA IMPORTS ===.
Logging: the scaffold provides `logger` — use `logger.info/...`; `_log` does NOT exist.
Stdlib modules you use (e.g. `time`) MUST be imported in === EXTRA IMPORTS ===."""


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
    returns: str = ""               # return-type stem (inner of Optional/List/Union), if annotated
    annotations: dict = field(default_factory=dict)    # param -> annotation source text


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
    pos_args = posonly + regular
    if skip_self and pos_args:
        pos_args = pos_args[1:]
    names = [a.arg for a in pos_args]
    kwonly = [a.arg for a in args.kwonlyargs]
    params = set(names) | set(kwonly)
    annotations = {}
    for a in pos_args + list(args.kwonlyargs):
        if a.annotation is not None:
            try:
                annotations[a.arg] = ast.unparse(a.annotation)
            except Exception:
                pass
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
        annotations=annotations,
    )


def _return_type_stem(ann) -> str:
    """Inner type name of a return annotation, unwrapping Optional/List/Union wrappers.

    `List[ConfigDescriptorUnion]` -> 'ConfigDescriptorUnion'; `Optional[Foo]` -> 'Foo';
    `mod.Bar` -> 'Bar'. '' when unannotated / not resolvable."""
    if ann is None:
        return ""
    if isinstance(ann, ast.Name):
        return ann.id
    if isinstance(ann, ast.Attribute):
        return ann.attr
    if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
        return ann.value.split("[")[-1].split("]")[0].split(".")[-1].strip()
    if isinstance(ann, ast.Subscript):
        sl = ann.slice
        if isinstance(sl, ast.Tuple) and sl.elts:
            return _return_type_stem(sl.elts[-1])   # Union[A,B]/Dict[K,V] -> last
        return _return_type_stem(sl)                # List[X]/Optional[X] -> X
    return ""


def _class_sig(node: ast.ClassDef) -> SigSpec:
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
            s = _sig_from_args(item.args, skip_self=True)
            s.kind = "class"
            return s
    # No __init__ found — accept any construction (avoid false positives).
    return SigSpec(kind="class", has_kwargs=True, has_varargs=True)


def _resolve_script_absolute(root: Path | None, module: str | None) -> Path | None:
    """Resolve an absolute `Script.x.y` module name to a file under the Script root."""
    if root is None or not module:
        return None
    parts = module.split(".")
    if parts[0] != "Script" or len(parts) < 2:
        return None
    target = root.joinpath(*parts[1:])
    if target.with_suffix(".py").is_file():
        return target.with_suffix(".py")
    init = target / "__init__.py"
    return init if init.is_file() else None


def _module_exports_ex(module_file: Path, cache: dict, visiting: set,
                       root: Path | None = None) -> tuple:
    """(exports, complete) for a module, mirroring Python's star-import semantics.

    exports = {name: SigSpec} of every PUBLIC name the module namespace binds:
    defs/classes/assigns, `import x` module bindings, by-name imports, and the
    (underscore-filtered) merge of every resolvable `import *` — relative AND
    absolute `Script.*` (when `root` is given). `complete` is False when any star
    import could NOT be resolved (external lib, missing file, parse error) — i.e.
    the export set may be missing names, so callers relying on it for bare-name
    legality must suppress instead of flag (false-negative bias).
    Respects `__all__` when present. Cycle-safe via `visiting`."""
    key = str(module_file)
    if key in cache:
        return cache[key]
    if key in visiting:
        return {}, True      # cycle — break; the cycle owner accumulates the rest
    visiting.add(key)

    exports: dict = {}
    complete = True
    dunder_all: set | None = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(module_file.read_text(encoding="utf-8-sig", errors="ignore"))
    except (OSError, SyntaxError):
        visiting.discard(key)
        cache[key] = ({}, False)
        return {}, False

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spec = _sig_from_args(node.args, skip_self=False)
            spec.returns = _return_type_stem(node.returns)
            exports[node.name] = spec
        elif isinstance(node, ast.ClassDef):
            exports[node.name] = _class_sig(node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    if t.id == "__all__":
                        dunder_all = _literal_str_set(node.value)
                    else:
                        exports.setdefault(t.id, SigSpec(kind="name"))
        elif isinstance(node, ast.Import):
            # `import time` binds `time` in the module namespace — a star import of
            # THIS module re-exports it (that is how real patterns get bare `time`).
            for a in node.names:
                exports.setdefault(a.asname or a.name.split(".")[0], SigSpec(kind="name"))
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                parts = node.module.split(".") if node.module else []
                target = _resolve_relative(module_file, node.level, parts)
            else:
                target = _resolve_script_absolute(root, node.module)
            if any(a.name == "*" for a in node.names):
                if target is None:
                    complete = False        # unresolvable star — exports may be missing
                    continue
                # Python's star import skips underscore-prefixed names (barring __all__,
                # which the sub-module's own export set already respects for its public
                # names) — without this, private module vars like `_log` leak into the
                # namespace model and bare `_log` gets "resolved" to `api._log`.
                sub, sub_complete = _module_exports_ex(target, cache, visiting, root)
                complete = complete and sub_complete
                exports.update({n: s for n, s in sub.items() if not n.startswith("_")})
            else:
                sub = {}
                if target is not None:
                    sub, _c = _module_exports_ex(target, cache, visiting, root)
                for a in node.names:
                    bound = a.asname or a.name
                    if a.name in sub:
                        exports[bound] = sub[a.name]
                    else:
                        # importing a submodule or unresolved name; the NAME is bound
                        # regardless of resolvability — record existence
                        exports.setdefault(bound, SigSpec(kind="name"))

    if dunder_all is not None:
        exports = {n: s for n, s in exports.items() if n in dunder_all}

    visiting.discard(key)
    cache[key] = (exports, complete)
    return exports, complete


def _module_exports(module_file: Path, cache: dict, visiting: set,
                    root: Path | None = None) -> dict:
    """Back-compat wrapper over _module_exports_ex (exports dict only)."""
    return _module_exports_ex(module_file, cache, visiting, root)[0]


def _literal_str_set(value: ast.AST) -> set:
    out = set()
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.add(elt.value)
    return out


def _walk_all_names(package_dir: Path) -> set:
    """Every top-level def/class/constant name anywhere under a package (fallback set).

    Module-level Assign targets count too: real patterns reference package constants
    (`api.BLOCK4K_SIZE_128M_BYTE`, defined by assignment in api/.../constant_define.py)
    — a def/class-only set would wrongly flag those as unknown/wrong-namespace."""
    names: set = set()
    if not package_dir.exists():
        return names
    for py in package_dir.rglob("*.py"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8-sig", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return names


# ---------------------------------------------------------------------------
# Deterministic API facts: real signatures + enum-member whitelist (the arbiter).
# These exist so neither the model NOR a reviewer has to GUESS param names
# (index= vs lun=) or enum members (IDLE vs Idle) — the answer is read straight
# from the Script source, which never lags the code.
# ---------------------------------------------------------------------------

_ENUM_BASES = {"IntEnum", "IntFlag", "Enum", "Flag", "StrEnum"}


def render_sig(name: str, spec: "SigSpec") -> str:
    """Readable real signature, e.g. `set_flag(idn, index=..., selector=...)`.

    Annotated params carry their real type (`write_record: list[list[WriteRecordNode]]`)
    so the model copies the true container shape instead of guessing."""
    def _p(p: str, required: bool) -> str:
        ann = spec.annotations.get(p)
        out = f"{p}: {ann}" if ann else p
        return out if required else f"{out}=..."
    parts = [_p(p, i < spec.num_pos_required) for i, p in enumerate(spec.pos_params)]
    for k in sorted(spec.params - set(spec.pos_params)):     # keyword-only params
        parts.append(_p(k, k in spec.required_kwonly))
    if spec.has_varargs:
        parts.append("*args")
    if spec.has_kwargs:
        parts.append("**kwargs")
    return f"{name}({', '.join(parts)})"


def _build_struct_fields(root: Path) -> dict:
    """{ClassName: {field names}} for every class under api/.

    Fields = `self.<x> =` assignments in any method (descriptor structs set them in
    __init__/from_bytes) PLUS class-level `<x> =` assignments (bit accessors like
    `u8_write_booster = CHK_BIT(...)`). The basis for verifying struct attribute access —
    the gap api_grounding otherwise skips (attribute access needs this field table)."""
    base = root / "api"
    if not base.is_dir():
        return {}
    own: dict = {}      # class -> own fields (self.x=, class-level x=, @property)
    bases: dict = {}    # class -> [base class names]
    for py in base.rglob("*.py"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8-sig", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            fields: set = set()
            # self.<attr> = ... anywhere in the class
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                                and t.value.id == "self"):
                            fields.add(t.attr)
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Attribute):
                    if isinstance(sub.target.value, ast.Name) and sub.target.value.id == "self":
                        fields.add(sub.target.attr)
            for item in node.body:
                # class-level field / bit-accessor assignments
                if isinstance(item, ast.Assign):
                    fields |= {t.id for t in item.targets if isinstance(t, ast.Name)}
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
                # @property (and cached_property) — attribute-like access, not a method call
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for dec in item.decorator_list:
                        dname = dec.attr if isinstance(dec, ast.Attribute) else (
                            dec.id if isinstance(dec, ast.Name) else "")
                        if "property" in dname.lower():
                            fields.add(item.name)
            own.setdefault(node.name, set()).update(fields)
            bases.setdefault(node.name, []).extend(
                b.id for b in node.bases if isinstance(b, ast.Name))

    # Merge inherited fields transitively (a field on a base is valid on the subclass).
    def _collect(cls: str, seen: set) -> set:
        if cls in seen:
            return set()
        seen.add(cls)
        out = set(own.get(cls, ()))
        for b in bases.get(cls, ()):
            out |= _collect(b, seen)
        return out

    return {cls: _collect(cls, set()) for cls in own}


def resolve_fields(index: dict, type_name: str) -> set:
    """Field set for a return/struct type name. Exact class match, else merge classes that
    share the type stem (e.g. `ExtendedWriteBoosterSupportUnion` -> `ExtendedWriteBoosterSupport*`),
    else empty set."""
    if not type_name:
        return set()
    structs = index.get("_structs", {})
    if type_name in structs:
        return set(structs[type_name])
    stem = type_name
    for suf in ("Union", "ABC"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
    merged: set = set()
    for cname, fields in structs.items():
        if cname == stem or cname.startswith(stem):
            merged |= fields
    return merged


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
                tree = ast.parse(py.read_text(encoding="utf-8-sig", errors="ignore"))
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
            symbols=_module_exports(api_init, cache, set(), root=root),
            all_names=_walk_all_names(root / "api"),
        )
    if cmdseq_init.is_file():
        index["ExecuteCMD"] = Namespace(
            symbols=_module_exports(cmdseq_init, cache, set(), root=root),
            all_names=_walk_all_names(root / "api" / "cmd_seq"),
        )
    if lib_file.is_file():
        index["lib"] = Namespace(
            symbols=_module_exports(lib_file, cache, set(), root=root),
            all_names=_walk_all_names(root / "lib"),
        )
    index["_enums"] = _build_enum_index(root)   # not a namespace alias; see check_api_calls
    structs = _build_struct_fields(root)        # for struct-field FEED + CATCH
    index["_structs"] = structs
    index["_all_struct_fields"] = (
        frozenset().union(*structs.values()) if structs else frozenset())
    index["_root"] = str(root)                  # for star-import resolution (check_bare_names)
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


@functools.lru_cache(maxsize=8)
def _cached_call_sites(script_root_str: str) -> dict:
    """{callee_name: [(rel_path, lineno), ...]} — every call site in Script.

    The FEED complement of the IDIOM & SELECTION rule: instead of hoping the model
    reverse-looks-up real callers itself (gitnexus `cypher` — advisory, easily skipped),
    prepare computes them here and injects them, so "read a real caller" becomes
    "open the file:line already printed in your prompt". One entry per (file, name):
    the FIRST call in a file (distinct files > repeat hits — idiom evidence wants
    diversity). Directories named `generated` are EXCLUDED: generated patterns are this
    pipeline's own output — feeding them back as caller evidence would let a wrong
    generated idiom certify the next generation (self-poisoning)."""
    root = Path(script_root_str)
    if not root.exists():
        return {}
    sites: dict = {}
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root)
        if "generated" in rel.parts:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8-sig", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        rel_str = rel.as_posix()
        seen_here: set = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else (
                f.id if isinstance(f, ast.Name) else None)
            if not name or name in seen_here:
                continue
            seen_here.add(name)
            sites.setdefault(name, []).append((rel_str, node.lineno))
    return sites


def build_call_sites(script_root) -> dict:
    """Public cached accessor for the call-site reverse index (see _cached_call_sites)."""
    return _cached_call_sites(str(script_root))


def _caller_rank(site: tuple) -> tuple:
    """Sort key: sample_code (curated idioms) > real pattern/ callers > library-internal."""
    path = site[0]
    if "pattern/sample_code/" in path:
        pri = 0
    elif path.startswith("pattern/"):
        pri = 1
    else:
        pri = 2
    return (pri, path, site[1])


def api_facts(script_root, symbol_names=(), query: str = "", max_enums: int = 8,
              call_sites: dict | None = None) -> list:
    """Authoritative facts to inject into a unit prompt (possibly empty).

    * exact signature for each candidate `symbol_names` found in api/ExecuteCMD/lib;
    * valid members of every enum whose class-name shares a (non-generic) token with
      the unit query or a candidate symbol — so the model copies the real member;
    * with `call_sites` (build_call_sites), a `real callers of X():` line per matched
      symbol (top 3, sample_code > pattern > rest) — the caller-idiom evidence FED
      instead of relying on the model to reverse-look-it-up itself.

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
                # struct fields of the return type, so the model copies the real field
                # (e.g. l18_…/u0_…) instead of guessing (e.g. l85_…). Capped to stay concise.
                if spec.returns:
                    rf = sorted(resolve_fields(index, spec.returns))
                    if rf:
                        shown = ", ".join(rf[:30]) + (f", … (+{len(rf) - 30} more)"
                                                      if len(rf) > 30 else "")
                        facts.append(f"{spec.returns} fields (from {n}()): {shown}")
                hits = (call_sites or {}).get(n) or []
                if hits:
                    top = sorted(hits, key=_caller_rank)[:3]
                    facts.append("real callers of {}(): {}".format(
                        n, ", ".join(f"{p}:{ln}" for p, ln in top)))
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
            owner = resolve_bare_name(ename, index)
            shown = f"{owner}.{ename}" if owner else ename
            facts.append(f"{shown} valid members: {', '.join(sorted(members))}")
    return facts


# ---------------------------------------------------------------------------
# Public: check a generated source against the index
# ---------------------------------------------------------------------------

def _membership_issue(alias: str, name: str, index: dict, lineno: int,
                      is_call: bool) -> dict:
    """Issue for `alias.name` absent from alias's namespace: `wrong_namespace` when the
    symbol unambiguously lives under ANOTHER scaffold alias (detail = the exact fix, so
    the repair prompt carries the resolution, not just the error), else `unknown_symbol`."""
    other = resolve_bare_name(name, index)
    if other and other != alias:
        form = f"{other}.{name}(...)" if is_call else f"{other}.{name}"
        return {"alias": alias, "symbol": name, "kind": "wrong_namespace",
                "detail": (f"{alias}.{name} — this symbol lives under "
                           f"{_ALIAS_HOME[other]}; write {form}"),
                "line": lineno}
    issue = {"alias": alias, "symbol": name, "kind": "unknown_symbol",
             "detail": f"{alias}.{name} not found in Script", "line": lineno}
    ns = index.get(alias)
    near = difflib.get_close_matches(name, ns.symbols.keys(), n=1, cutoff=0.7) if ns else []
    if near:
        issue["suggestion"] = near[0]
    return issue


def check_api_calls(py_source: str, index: dict) -> list:
    """Return a list of issue dicts for namespace usage that doesn't match Script.

    Each issue: {alias, symbol, kind, detail, line, [suggestion]}.
    kind in {"unknown_symbol", "wrong_namespace", "unknown_kwarg",
    "too_many_positional", "missing_required_arg", "unknown_enum_member"}.
    Covers `alias.X(...)` calls AND non-call `alias.X` attribute access (so a
    wrong-prefix enum like `lib.Dcmd5ResetType.HW_RESET` is caught too)."""
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []          # syntax errors are reported separately by validate()

    issues: list = []
    checked_funcs: set = set()   # id() of alias-Attribute nodes handled as call funcs
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
            continue
        alias = func.value.id
        if alias not in NAMESPACE_ALIASES or alias not in index:
            continue
        checked_funcs.add(id(func))
        ns = index[alias]
        name = func.attr

        if name not in ns.symbols:
            if name in ns.all_names:
                continue   # exists somewhere; resolver just didn't reach it — skip
            issues.append(_membership_issue(alias, name, index, node.lineno, is_call=True))
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

    # Non-call alias attribute access (`lib.Dcmd5ResetType.HW_RESET`, `api.SOME_CONST`) —
    # the wrong prefix on an attribute chain was previously never questioned.
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        if id(node) in checked_funcs:
            continue                       # already validated as a call above
        alias = node.value.id
        if alias not in NAMESPACE_ALIASES or alias not in index:
            continue
        ns = index[alias]
        name = node.attr
        if name in ns.symbols or name in ns.all_names:
            continue
        issues.append(_membership_issue(alias, name, index, node.lineno, is_call=False))

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


# ---------------------------------------------------------------------------
# Public: citation reality check (audit) — are the agent's `=== CODE REFS ===`
# self-reported, so an agent can fabricate a symbol AND a "(gitnexus rank1)"
# citation for it. The harmful case (a fake symbol USED in code) is caught by
# check_api_calls; this catches the fabricated CITATION itself (audit integrity).
# Conservative: flag only a citation whose symbol resolves NOWHERE in Script.
# ---------------------------------------------------------------------------

# `<path>.py:<symbol>` inside a code-ref line; symbol may be dotted (Class.method).
_CITATION_RE = re.compile(r"([\w/\\.\-]+\.py)\s*:\s*([A-Za-z_][\w.]*)")


@functools.lru_cache(maxsize=8)
def _all_script_names(script_root_str: str) -> frozenset:
    """Every IDENTIFIER that appears anywhere in Script source (def/class/method names,
    variable names, and attribute names).

    The whitelist for citation reality. It is deliberately broad — citations legitimately
    point not just at functions/classes but at methods (`printout_config_desc_header`),
    module vars (`param`), and struct/instance fields (`gLUCapacity`, `gMaxNumberLU`), none
    of which a def/class-only set contains. Verifying those precisely needs type inference
    (which api_grounding avoids), so the audit instead asks the strong, FP-free question:
    does this cited token exist NOWHERE in the codebase? — which catches pure fabrications
    like `random_read_and_compare` (0 occurrences) without crying wolf on real fields.
    Empty frozenset if the root is absent."""
    root = Path(script_root_str)
    if not root.exists():
        return frozenset()
    names: set = set()
    for py in root.rglob("*.py"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(py.read_text(encoding="utf-8-sig", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
    return frozenset(names)


def check_citations(code_refs, script_root) -> list:
    """Flag `=== CODE REFS ===` lines that cite a symbol existing NOWHERE in Script.

    Reuses the AST view of Script (same source of truth as check_api_calls). Lines
    with no `path.py:symbol` citation (prose like 'No API calls needed', `src[wiki]:`,
    `NO MATCH`) are skipped. Conservative — a citation passes if ANY dotted component
    of its symbol is a known Script name, so legit `Script/pattern/...:Pattern.step1`
    is never flagged; pure fabrications (`random_read_and_compare`) are. Returns the
    standard issue-dict shape (line 0 — citations are metadata, not source lines)."""
    if not script_root:
        return []
    known = _all_script_names(str(script_root))
    if not known:
        return []
    issues: list = []
    for ref in code_refs or []:
        m = _CITATION_RE.search(ref or "")
        if not m:
            continue
        path, symbol = m.group(1), m.group(2)
        components = symbol.split(".")
        if any(c in known for c in components):
            continue   # at least one component is a real Script symbol
        issue = {"alias": "citation", "symbol": symbol, "kind": "citation_unknown_symbol",
                 "detail": f"cited symbol '{symbol}' ({path}) does not exist in Script "
                           f"(fabricated grounding citation)", "line": 0}
        near = difflib.get_close_matches(components[-1], known, n=1, cutoff=0.7)
        if near:
            issue["suggestion"] = near[0]
        issues.append(issue)
    return issues


def _ns_call_return(call: ast.Call, index: dict) -> str:
    """Return-type stem of an `api.F()/ExecuteCMD.F()/lib.F()` call, else ''."""
    f = call.func
    if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            and f.value.id in NAMESPACE_ALIASES):
        ns = index.get(f.value.id)
        spec = ns.symbols.get(f.attr) if ns else None
        return getattr(spec, "returns", "") if spec else ""
    return ""


def _is_struct_type(index: dict, rtype: str) -> bool:
    return bool(rtype) and (bool(resolve_fields(index, rtype))
                            or rtype.endswith(("Descriptor", "Support", "Header", "Union")))


def check_struct_fields(py_source: str, index: dict) -> list:
    """Flag `<x>.<attr>` where <x> is the result of a struct-returning api/lib call and <attr>
    is a field of NO Script struct (a fabricated descriptor field — the gap check_api_calls
    skips). Covers both `v = api.F(); v.attr` (var-origin, like semantic_checks) and the inline
    `api.F().attr`.

    Conservative / FP-safe: DIRECT single-hop only (skips `x[0].header.y` chains and `self.*`);
    flags only attrs absent from the GLOBAL field set, so real fields (`u0_…`) and method calls
    (`.append`) pass while blatant fabrications (`l85_…`) are caught."""
    if not index:
        return []
    all_fields = index.get("_all_struct_fields") or frozenset()
    if not all_fields:
        return []
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []

    issues: list = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # vars assigned more than once are untrustworthy (could be reassigned to another
        # type) -> exclude them, so we never flag a `.attr` on a since-reassigned var.
        assigned: set = set()
        multi: set = set()
        for node in ast.walk(fn):
            tgts: list = []
            if isinstance(node, ast.Assign):
                tgts = [t for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(
                    getattr(node, "target", None), ast.Name):
                tgts = [node.target]
            for t in tgts:
                (multi if t.id in assigned else assigned).add(t.id)

        # var -> (rtype, fields) for a SINGLE-assignment `var = api.F(...)` returning a struct
        origin: dict = {}
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id not in multi
                    and isinstance(node.value, ast.Call)):
                rtype = _ns_call_return(node.value, index)
                if _is_struct_type(index, rtype):
                    origin[node.targets[0].id] = (rtype, resolve_fields(index, rtype))

        for node in ast.walk(fn):
            if not (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)):
                continue
            attr = node.attr
            if attr.startswith("__") or attr in ("value", "name"):
                continue
            v = node.value
            if isinstance(v, ast.Name) and v.id in origin:        # var-origin: v.attr
                rtype, fields = origin[v.id]
            elif isinstance(v, ast.Call) and _is_struct_type(index, _ns_call_return(v, index)):
                rtype = _ns_call_return(v, index)                  # inline: api.F().attr
                fields = resolve_fields(index, rtype)
            else:
                continue
            # PRECISE when the return struct resolved to a field set: flag attr not on THAT
            # struct (catches right-field-wrong-struct, e.g. a DeviceDescriptor field read off
            # the WriteBooster-support union). When unresolved, fall back to the GLOBAL set
            # (only blatant fabrications). Either way real fields / methods pass.
            valid = fields if fields else all_fields
            if attr in valid:
                continue
            where = f"a field of {rtype}" if fields else "any Script struct field"
            issue = {"alias": "struct", "symbol": attr, "kind": "unknown_struct_field",
                     "detail": f"'.{attr}' is not {where}", "line": node.lineno}
            near = difflib.get_close_matches(attr, sorted(fields or all_fields), n=1, cutoff=0.7)
            if near:
                issue["suggestion"] = near[0]
            issues.append(issue)
    return issues


# ---------------------------------------------------------------------------
# Public: bare/undefined-name check — closes the blind spot that let a BARE
# `init_tester_to_unit_ready(...)` (copied from a star-importing reference pattern)
# and `_log.info(...)` produce ZERO findings: check_api_calls only inspects
# `alias.attr(...)`. PREVENT half = NAMESPACE_RULE (same table).
# ---------------------------------------------------------------------------

_BUILTIN_NAMES = frozenset(dir(builtins))


def _bound_names_from_import(node) -> set:
    """Names an import statement binds (asname-aware; `*` handled by the caller)."""
    out: set = set()
    if isinstance(node, ast.Import):
        for a in node.names:
            out.add(a.asname or a.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        for a in node.names:
            if a.name != "*":
                out.add(a.asname or a.name)
    return out


def _star_import_exports(node: ast.ImportFrom, root: Path, cache: dict) -> set | None:
    """Names bound by `from Script.x.y import *`; None when unresolvable OR incomplete.

    Incomplete = the module (or anything it transitively star-imports) contains a
    star import we could not resolve — its export set may be missing names, so the
    caller must suppress the whole bare-name check rather than flag on a partial
    picture (false-negative bias)."""
    if node.level:                 # relative — never emitted by generated/real patterns
        return None
    f = _resolve_script_absolute(root, node.module or "")
    if f is None:
        return None
    exports, complete = _module_exports_ex(f, cache, set(), root)
    if not complete or not exports:
        return None
    return set(exports)


def _bare_issue(name: str, lineno: int, index: dict, is_call: bool) -> dict:
    """Issue for a bare name that is not in scope. Detail = the deterministic fix.

    Stdlib module names win over alias resolution: some Script modules `import time`
    at top level (making `api.time` technically reachable via star re-export), but
    the RIGHT fix for a bare `time` is always `import time`, never `api.time`."""
    if name in sys.stdlib_module_names and not is_call:
        return {"alias": "", "symbol": name, "kind": "undefined_name",
                "detail": (f"name '{name}' is undefined — add 'import {name}' to "
                           f"=== EXTRA IMPORTS ==="), "line": lineno}
    alias = resolve_bare_name(name, index)
    if alias:
        form = f"{alias}.{name}(...)" if is_call else f"{alias}.{name}"
        return {"alias": alias, "symbol": name, "kind": "bare_name",
                "detail": (f"bare name '{name}' — the scaffold has no star import; "
                           f"write {form} (defined under {_ALIAS_HOME[alias]})"),
                "line": lineno}
    if name in sys.stdlib_module_names:
        return {"alias": "", "symbol": name, "kind": "undefined_name",
                "detail": (f"name '{name}' is undefined — add 'import {name}' to "
                           f"=== EXTRA IMPORTS ==="), "line": lineno}
    issue = {"alias": "", "symbol": name, "kind": "undefined_name",
             "detail": (f"name '{name}' is not defined (not a local, import, "
                        f"scaffold name, or Script symbol)"), "line": lineno}
    if name in ("_log", "log"):
        issue["suggestion"] = "logger"
    else:
        near = difflib.get_close_matches(name, sorted(SCAFFOLD_NAMES), n=1, cutoff=0.7)
        if near:
            issue["suggestion"] = near[0]
    return issue


def check_bare_names(py_source: str, index: dict, extra_imports=()) -> list:
    """Flag bare Script symbols and undefined names in function bodies.

    kind `bare_name`: the name resolves (via ALIAS_PRIORITY) to a scaffold namespace —
    the model copied a star-import idiom verbatim; the detail says the prefixed form.
    kind `undefined_name`: resolves nowhere — `_log` (suggest `logger`), a missing
    stdlib import (`time` -> "add 'import time'"), or a genuine typo.

    Conservative scope model (false-negative bias): builtins + SCAFFOLD_NAMES +
    self/cls + every module-level binding + all import statements anywhere in the
    source + `extra_imports` lines + per-function locals (params of the function AND
    anything nested, every Name-Store target, nested def/class names, global/nonlocal,
    except-handler names). `from Script.x import *` is resolved to its real exports via
    the index's script root; ANY unresolvable `import *` suppresses the whole check.
    Works on fragments (unit methods wrapped in a dummy class) and whole files alike.
    One finding per name (first occurrence)."""
    if not index:
        return []
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []

    root_str = index.get("_root", "")
    root = Path(root_str) if root_str else None
    cache: dict = {}
    known: set = set(_BUILTIN_NAMES) | set(SCAFFOLD_NAMES) | {"self", "cls"}

    # Imports: anywhere in the source (function-level imports over-approximate to
    # file scope — false-negative direction) + the unit's EXTRA IMPORTS lines.
    import_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    for line in extra_imports or ():
        try:
            sub = ast.parse(str(line))
        except SyntaxError:
            continue
        import_nodes.extend(n for n in sub.body if isinstance(n, (ast.Import, ast.ImportFrom)))
    for n in import_nodes:
        known |= _bound_names_from_import(n)
        if isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names):
            exports = _star_import_exports(n, root, cache) if root else None
            if exports is None:
                return []      # unresolvable star import — bare names may be legal; stay silent
            known |= exports

    for n in tree.body:        # module-level bindings
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            known.add(n.name)
        elif isinstance(n, ast.Assign):
            known |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            known.add(n.target.id)

    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    nested: set = set()
    for f in funcs:
        for sub in ast.walk(f):
            if sub is not f and isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested.add(id(sub))

    issues: list = []
    reported: set = set()
    for fn in funcs:
        if id(fn) in nested:
            continue           # checked as part of its enclosing function
        local = set(known)
        for sub in ast.walk(fn):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local.add(sub.name)
                a = sub.args
                for arg in (list(getattr(a, "posonlyargs", [])) + list(a.args)
                            + list(a.kwonlyargs)):
                    local.add(arg.arg)
                if a.vararg:
                    local.add(a.vararg.arg)
                if a.kwarg:
                    local.add(a.kwarg.arg)
            elif isinstance(sub, ast.ClassDef):
                local.add(sub.name)
            elif isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
                local.add(sub.id)
            elif isinstance(sub, (ast.Global, ast.Nonlocal)):
                local.update(sub.names)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                local.add(sub.name)

        for sub in ast.walk(fn):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                nm = sub.func.id
                if nm not in local and nm not in reported:
                    reported.add(nm)
                    issues.append(_bare_issue(nm, sub.lineno, index, is_call=True))
            elif (isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name)
                  and isinstance(sub.value.ctx, ast.Load)):
                nm = sub.value.id
                if nm not in local and nm not in reported:
                    reported.add(nm)
                    issues.append(_bare_issue(nm, sub.lineno, index, is_call=False))
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
