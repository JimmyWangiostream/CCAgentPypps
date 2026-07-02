"""Citation reality check (Defect C): the agent's `=== CODE REFS ===` lines must cite
real Script symbols; a fabricated `(gitnexus rank1)` citation is flagged for audit."""
from pattern_generator.api_grounding import check_citations


def _mini_script(tmp_path):
    """A tiny Script root with a few known top-level symbols."""
    root = tmp_path / "Script"
    (root / "api").mkdir(parents=True)
    (root / "api" / "rw.py").write_text(
        "def read_compare(write_record, compare_method=0):\n    pass\n", encoding="utf-8")
    (root / "api" / "enums.py").write_text(
        "class FlagIDN:\n    WRITEBOOSTER_EN = 0x0E\n", encoding="utf-8")
    (root / "api" / "sample.py").write_text(
        "class Pattern:\n    def step1(self):\n        pass\n", encoding="utf-8")
    return root


def test_fabricated_citation_flagged(tmp_path):
    # The actual Hermes citation: a symbol that exists nowhere in Script.
    refs = ["Script/api/ufs_api/scsi/sequential_functions.py:random_read_and_compare (gitnexus rank1)"]
    issues = check_citations(refs, _mini_script(tmp_path))
    assert len(issues) == 1
    assert issues[0]["kind"] == "citation_unknown_symbol"
    assert "random_read_and_compare" in issues[0]["detail"]


def test_real_citations_clean(tmp_path):
    refs = [
        "Script/api/rw.py:read_compare (gitnexus rank1)",
        "Script/api/enums.py:FlagIDN (gitnexus rank2)",
        # dotted Class.method — passes because the class is a known symbol
        "Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 (gitnexus rank3)",
    ]
    assert check_citations(refs, _mini_script(tmp_path)) == []


def test_non_citation_lines_ignored(tmp_path):
    refs = [
        "No API calls needed for pure time.sleep delay",
        "NO MATCH",
        "src[wiki]: default.md",
        "- entities/write-booster.md - WriteBooster flag enabling",
    ]
    assert check_citations(refs, _mini_script(tmp_path)) == []


def test_noop_without_script_root():
    assert check_citations(["x.py:foo"], None) == []
    assert check_citations(["x.py:foo"], "") == []
