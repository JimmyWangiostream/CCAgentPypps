"""Grounding-consistency lint — does the wiki's MACHINE FACTS match the real Script code?

The structural lint (`wiki_retrieval.lint`) checks the wiki's shape (links, frontmatter,
staleness). This is the FACTUAL layer: the wiki is injected into every generation prompt,
so a wrong machine-fact silently teaches the model the wrong thing. The bug that motivated
this: `entities/device-descriptor.md` said WriteBooster support = `dExtendedUFSFeaturesSupport`
**bit[0]**, but the real struct `ExtendedUFSFeaturesSupport` has `u0_ffu` at bit 0 and
`u8_write_booster` at bit 8 — the wiki was teaching the exact `u0_ffu` confusion its sibling
idiom warns about, and no lint could see it.

Source of truth = the `pattern_generator.api_grounding` AST index over Script (struct fields,
enum members, namespace symbols). The wiki's machine facts are checked AGAINST it; code wins.

Three deterministic checks (conservative — false-negatives over false-positives, like
api_grounding):
  * bit_mismatch      — `bit[N]=<Feature>` where a struct field names that feature at a
                        DIFFERENT bit (the device-descriptor case). High confidence -> error.
  * unknown_struct_field — a `u8_write_booster`-style field token that is on NO Script struct.
  * unknown_api       — an `api.NAME(` / `ExecuteCMD.NAME(` / `lib.NAME(` whose NAME resolves
                        to no Script symbol (fabricated API taught by the wiki).

Findings reuse the structural-lint dict shape: {level, kind, page, detail}.
"""
from __future__ import annotations

import re
from pathlib import Path

from wiki_retrieval.corpus import DEFAULT_WIKI, load_doc

# Dirs whose pages carry machine facts worth checking against code.
_FACT_DIRS = ("concepts", "entities", "sources", "VC")

# A struct-style field token: prefix letter + offset digits + _ + snake name.
# Matches `u8_write_booster`, `l85_num_shared_write_booster_buffer_alloc_units`,
# `b12_max_number_lu`. Does NOT match spec names like `dExtendedUFSFeaturesSupport`
# (no digit after the prefix) — those are described in prose, not as struct fields.
_FIELD_TOKEN_RE = re.compile(r"\b([bwlqu]\d+_[a-z][a-z0-9_]*)\b")

# A bitmap field: `u<N>_<name>` -> (bit N, name). Only `u` fields are single-bit flags.
_UBIT_RE = re.compile(r"^u(\d+)_(.+)$")

# A wiki bit claim: `bit[0]=WriteBooster`, `- **bit[0]**: WriteBooster supported`.
# Captures the bit index and the following feature phrase (up to , | ( newline).
_BIT_CLAIM_RE = re.compile(r"bit\[(\d+)\]\**\s*[:=]\s*\**\s*([A-Za-z][A-Za-z0-9 /]{2,40})")

# A namespace API call written in the wiki: `api.get_device_descriptor(`.
_WIKI_API_RE = re.compile(r"\b(api|ExecuteCMD|lib)\.([a-z_][a-z0-9_]*)\s*\(")

# Feature keys shorter than this are too generic to match without false positives
# (ffu/psa/hid). We deliberately skip them — the high-value traps (writebooster,
# fastrecovery, ...) are all longer.
_MIN_FEATURE_KEY = 5


def _norm(s: str) -> str:
    """Lowercase, keep only a-z0-9 (drops spaces/underscores)."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def build_field_bits(index: dict) -> dict:
    """{normalized_feature_name: {bit indices}} from every `u<N>_<name>` struct field.

    e.g. `u8_write_booster` -> {'writebooster': {8}}, `u0_ffu` -> {'ffu': {0}}."""
    out: dict = {}
    for fields in (index.get("_structs") or {}).values():
        for f in fields:
            m = _UBIT_RE.match(f)
            if not m:
                continue
            out.setdefault(_norm(m.group(2)), set()).add(int(m.group(1)))
    return out


def check_bit_positions(body: str, field_bits: dict) -> list:
    """Flag `bit[N]=<Feature>` claims that contradict the struct's bit for that feature.

    Conservative: only fires when the feature phrase CONTAINS a known field key
    (len >= _MIN_FEATURE_KEY) and the claimed bit is not among that field's real bits."""
    issues: list = []
    for m in _BIT_CLAIM_RE.finditer(body or ""):
        claimed = int(m.group(1))
        phrase = _norm(m.group(2))
        # longest field key that is a substring of the claimed feature phrase
        best = ""
        for key in field_bits:
            if len(key) >= _MIN_FEATURE_KEY and key in phrase and len(key) > len(best):
                best = key
        if not best:
            continue
        real = field_bits[best]
        if claimed not in real:
            bits = sorted(real)
            issues.append({
                "kind": "wiki_bit_mismatch",
                "detail": (f"bit[{claimed}]={m.group(2).strip()} contradicts Script: "
                           f"'{best}' is at bit {bits[0] if len(bits) == 1 else bits}, "
                           f"not {claimed}"),
            })
    return issues


def check_struct_field_tokens(body: str, all_fields) -> list:
    """Flag `u8_write_booster`-style tokens that are on NO Script struct (fabricated field)."""
    if not all_fields:
        return []
    issues: list = []
    seen: set = set()
    for m in _FIELD_TOKEN_RE.finditer(body or ""):
        tok = m.group(1)
        if tok in seen or tok in all_fields:
            continue
        seen.add(tok)
        issues.append({
            "kind": "wiki_unknown_struct_field",
            "detail": f"cites struct field '{tok}' found on no Script struct",
        })
    return issues


def check_namespace_apis(body: str, index: dict) -> list:
    """Flag `api./ExecuteCMD./lib.NAME(` whose NAME resolves to no Script symbol."""
    issues: list = []
    seen: set = set()
    for m in _WIKI_API_RE.finditer(body or ""):
        alias, name = m.group(1), m.group(2)
        if (alias, name) in seen:
            continue
        ns = index.get(alias)
        if not ns:
            continue
        if name in ns.symbols or name in ns.all_names:
            continue
        seen.add((alias, name))
        issues.append({
            "kind": "wiki_unknown_api",
            "detail": f"cites {alias}.{name}() which resolves to no Script symbol",
        })
    return issues


def lint_wiki_grounding(wiki_root=None, script_root=None) -> list:
    """Cross-check wiki machine-facts against the Script api_grounding index.

    Returns [] (no findings) if the Script index can't be built (graceful — the
    structural lint still runs). Each finding: {level, kind, page, detail}."""
    # Imported lazily: the structural lint must stay pure-wiki with no Script dependency.
    from pattern_generator.api_grounding import build_script_index

    if not script_root:
        return []
    index = build_script_index(script_root)
    if not index:
        return []

    root = Path(wiki_root) if wiki_root else DEFAULT_WIKI
    field_bits = build_field_bits(index)
    all_fields = index.get("_all_struct_fields") or frozenset()

    findings: list = []
    for layer_dir in _FACT_DIRS:
        d = root / layer_dir
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            doc = load_doc(md, layer_dir)
            raw = [
                *(dict(f, level="error") for f in check_bit_positions(doc.body, field_bits)),
                *(dict(f, level="warn") for f in check_struct_field_tokens(doc.body, all_fields)),
                *(dict(f, level="warn") for f in check_namespace_apis(doc.body, index)),
            ]
            for f in raw:
                f["page"] = doc.path
                findings.append(f)
    return findings
