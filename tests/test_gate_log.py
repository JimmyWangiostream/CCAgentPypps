from pattern_generator.gate_log import append_record, format_record, log_path

FAIL_REPORT = {
    "syntax": "pass",
    "structure": ["method 'step1' is defined OUTSIDE the pattern class (...)"],
    "dataflow": "pass",
    "api_grounding": ["L207: api.random_read() missing required argument(s): cmd_count"],
}
PASS_REPORT = {"syntax": "pass", "structure": "pass", "dataflow": "pass",
               "api_grounding": "pass"}


def test_format_fail_lists_findings():
    block = format_record("PFX", "p.py", "finish", 2, FAIL_REPORT, timestamp="T")
    assert "## T — finish round 2 — FAIL  (p.py)" in block
    assert "- [structure] method 'step1' is defined OUTSIDE" in block
    assert "- [api_grounding] L207:" in block


def test_format_pass_no_findings():
    block = format_record("PFX", "p.py", "validate", None, PASS_REPORT, timestamp="T")
    assert "— validate — PASS" in block   # round omitted when None
    assert "(no findings)" in block


def test_append_accumulates_and_does_not_overwrite(tmp_path):
    p1 = append_record(tmp_path, "PFX", "p.py", "finish", 1, FAIL_REPORT, timestamp="T1")
    p2 = append_record(tmp_path, "PFX", "p.py", "finish", 2, PASS_REPORT, timestamp="T2")
    assert p1 == p2 == log_path(tmp_path, "PFX")
    text = p1.read_text(encoding="utf-8")
    # both entries present, in order, under one title
    assert text.count("# Gate log — PFX") == 1
    assert "T1 — finish round 1 — FAIL" in text
    assert "T2 — finish round 2 — PASS" in text
    assert text.index("T1") < text.index("T2")


def test_append_creates_dir(tmp_path):
    sub = tmp_path / "gate_logs"
    append_record(sub, "PFY", "q.py", "validate", None, PASS_REPORT, timestamp="T")
    assert (sub / "PFY.gate_log.md").exists()
