import importlib.util
from pathlib import Path

import pytest

from pattern_generator.validator import validate, _check_mypy
from pattern_generator.config import PGConfig


# Two sequential steps: step1 produces max_lba, step2 consumes it.
SEQ_IR = {
    "pattern_id": "PFX", "title": "t",
    "phases": [{"phase_id": "phase_0", "name": "P", "type": "sequential",
                "loop_type": None, "loop_count": None, "steps": [
        {"step_id": "s1", "scsi_cmd": "TUR", "ufs_query": None, "opcode": "0x00",
         "query_opcode": None, "idn": None, "expected": "GOOD",
         "produces": ["max_lba"], "consumes": []},
        {"step_id": "s2", "scsi_cmd": "READ", "ufs_query": None, "opcode": "0x28",
         "query_opcode": None, "idn": None, "expected": "GOOD",
         "produces": [], "consumes": ["max_lba"]}],
        "inputs": [], "outputs": ["max_lba"]}],
    "dependency_graph": {"nodes": ["phase_0"], "edges": []},
}

# Count loop (50) with one sub-step -> methods: _loop1_step_1_1 + wrapper step1.
LOOP_IR = {
    "pattern_id": "PFY", "title": "t",
    "phases": [{"phase_id": "loop_1", "name": "L", "type": "loop",
                "loop_type": "count", "loop_count": 50, "steps": [
        {"step_id": "step_1_1", "scsi_cmd": "X", "ufs_query": None, "opcode": None,
         "query_opcode": None, "idn": None, "expected": "", "produces": [],
         "consumes": []}], "inputs": [], "outputs": []}],
    "dependency_graph": {"nodes": ["loop_1"], "edges": []},
}

GOOD = (
    "class P(UFSTC):\n"
    "    def step1(self) -> None:\n"
    "        self.max_lba = 100\n"
    "    def step2(self) -> None:\n"
    "        x = self.max_lba\n"
    "\n"
    "if __name__ == '__main__':\n"
    "    P().run()\n"
)


def test_syntax_failure_is_reported():
    out = validate("def f(:\n  pass", SEQ_IR)
    assert out["syntax"] != "pass"


def test_structure_passes_well_formed():
    out = validate(GOOD, SEQ_IR)
    assert out["syntax"] == "pass"
    assert out["structure"] == "pass"
    assert out["dataflow"] == "pass"


def test_structure_catches_methods_outside_class():
    """The #1 catastrophic bug: stepN methods land outside the class / after the
    __main__ guard. Parses fine, but process() runs nothing."""
    bad = (
        "class P(UFSTC):\n"
        "    def pre_process(self) -> None:\n"
        "        pass\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    P().run()\n"
        "\n"
        "    def step1(self) -> None:\n"
        "        self.max_lba = 100\n"
        "    def step2(self) -> None:\n"
        "        x = self.max_lba\n"
    )
    out = validate(bad, SEQ_IR)
    assert out["structure"] != "pass"
    blob = " ".join(out["structure"])
    assert "OUTSIDE the pattern class" in blob
    assert "no stepN" in blob          # class itself has no step method


def test_structure_flags_no_pattern_class():
    out = validate("x = 1\n", SEQ_IR)
    assert out["structure"] != "pass"
    assert any("no pattern class" in m for m in out["structure"])


def test_structure_passes_with_loop_count_present():
    src = (
        "class P(UFSTC):\n"
        "    def _loop1_step_1_1(self, loop_idx: int) -> None:\n"
        "        pass\n"
        "    def step1(self) -> None:\n"
        "        for i in range(50):\n"
        "            self._loop1_step_1_1(i)\n"
    )
    out = validate(src, LOOP_IR)
    assert out["structure"] == "pass"


def test_structure_flags_missing_loop_count():
    src = (
        "class P(UFSTC):\n"
        "    def _loop1_step_1_1(self, loop_idx: int) -> None:\n"
        "        pass\n"
        "    def step1(self) -> None:\n"
        "        for i in range(10):\n"   # 50 absent
        "            self._loop1_step_1_1(i)\n"
    )
    out = validate(src, LOOP_IR)
    assert out["structure"] != "pass"
    assert any("loop_count" in m for m in out["structure"])


