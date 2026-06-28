"""Tests for pattern_generator.api_grounding: build_script_index + check_api_calls.

Uses a tiny synthetic Script/ tree (no dependency on the real GitNexusMCP index)."""
from pathlib import Path

from pattern_generator.api_grounding import (
    build_script_index, check_api_calls, format_issues,
)


def _mini_script(root: Path) -> Path:
    """Build a minimal Script/ library exercising `import *` chains + aliases."""
    api = root / "api"
    (api / "ufs_api").mkdir(parents=True)
    (api / "cmd_seq").mkdir(parents=True)
    (root / "lib").mkdir(parents=True)

    (api / "__init__.py").write_text(
        "from .ufs_api import *\nfrom .cmd_seq import *\n", encoding="utf-8")
    (api / "ufs_api" / "__init__.py").write_text(
        "from .rw import *\n", encoding="utf-8")
    (api / "ufs_api" / "rw.py").write_text(
        "from enum import IntEnum\n"
        "class Status(IntEnum):\n    OK = 0\n    FAIL = 1\n"
        "def sequential_write(lun, start_lba, total_size, chunk_size, fua):\n"
        "    pass\n"
        "def random_read(cmd_count, min_lun, max_lun, need_compare, write_record):\n"
        "    pass\n"
        "def get_config_descriptors(print=False):\n"
        "    return []\n"
        "def flexible(a, **kwargs):\n"
        "    pass\n",
        encoding="utf-8")
    (api / "cmd_seq" / "__init__.py").write_text(
        "from .cmds import *\nfrom .executor import send\n", encoding="utf-8")
    (api / "cmd_seq" / "cmds.py").write_text(
        "class ReadCapacity10:\n    pass\n"
        "class CmdSeqTestUnitReady:\n"
        "    def __init__(self):\n        pass\n",
        encoding="utf-8")
    (api / "cmd_seq" / "executor.py").write_text(
        "def send(clear_on_success=True, timeout=None):\n    pass\n", encoding="utf-8")
    (root / "lib" / "sdk_lib.py").write_text(
        "def delay(seconds):\n    pass\n", encoding="utf-8")
    return root


class TestBuildIndex:
    def test_resolves_aliases_and_symbols(self, tmp_path):
        idx = build_script_index(_mini_script(tmp_path / "Script"))
        assert {"api", "ExecuteCMD", "lib"} <= set(idx)
        assert "_enums" in idx                       # deterministic enum whitelist
        assert "random_read" in idx["api"].symbols
        assert "sequential_write" in idx["api"].symbols
        assert "send" in idx["ExecuteCMD"].symbols
        assert "ReadCapacity10" in idx["ExecuteCMD"].symbols
        assert "delay" in idx["lib"].symbols

    def test_signature_params_captured(self, tmp_path):
        idx = build_script_index(_mini_script(tmp_path / "Script"))
        rr = idx["api"].symbols["random_read"]
        assert rr.params == {"cmd_count", "min_lun", "max_lun", "need_compare", "write_record"}
        assert not rr.has_kwargs
        assert rr.max_positional == 5

    def test_missing_root_returns_none(self, tmp_path):
        assert build_script_index(tmp_path / "nope") is None


