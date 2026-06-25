"""Tests for pattern_generator.assemble: _parse_unit_methods and assemble_pattern."""
import pytest
from pathlib import Path
from pattern_generator.assemble import (
    _parse_unit_methods, _parse_phase_methods, assemble_pattern,
)

SCAFFOLD = """\
import package_root
from Script import api
# @@EXTRA_IMPORTS@@


class MyPattern(UFSTC):
    def pre_process(self) -> None:
        pass

    # @@PHASE_METHODS@@

    def post_process(self) -> None:
        pass


if __name__ == '__main__':
    MyPattern().run()
"""

UNIT_0 = """\
=== WIKI REFS ===
- entities/scsi-commands.md — TEST UNIT READY
=== CODE REFS ===
- Script/api/cmd_seq/cmds.py: TestUnitReady (gitnexus rank1)
- Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus rank2)
=== REVIEW FLAGS ===
=== EXTRA IMPORTS ===
import random
=== METHODS ===
    def step1(self) -> None:
        pass

    def step2(self) -> None:
        self.max_lba = 1000
"""

UNIT_LOOP = """\
=== WIKI REFS ===
- entities/write-booster.md
=== CODE REFS ===
- NO MATCH
=== REVIEW FLAGS ===
TODO-REVIEW-NO-CODE-REF
=== EXTRA IMPORTS ===
=== METHODS ===
    def step3(self) -> None:
        # TODO-REVIEW-NO-CODE-REF
        for _ in range(10):
            pass  # TODO human-confirm: WRITEBOOSTER_EN not found
"""

UNIT_BOTH_MISS = """\
=== WIKI REFS ===
NO MATCH
=== CODE REFS ===
NO MATCH
=== REVIEW FLAGS ===
TODO-REVIEW-BOTH-MISS
=== EXTRA IMPORTS ===
=== METHODS ===
    def step4(self) -> None:
        import time; time.sleep(1)  # TODO-REVIEW-BOTH-MISS
"""


# ---------------------------------------------------------------------------
# _parse_unit_methods
# ---------------------------------------------------------------------------

class TestParseUnitMethods:

    def test_wiki_and_code_refs_captured(self):
        u = _parse_unit_methods(UNIT_0)
        assert any("scsi-commands" in r for r in u.wiki_refs)
        assert len(u.code_refs) == 2
        assert any("TestUnitReady" in r for r in u.code_refs)

    def test_review_flag_parsed(self):
        u = _parse_unit_methods(UNIT_LOOP)
        assert u.review_flags == ["TODO-REVIEW-NO-CODE-REF"]

    def test_no_match_detection(self):
        u = _parse_unit_methods(UNIT_BOTH_MISS)
        assert u.is_no_match(u.wiki_refs)
        assert u.is_no_match(u.code_refs)
        assert u.review_flags == ["TODO-REVIEW-BOTH-MISS"]

    def test_extra_imports_parsed(self):
        u = _parse_unit_methods(UNIT_0)
        assert u.extra_imports == ["import random"]

    def test_methods_text_stripped(self):
        u = _parse_unit_methods(UNIT_0)
        assert u.methods.startswith("    def step1")
        assert "step2" in u.methods

    def test_legacy_grounding_log_tolerated_as_code(self):
        legacy = ("=== GROUNDING LOG ===\n"
                  "python graph_query.py TestUnitReady -> api/cmd_seq/cmds.py:299\n"
                  "=== METHODS ===\n    def step1(self): pass\n")
        u = _parse_unit_methods(legacy)
        assert any("TestUnitReady" in r for r in u.code_refs)

    def test_commented_grounding_log_lines_captured(self):
        # The hermes failure: every grounding-log line was a "# ..." comment and
        # got silently dropped, blanking the code refs.
        commented = ("=== GROUNDING LOG ===\n"
                     "# Step: step_0_3 (READ DEVICE DESCRIPTOR)\n"
                     "# Source: Script/api/.../functions.py — get_device_descriptor\n"
                     "=== METHODS ===\n    def step3(self): pass\n")
        u = _parse_unit_methods(commented)
        assert any("get_device_descriptor" in r for r in u.code_refs)
        assert not u.is_no_match(u.code_refs)

    def test_legacy_tuple_shim(self):
        code, imports, methods = _parse_phase_methods(UNIT_0)
        assert imports == ["import random"]
        assert "def step1" in methods
        assert len(code) == 2


# ---------------------------------------------------------------------------
# assemble_pattern
# ---------------------------------------------------------------------------

