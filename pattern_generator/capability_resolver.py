"""Deterministic capability resolution over the api_grounding Script index.

Two jobs, both deterministic and version-aware — they replace name-similarity guessing
for the cases they can decide, and are conservative (fall back to the existing heuristic
FEED) for the cases they can't:

  1. version_gate(index, names, version)
       Drop a candidate accessor whose RETURN struct exists only on a version other than
       the target — e.g. `get_extended_write_booster_support` returns
       `ExtendedWriteBoosterSupport410` (UFS 4.1 only), so it is excluded on a 3.1 target.
       This kills the Hermes WriteBooster bug at its source on the right version.

  2. canonical_symbols(canonical_facts)
       The accessor names a canonical idiom points at (parsed from
       `api.get_extended_ufs_features_support().u8_write_booster`). Feeding these into the
       api_facts symbol list guarantees the CORRECT accessor's real signature + struct
       fields (incl. `u8_write_booster`) are injected — so the model has a concrete correct
       anchor instead of only the idiom prose + a wrong sibling's field list.

Single source of truth = the same `api_grounding` AST index used for FEED/CATCH.
"""
from __future__ import annotations

import ast
import re

from pattern_generator.ufs_version import struct_suffix

# `api.get_extended_ufs_features_support().u8_write_booster` -> ('get_..._support', 'u8_write_booster')
_ACCESSOR_FIELD_RE = re.compile(r"\bapi\.([a-z_][a-z0-9_]*)\(\)(?:\.([a-z_][a-z0-9_]*))?")
# A versioned struct class name: `<stem><NNN>` e.g. DeviceDescriptor410.
_VERSION_SUFFIX_RE = re.compile(r"^(.*?)(\d{3})$")

_ALIASES = ("api", "ExecuteCMD", "lib")


def canonical_symbols(canonical_facts) -> list:
    """Accessor names referenced by canonical-idiom facts, deduped, order-preserving."""
    syms: list = []
    for fact in canonical_facts or []:
        for m in _ACCESSOR_FIELD_RE.finditer(fact):
            syms.append(m.group(1))
    return list(dict.fromkeys(syms))


def _return_stem(index: dict, accessor: str) -> str:
    """Return-type name of an accessor in api/ExecuteCMD/lib, else ''."""
    for alias in _ALIASES:
        ns = index.get(alias)
        spec = ns.symbols.get(accessor) if ns else None
        if spec and getattr(spec, "returns", ""):
            return spec.returns
    return ""


def _struct_family_versions(index: dict, type_name: str) -> set:
    """Version suffixes present for a struct family, e.g. `ExtendedUFSFeaturesSupportUnion`
    -> {'310','400','410'}; `ExtendedWriteBoosterSupportUnion` -> {'410'}. Empty when the
    family is not versioned (no `<stem><NNN>` classes) or unknown."""
    stem = type_name
    for suf in ("Union", "ABC"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
    if not stem:
        return set()
    versions: set = set()
    for cname in index.get("_structs", {}):
        m = _VERSION_SUFFIX_RE.match(cname)
        if m and m.group(1) == stem:
            versions.add(m.group(2))
    return versions


def symbol_version_ok(index: dict, accessor: str, version) -> bool:
    """False iff `accessor`'s return struct family exists but NOT for the target version
    (so calling it on that version would raise at runtime). True when there is no target
    version, the family is non-versioned, or the target variant exists."""
    suf = struct_suffix(version)
    if not suf:
        return True                       # no target version -> no gating
    versions = _struct_family_versions(index, _return_stem(index, accessor))
    if not versions:
        return True                       # non-versioned / unknown -> allow (conservative)
    return suf in versions


def version_gate(index: dict, symbol_names, version) -> tuple:
    """Split candidate symbols into (kept, dropped) by target-version availability."""
    kept: list = []
    dropped: list = []
    for n in symbol_names:
        (kept if symbol_version_ok(index, n, version) else dropped).append(n)
    return kept, dropped


def check_version_availability(py_source: str, index: dict, version) -> list:
    """CATCH (validator side): flag `api./ExecuteCMD./lib.X()` calls whose accessor returns a
    struct unavailable on the target `version` — the FEED-side complement of version_gate.
    Issue-dict shape matches check_api_calls so the gate/format_issues handle it unchanged."""
    if not version or not index:
        return []
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []
    suf = struct_suffix(version)
    issues: list = []
    seen: set = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id in _ALIASES):
            continue
        name = f.attr
        if name in seen or symbol_version_ok(index, name, version):
            continue
        seen.add(name)
        issues.append({
            "alias": f.value.id, "symbol": name, "kind": "version_unavailable",
            "detail": (f"{f.value.id}.{name}() returns a struct with no *{suf} variant — it is "
                       f"unavailable on UFS {version} (newer-spec-only); use the "
                       "version-appropriate accessor"),
            "line": node.lineno,
        })
    return issues