class TestCheckApiCalls:
    def _idx(self, tmp_path):
        return build_script_index(_mini_script(tmp_path / "Script"))

    def test_sibling_param_conflation_flagged(self, tmp_path):
        # random_read called with sequential_write's parameters
        src = ("def f(self):\n"
               "    api.random_read(lun=1, start_lba=0, total_size=4096, "
               "chunk_size=512, fua=0)\n")
        issues = check_api_calls(src, self._idx(tmp_path))
        bad = {i["detail"] for i in issues if i["kind"] == "unknown_kwarg"}
        assert any("'lun'" in d for d in bad)
        assert any("'start_lba'" in d for d in bad)
        assert any("'chunk_size'" in d for d in bad)

    def test_unknown_symbol_with_suggestion(self, tmp_path):
        src = "def f(self):\n    api.get_config_descriptor()\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert len(issues) == 1
        assert issues[0]["kind"] == "unknown_symbol"
        assert issues[0]["suggestion"] == "get_config_descriptors"

    def test_correct_call_passes(self, tmp_path):
        src = ("def f(self):\n"
               "    api.sequential_write(lun=1, start_lba=0, total_size=4096, "
               "chunk_size=512, fua=0)\n")
        assert check_api_calls(src, self._idx(tmp_path)) == []

    def test_too_many_positional_flagged(self, tmp_path):
        src = "def f(self):\n    lib.delay(1, 2, 3)\n"   # delay takes 1
        issues = check_api_calls(src, self._idx(tmp_path))
        assert any(i["kind"] == "too_many_positional" for i in issues)

    def test_missing_required_arg_flagged(self, tmp_path):
        # random_read requires cmd_count, min_lun, max_lun, need_compare, write_record
        src = "def f(self):\n    api.random_read(cmd_count=1, min_lun=0)\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        miss = [i for i in issues if i["kind"] == "missing_required_arg"]
        assert miss
        # check the missing-list portion (the detail now also appends the real signature)
        missing_part = miss[0]["detail"].split("[real signature")[0]
        assert "max_lun" in missing_part
        assert "write_record" in missing_part
        assert "min_lun" not in missing_part        # supplied -> not in the missing list

    def test_required_args_satisfied_positionally(self, tmp_path):
        src = "def f(self):\n    api.random_read(1, 0, 0, True, None)\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert not [i for i in issues if i["kind"] == "missing_required_arg"]

    def test_missing_required_skipped_on_kwargs_splat(self, tmp_path):
        src = "def f(self):\n    api.random_read(**opts)\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert not [i for i in issues if i["kind"] == "missing_required_arg"]

    def test_default_arg_not_required(self, tmp_path):
        # get_config_descriptors(print=False) -> no required args
        src = "def f(self):\n    api.get_config_descriptors()\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert issues == []

    def test_enum_member_whitelisted(self, tmp_path):
        idx = self._idx(tmp_path)
        assert idx["_enums"].get("Status") == {"OK", "FAIL"}

    def test_unknown_enum_member_flagged_with_valid_list(self, tmp_path):
        src = "def f(self):\n    x = api.Status.NOPE\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        miss = [i for i in issues if i["kind"] == "unknown_enum_member"]
        assert miss
        assert "OK" in miss[0]["detail"] and "FAIL" in miss[0]["detail"]   # valid members listed

    def test_valid_enum_member_passes(self, tmp_path):
        src = "def f(self):\n    x = api.Status.OK\n    y = api.Status.OK.value\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert not [i for i in issues if i["kind"] == "unknown_enum_member"]

    def test_finding_carries_real_signature(self, tmp_path):
        # bad kwarg -> the detail must include the real signature (copy-paste fix)
        src = "def f(self):\n    api.random_read(badkw=1)\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        det = " ".join(i["detail"] for i in issues)
        assert "real signature: random_read(" in det

    def test_kwargs_func_accepts_any_kwarg(self, tmp_path):
        src = "def f(self):\n    api.flexible(a=1, anything=2, more=3)\n"
        assert check_api_calls(src, self._idx(tmp_path)) == []

    def test_class_without_init_accepts_any(self, tmp_path):
        src = "def f(self):\n    ExecuteCMD.ReadCapacity10(x=1)\n"
        assert check_api_calls(src, self._idx(tmp_path)) == []

    def test_instance_method_calls_ignored(self, tmp_path):
        # cmd.enqueue() is not a namespace call — must not be flagged
        src = "def f(self):\n    cmd.enqueue()\n    resp.data\n"
        assert check_api_calls(src, self._idx(tmp_path)) == []

    def test_format_issues_renders_lines(self, tmp_path):
        src = "def f(self):\n    api.get_config_descriptor()\n"
        lines = format_issues(check_api_calls(src, self._idx(tmp_path)))
        assert lines and "did you mean 'get_config_descriptors'" in lines[0]
