"""Tests for the target-UFS-version channel (pattern_generator.ufs_version)."""
from pattern_generator.ufs_version import (
    normalize, struct_suffix, project_default, resolve,
)


def test_normalize_dotted():
    assert normalize("3.1") == "3.1"
    assert normalize("UFS 4.1") == "4.1"
    assert normalize("v4.0") == "4.0"


def test_normalize_suffix_and_hex():
    assert normalize("310") == "3.1"
    assert normalize("410") == "4.1"
    assert normalize("0x0410") == "4.1"
    assert normalize("0410") == "4.1"


def test_normalize_unknown_and_blank():
    assert normalize("") is None
    assert normalize(None) is None
    assert normalize("5.0") is None
    assert normalize("garbage") is None


def test_struct_suffix():
    assert struct_suffix("3.1") == "310"
    assert struct_suffix("4.1") == "410"
    assert struct_suffix("UFS 4.0") == "400"
    assert struct_suffix("nope") is None


def test_project_default_reads_target_md(tmp_path):
    (tmp_path / "target.md").write_text("# Target\n\nufs_version: 3.1\n", encoding="utf-8")
    assert project_default(tmp_path) == "3.1"


def test_project_default_absent(tmp_path):
    assert project_default(tmp_path) is None


def test_resolve_priority(tmp_path):
    (tmp_path / "target.md").write_text("ufs_version: 4.1\n", encoding="utf-8")
    # TC frontmatter (ir) beats project default
    assert resolve({"ufs_version": "3.1"}, wiki_root=tmp_path) == "3.1"
    # explicit override beats both
    assert resolve({"ufs_version": "3.1"}, wiki_root=tmp_path, override="4.0") == "4.0"
    # falls back to project default when TC is silent
    assert resolve({"ufs_version": ""}, wiki_root=tmp_path) == "4.1"
    # nothing anywhere -> None
    assert resolve({}, wiki_root=tmp_path / "nope") is None


def test_parser_extracts_ufs_version(tmp_path):
    from ir_generator.parser import parse_tc
    tc = tmp_path / "tc.md"
    tc.write_text(
        '---\ntitle: PF999_0001 X\nufs_version: "3.1"\ntags: [a]\n---\n\n'
        '## Phase 0 — P\n\n### Step 0.1: do\n**UFS QUERY**: `READ DESCRIPTOR (0x07)`\n',
        encoding="utf-8")
    ir = parse_tc(tc)
    assert ir["ufs_version"] == "3.1"
