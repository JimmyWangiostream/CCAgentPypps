from pattern_generator.review import build_review_prompt, _checkpoints, _ir_terms

IR = {
    "pattern_id": "PFX", "title": "WB test",
    "phases": [{"phase_id": "phase_0", "type": "sequential", "steps": [
        {"step_id": "s3", "name": "check WB support",
         "ufs_query": "READ ATTRIBUTE (dExtendedUFSFeaturesSupport)",
         "expected": "QUERY RESPONSE Success, WB bit set", "fail_condition": None},
        {"step_id": "s4", "name": "read compare",
         "scsi_cmd": "READ(10)", "expected": "GOOD Status, Data Match",
         "fail_condition": "NOT (GOOD Status, Data Match)", "on_fail": "abort"},
    ]}],
}

SRC = (
    "class P(UFSTC):\n"
    "    def step3(self) -> None:\n"
    "        d = api.get_device_descriptor().b84_write_booster_buffer_type\n"
)


def test_checkpoints_extracted():
    cps = _checkpoints(IR)
    ids = {c[0] for c in cps}
    assert ids == {"s3", "s4"}


def test_ir_terms_lowercased():
    terms = _ir_terms(IR)
    assert any("read attribute" in t for t in terms)
    assert any("read(10)" in t for t in terms)


def test_prompt_has_checkpoints_rules_and_code():
    p = build_review_prompt(SRC, IR)
    # checkpoint text
    assert "s3 (check WB support)" in p
    assert "Data Match" in p
    # rule selected from IR/source signal
    assert "query-vs-descriptor" in p
    assert "get_extended_ufs_features_support" in p
    # the raise/assert discipline instruction
    assert "raise api.PATTERN_ASSERT_" in p
    # the code itself, in a python block
    assert "```python" in p
    assert "b84_write_booster_buffer_type" in p


def test_prompt_demands_whole_file():
    p = build_review_prompt(SRC, IR)
    assert "COMPLETE corrected file" in p
