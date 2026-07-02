import re
import sys

import pytest

from pattern_generator.rules import select_refs, format_refs, all_ref_names


def test_refs_are_shipped():
    names = all_ref_names()
    assert names  # the review_refs/ docs are present
    assert "step03-query-vs-descriptor-trap" in names
    assert "volatile-flag-assert-discipline" in names


def test_select_query_vs_descriptor():
    refs = select_refs("step3 READ ATTRIBUTE (dExtendedUFSFeaturesSupport) confirm WB bit")
    names = {stem for stem, _ in refs}
    assert "step03-query-vs-descriptor-trap" in names


def test_select_volatile_flag_on_reset():
    refs = select_refs("verify fWriteBoosterEn after reset")
    names = {stem for stem, _ in refs}
    assert "volatile-flag-assert-discipline" in names


def test_select_via_extra_terms():
    # nothing in the bare text, but IR cmd tokens carry the signal
    refs = select_refs("do thing", extra_terms=("writebooster ssu reset",))
    assert refs  # a matching doc is selected from the extra IR terms


def test_select_caps_results():
    # a broad query that hits many docs is still capped
    refs = select_refs("writebooster ssu reset flag attribute descriptor lba", cap=3)
    assert len(refs) <= 3


def test_select_returns_only_hits():
    # BM25 returns score>0 only -> a query with no domain keyword selects nothing
    assert select_refs("qqqzzz xyzzy nonexistent") == []


def test_format_includes_stem_and_body():
    out = format_refs(select_refs("read attribute dExtendedUFSFeaturesSupport"))
    assert "step03-query-vs-descriptor-trap" in out
    assert "get_extended_ufs_features_support" in out


def test_format_empty():
    assert "no matching review references" in format_refs([])


def test_review_refs_use_canonical_alias_prefixes():
    """Pollution lint: a review_refs doc must never quote a Script symbol under a
    NON-scaffold alias (the `idv.init_tester_to_unit_ready` incident — a hallucinated
    prefix baked into a committed doc, copied verbatim into repair prompts, teaching
    the model wrong prefixes). Flags `X.symbol(` where X is not api/ExecuteCMD/lib
    (nor self/cls/a stdlib module) but `symbol` resolves to a scaffold namespace —
    such a form is never legitimate, not even as a 'before' example."""
    from pattern_generator.api_grounding import (
        NAMESPACE_ALIASES, build_script_index, resolve_bare_name,
    )
    from pattern_generator.config import PGConfig
    from pattern_generator.rules import REFS_DIR

    index = build_script_index(PGConfig().script_root)
    if not index:
        pytest.skip("Script library not present")

    ok_bases = set(NAMESPACE_ALIASES) | {"self", "cls"} | set(sys.stdlib_module_names)
    call_re = re.compile(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(")
    offenders: list = []
    for md in sorted(REFS_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in call_re.finditer(text):
            base, symbol = m.group(1), m.group(2)
            if base in ok_bases:
                continue
            alias = resolve_bare_name(symbol, index)
            if alias:
                offenders.append(f"{md.name}: '{base}.{symbol}(' — write {alias}.{symbol}(...)")
    assert not offenders, "non-canonical alias prefix in review_refs:\n" + "\n".join(offenders)