def test_dataflow_catches_rerandomized_consume():
    """step2 consumes max_lba but overwrites self.max_lba without reading it."""
    bad = (
        "import random\n"
        "class P(UFSTC):\n"
        "    def step1(self) -> None:\n"
        "        self.max_lba = 100\n"
        "    def step2(self) -> None:\n"
        "        self.max_lba = random.randint(0, 9)\n"
    )
    out = validate(bad, SEQ_IR)
    assert out["dataflow"] != "pass"
    assert any("max_lba" in m for m in out["dataflow"])


def test_dataflow_passes_when_threaded():
    out = validate(GOOD, SEQ_IR)
    assert out["dataflow"] == "pass"


# ---------------------------------------------------------------------------
# mypy gate (opt-in)
# ---------------------------------------------------------------------------

_SCRIPT_ROOT = PGConfig().script_root
_MYPY_OK = (importlib.util.find_spec("mypy") is not None
            and (_SCRIPT_ROOT.parent / "mypy_skip_known_issue.ini").is_file())
_skip_mypy = pytest.mark.skipif(not _MYPY_OK, reason="mypy / GitNexusMCP config not present")


def test_validate_no_mypy_key_by_default():
    out = validate(GOOD, SEQ_IR)               # run_mypy defaults False
    assert "mypy" not in out


def test_mypy_skipped_without_path():
    assert _check_mypy(None, _SCRIPT_ROOT) == "skipped"


def test_mypy_skipped_when_no_config(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("x = 1\n", encoding="utf-8")
    # script_root whose parent has no mypy_skip_known_issue.ini
    assert _check_mypy(f, tmp_path / "Script") == "skipped"


@_skip_mypy
def test_mypy_clean_file_passes(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text("x: int = 1\n", encoding="utf-8")
    assert _check_mypy(f, _SCRIPT_ROOT) == "pass"


@_skip_mypy
def test_mypy_flags_type_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("x: int = 'not an int'\n", encoding="utf-8")
    res = _check_mypy(f, _SCRIPT_ROOT)
    assert isinstance(res, list) and any("error" in e.lower() for e in res)


# ---------------------------------------------------------------------------
# api_grounding integration
# ---------------------------------------------------------------------------

NOLOOP_IR = {"phases": []}


def _mini_script(root: Path) -> Path:
    api = root / "api"
    api.mkdir(parents=True)
    (root / "lib").mkdir(parents=True)
    (api / "__init__.py").write_text("from .funcs import *\n", encoding="utf-8")
    (api / "funcs.py").write_text(
        "def get_config_descriptors():\n    return []\n"
        "def random_read(cmd_count, min_lun, max_lun):\n    pass\n",
        encoding="utf-8")
    (api / "cmd_seq").mkdir()
    (api / "cmd_seq" / "__init__.py").write_text("", encoding="utf-8")
    (root / "lib" / "sdk_lib.py").write_text("def x():\n    pass\n", encoding="utf-8")
    return root


def test_api_grounding_skipped_without_script_root():
    out = validate("api.anything()\n", NOLOOP_IR)
    assert out["api_grounding"] == "skipped"


def test_api_grounding_skipped_on_bad_root(tmp_path):
    out = validate("api.anything()\n", NOLOOP_IR, script_root=tmp_path / "nope")
    assert out["api_grounding"] == "skipped"


def test_api_grounding_flags_unknown_symbol(tmp_path):
    root = _mini_script(tmp_path / "Script")
    out = validate("api.get_config_descriptor()\n", NOLOOP_IR, script_root=root)
    assert out["api_grounding"] != "pass"
    assert any("get_config_descriptor" in m for m in out["api_grounding"])


def test_api_grounding_flags_bad_kwargs(tmp_path):
    root = _mini_script(tmp_path / "Script")
    out = validate("api.random_read(lun=1, start_lba=0)\n", NOLOOP_IR, script_root=root)
    assert out["api_grounding"] != "pass"
    assert any("lun" in m for m in out["api_grounding"])


def test_api_grounding_passes_for_good_call(tmp_path):
    root = _mini_script(tmp_path / "Script")
    out = validate("api.random_read(cmd_count=1, min_lun=0, max_lun=0)\n",
                   NOLOOP_IR, script_root=root)
    assert out["api_grounding"] == "pass"
