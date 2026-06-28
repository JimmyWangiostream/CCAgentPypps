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
