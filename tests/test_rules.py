from pattern_generator.rules import RULES, Rule, select_rules, format_rules


def test_rules_have_unique_ids():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))
    assert all(isinstance(r, Rule) and r.keywords for r in RULES)


def test_select_query_vs_descriptor():
    text = "step3 READ ATTRIBUTE (dExtendedUFSFeaturesSupport) confirm WB bit"
    ids = {r.id for r in select_rules(text)}
    assert "query-vs-descriptor" in ids


def test_select_volatile_flag_on_reset():
    ids = {r.id for r in select_rules("verify fWriteBoosterEn after reset")}
    assert "volatile-flag-assert" in ids


def test_select_via_extra_terms():
    # nothing in the bare text, but IR cmd tokens carry the signal
    ids = {r.id for r in select_rules("do thing", extra_terms=("write(10)",))}
    assert "lba-pool-dedup" in ids


def test_format_includes_id_and_body():
    rules = select_rules("read attribute dExtendedUFSFeaturesSupport")
    out = format_rules(rules)
    assert "query-vs-descriptor" in out
    assert "get_extended_ufs_features_support" in out


def test_format_empty():
    assert "no domain rules" in format_rules([])
