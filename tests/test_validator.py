from pathlib import Path

from pattern_generator.validator import validate


IR = {"phases": [{"phase_id": "loop_1", "type": "loop", "loop_type": "count",
                  "loop_count": 100, "steps": []}]}


def test_syntax_failure_is_reported():
    out = validate("def f(:\n  pass", IR)
    assert out["syntax"] != "pass"


def test_structure_checks_loop_count_present():
    good = "for i in range(100):\n    pass\n"
    out = validate(good, IR)
    assert out["syntax"] == "pass"
    assert out["structure"] == "pass"


def test_structure_flags_missing_loop_count():
    out = validate("x = 1\n", IR)
    assert out["structure"] != "pass"


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