class TestAssemblePattern:

    def _setup(self, tmp_path: Path) -> Path:
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (tmp_path / "unit_01_phase_0_methods.py").write_text(UNIT_0, encoding="utf-8")
        (tmp_path / "unit_02_loop_4_methods.py").write_text(UNIT_LOOP, encoding="utf-8")
        return tmp_path

    def test_writes_pattern_file(self, tmp_path):
        self._setup(tmp_path)
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        assert (tmp_path / "MyTest.py").exists()

    def test_main_py_defaults_to_parent_of_run_dir(self, tmp_path):
        # By default the final .py goes to the generated/ base (run_dir.parent),
        # while by-products (retrieval_debug.md) stay in the run subfolder.
        run = tmp_path / "PF010_0310"
        run.mkdir()
        (run / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (run / "unit_01_phase_0_methods.py").write_text(UNIT_0, encoding="utf-8")
        assemble_pattern(run, "MyTest")          # no output_dir -> run.parent
        assert (tmp_path / "MyTest.py").exists()
        assert not (run / "MyTest.py").exists()
        assert (run / "retrieval_debug.md").exists()

    def test_writes_retrieval_debug(self, tmp_path):
        self._setup(tmp_path)
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        assert (tmp_path / "retrieval_debug.md").exists()

    def test_extra_imports_inserted(self, tmp_path):
        self._setup(tmp_path)
        src = assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        assert "import random" in src
        assert "# @@EXTRA_IMPORTS@@" not in src

    def test_methods_inserted(self, tmp_path):
        self._setup(tmp_path)
        src = assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        assert "def step1" in src and "def step2" in src and "def step3" in src
        assert "# @@PHASE_METHODS@@" not in src

    def test_import_deduplication(self, tmp_path):
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        dup = "=== EXTRA IMPORTS ===\nimport random\n=== METHODS ===\n    def step1(self): pass\n"
        (tmp_path / "unit_01_a_methods.py").write_text(dup, encoding="utf-8")
        (tmp_path / "unit_02_b_methods.py").write_text(dup, encoding="utf-8")
        src = assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        assert src.count("import random") == 1

    def test_raises_when_no_method_files(self, tmp_path):
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)

    def test_retrieval_debug_lists_refs_per_unit(self, tmp_path):
        self._setup(tmp_path)
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "unit_01_phase_0_methods.py" in dbg
        assert "TestUnitReady" in dbg          # code ref echoed
        assert "scsi-commands" in dbg          # wiki ref echoed
        assert "NO MATCH" in dbg               # loop unit's code refs

    def test_retrieval_debug_flag_summary(self, tmp_path):
        self._setup(tmp_path)
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "TODO-REVIEW-NO-CODE-REF" in dbg
        assert "review flags raised" in dbg

    def test_retrieval_debug_clean_when_no_flags(self, tmp_path):
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (tmp_path / "unit_01_phase_0_methods.py").write_text(UNIT_0, encoding="utf-8")
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "no review flags" in dbg

    def test_both_miss_flag_aggregated(self, tmp_path):
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (tmp_path / "unit_01_x_methods.py").write_text(UNIT_BOTH_MISS, encoding="utf-8")
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "TODO-REVIEW-BOTH-MISS" in dbg

    def test_no_code_ref_derived_when_agent_forgets(self, tmp_path):
        # Code refs NO MATCH + an actual api call + empty REVIEW FLAGS section:
        # the flag must be DERIVED from content, not trusted from the agent.
        unit = ("=== WIKI REFS ===\n- entities/lun.md\n"
                "=== CODE REFS ===\nNO MATCH\n"
                "=== REVIEW FLAGS ===\n"
                "=== METHODS ===\n"
                "    def step1(self) -> None:\n"
                "        api.set_flag(idn=0x0E)\n")
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (tmp_path / "unit_01_x_methods.py").write_text(unit, encoding="utf-8")
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)     # no script_root -> no D check
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "TODO-REVIEW-NO-CODE-REF" in dbg
        assert "no review flags" not in dbg      # must NOT falsely claim all-grounded

    def test_pure_python_step_not_flagged_no_code_ref(self, tmp_path):
        # A delay step with no API call and no code ref must NOT be flagged NO-CODE-REF.
        unit = ("=== WIKI REFS ===\n- concepts/x.md\n"
                "=== CODE REFS ===\nNO MATCH\n"
                "=== REVIEW FLAGS ===\n"
                "=== METHODS ===\n"
                "    def step1(self) -> None:\n"
                "        import time; time.sleep(1)\n")
        (tmp_path / "scaffold.py").write_text(SCAFFOLD, encoding="utf-8")
        (tmp_path / "unit_01_x_methods.py").write_text(unit, encoding="utf-8")
        assemble_pattern(tmp_path, "MyTest", output_dir=tmp_path)
        dbg = (tmp_path / "retrieval_debug.md").read_text(encoding="utf-8")
        assert "TODO-REVIEW-NO-CODE-REF" not in dbg
