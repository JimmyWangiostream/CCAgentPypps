"""Per-unit gate (Q1): the SAME deterministic checks the final gate runs, run on one
unit's methods so bugs are caught at generation, not at end-stage review."""
from pattern_generator.unit_gate import check_unit, unit_findings


def _mini_script(tmp_path):
    root = tmp_path / "Script"
    (root / "api").mkdir(parents=True)
    # build_script_index requires api/__init__.py to recognise a Script root.
    # Re-export rw so bare-name resolution can see the symbols (as the real api does).
    (root / "api" / "__init__.py").write_text("from .rw import *\n", encoding="utf-8")
    (root / "api" / "rw.py").write_text(
        "def read_compare(write_record, compare_method=0):\n    pass\n", encoding="utf-8")
    return root


# A clean unit: real symbol, correct WB field, real citation.
GOOD = """\
    def step1(self) -> None:
        ext = api.get_extended_ufs_features_support()
        self.wb_supported = bool(ext.u8_write_booster)
"""

# A buggy unit: WB support read via the FFU bit (semantic, no Script lib needed).
BAD_SEMANTIC = """\
    def step1(self) -> None:
        ufs_feat = api.get_ufs_features_support()
        wb_supported = bool(ufs_feat.u0_ffu)
"""


def test_structure_flags_wrong_method_name():
    # Unit planned as step1, but emitted step2 -> missing step1 + unplanned step2.
    res = check_unit("    def step2(self) -> None:\n        pass\n", expected_methods=["step1"])
    msgs = " ".join(res["structure"])
    assert "missing planned method 'step1'" in msgs
    assert "unplanned method 'step2'" in msgs
    assert any("[structure]" in f for f in unit_findings(res))


def test_structure_clean_on_matching_name():
    res = check_unit("    def step1(self) -> None:\n        pass\n", expected_methods=["step1"])
    assert res["structure"] == []


def test_structure_skipped_without_expected_methods():
    # Back-compat: no expected_methods passed -> structure dimension inactive.
    res = check_unit("    def whatever(self) -> None:\n        pass\n")
    assert res["structure"] == []


def test_clean_unit_passes_semantic_without_script():
    res = check_unit(GOOD)
    assert unit_findings(res) == []


def test_semantic_bug_flagged_pure_ast():
    # semantic runs without a Script library (pure AST).
    res = check_unit(BAD_SEMANTIC)
    assert res["semantic"]
    assert any("u0_ffu" in m for m in res["semantic"])
    assert any("[semantic]" in line for line in unit_findings(res))


def test_fabricated_citation_flagged(tmp_path):
    root = _mini_script(tmp_path)
    res = check_unit(
        "    def step1(self) -> None:\n        api.read_compare(self.w)\n",
        code_refs=["Script/api/x.py:random_read_and_compare (gitnexus rank1)"],
        script_root=root,
    )
    assert res["citation"]
    assert any("random_read_and_compare" in m for m in res["citation"])


def test_unknown_api_symbol_flagged(tmp_path):
    root = _mini_script(tmp_path)
    res = check_unit(
        "    def step1(self) -> None:\n        api.totally_made_up(1)\n",
        script_root=root,
    )
    assert res["api"]
    assert any("totally_made_up" in m for m in res["api"])


def test_findings_are_dimension_tagged():
    lines = unit_findings(check_unit(BAD_SEMANTIC))
    assert all(line.startswith("[") for line in lines)


def test_bare_name_flagged_with_prefixed_fix(tmp_path):
    # the PF010_0310 class of bug: a BARE star-import idiom copied into a unit
    root = _mini_script(tmp_path)
    res = check_unit(
        "    def step1(self) -> None:\n        read_compare(self.w)\n",
        script_root=root,
    )
    assert any("write api.read_compare(...)" in m for m in res["api"])


def test_extra_imports_not_flagged(tmp_path):
    root = _mini_script(tmp_path)
    body = "    def step1(self) -> None:\n        x = cast(int, 1)\n"
    with_imports = check_unit(body, script_root=root,
                              extra_imports=["from typing import cast"])
    without = check_unit(body, script_root=root)
    assert with_imports["api"] == []
    assert any("cast" in m for m in without["api"])


def test_loop_idx_arity_enforced():
    body = "    def _loop1_step_1_1(self) -> None:\n        pass\n"
    res = check_unit(body, expected_methods=["_loop1_step_1_1"], loop_idx_required=True)
    assert any("(self, loop_idx)" in m for m in res["structure"])


def test_loop_idx_arity_clean():
    body = "    def _loop1_step_1_1(self, loop_idx) -> None:\n        pass\n"
    res = check_unit(body, expected_methods=["_loop1_step_1_1"], loop_idx_required=True)
    assert res["structure"] == []
