"""Tests for pattern_generator.api_grounding: build_script_index + check_api_calls.

Uses a tiny synthetic Script/ tree (no dependency on the real GitNexusMCP index)."""
from pathlib import Path

from pattern_generator.api_grounding import (
    SCAFFOLD_NAMES, alias_for_path, api_facts, build_script_index,
    check_api_calls, check_bare_names, format_issues, render_sig,
    resolve_bare_name,
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
        "class FlagIDN(IntEnum):\n    WRITEBOOSTER_EN = 0x0E\n    DEVICE_INIT = 0x04\n"
        "def set_flag(idn, index=0, selector=0):\n    pass\n"
        "def sequential_write(lun, start_lba, total_size, chunk_size, fua):\n"
        "    pass\n"
        "def random_read(cmd_count, min_lun, max_lun, need_compare, write_record):\n"
        "    pass\n"
        "def get_config_descriptors(print=False):\n"
        "    return []\n"
        "def flexible(a, **kwargs):\n"
        "    pass\n"
        "def do_write(write_record: list[list], count: int = 1):\n"
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


class TestApiFacts:
    """Phase B: inject exact signatures + relevant enum members AT generation time."""

    def _root(self, tmp_path):
        return _mini_script(tmp_path / "Script")

    def test_exact_signature_injected(self, tmp_path):
        facts = api_facts(self._root(tmp_path), ("set_flag",), "set flag")
        assert "api.set_flag(idn, index=..., selector=...)" in "\n".join(facts)

    def test_relevant_enum_members_listed(self, tmp_path):
        facts = api_facts(self._root(tmp_path), ("set_flag",), "set flag writebooster en")
        joined = "\n".join(facts)
        assert "FlagIDN valid members:" in joined
        assert "WRITEBOOSTER_EN" in joined and "DEVICE_INIT" in joined

    def test_generic_enum_not_selected_on_generic_token(self, tmp_path):
        # the 'Status' enum shares only the generic token 'status' -> must NOT inject
        facts = api_facts(self._root(tmp_path), (), "check status")
        assert not any("Status valid members" in f for f in facts)

    def test_unrelated_query_yields_nothing(self, tmp_path):
        assert api_facts(self._root(tmp_path), (), "zzz totally unrelated") == []

    def test_missing_root_returns_empty(self, tmp_path):
        assert api_facts(tmp_path / "nope", ("set_flag",), "set flag") == []

    def test_enum_fact_carries_alias_prefix(self, tmp_path):
        facts = api_facts(self._root(tmp_path), ("set_flag",), "set flag writebooster en")
        assert any(f.startswith("api.FlagIDN valid members:") for f in facts)


class TestAliasMapping:
    """ONE source of truth: defining-module path -> scaffold alias."""

    def test_alias_for_path(self):
        assert alias_for_path("api/ufs_api/initial_device.py") == "api"
        assert alias_for_path("api/cmd_seq/executor.py") == "ExecuteCMD"   # wins over api/
        assert alias_for_path("lib/sdk_lib/user.py") == "lib"
        assert alias_for_path("Script/api/rw.py") == "api"                 # Script/ prefix ok
        assert alias_for_path("api\\ufs_api\\rw.py") == "api"              # backslashes ok
        assert alias_for_path("pattern/sample_code/wb.py") is None
        assert alias_for_path("project_api/x.py") is None

    def test_resolve_bare_name_priority(self, tmp_path):
        idx = build_script_index(_mini_script(tmp_path / "Script"))
        assert resolve_bare_name("set_flag", idx) == "api"
        assert resolve_bare_name("delay", idx) == "lib"
        # cmd_seq symbols are re-exported into api -> api wins by priority (still valid)
        assert resolve_bare_name("send", idx) == "api"
        assert resolve_bare_name("no_such_symbol", idx) is None

    def test_scaffold_names_match_standard_imports(self):
        """SCAFFOLD_NAMES must equal the names stepwise.STANDARD_IMPORTS binds."""
        import ast
        from pattern_generator.stepwise import STANDARD_IMPORTS
        bound: set = set()
        for n in ast.parse(STANDARD_IMPORTS).body:
            if isinstance(n, ast.Import):
                bound |= {a.asname or a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                bound |= {a.asname or a.name for a in n.names}
        assert bound == set(SCAFFOLD_NAMES)


class TestWrongNamespace:
    """A symbol called under the WRONG alias must yield the exact corrected form."""

    def _idx(self, tmp_path):
        return build_script_index(_mini_script(tmp_path / "Script"))

    def test_wrong_namespace_on_call(self, tmp_path):
        src = "def f(self):\n    lib.set_flag(idn=1)\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        wn = [i for i in issues if i["kind"] == "wrong_namespace"]
        assert wn and "write api.set_flag(...)" in wn[0]["detail"]

    def test_wrong_namespace_on_non_call_attribute(self, tmp_path):
        # the lib.Dcmd5ResetType.HW_RESET class of bug — an attribute, not a call
        src = "def f(self):\n    x = lib.Status.OK\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        wn = [i for i in issues if i["kind"] == "wrong_namespace"]
        assert wn and "write api.Status" in wn[0]["detail"]

    def test_correct_alias_attribute_passes(self, tmp_path):
        src = "def f(self):\n    x = api.Status.OK\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert not [i for i in issues if i["kind"] in ("wrong_namespace", "unknown_symbol")]

    def test_unknown_everywhere_stays_unknown_symbol(self, tmp_path):
        src = "def f(self):\n    lib.totally_fabricated()\n"
        issues = check_api_calls(src, self._idx(tmp_path))
        assert [i for i in issues if i["kind"] == "unknown_symbol"]
        assert not [i for i in issues if i["kind"] == "wrong_namespace"]


class TestCheckBareNames:
    """Bare star-import idioms / undefined names — previously a total blind spot."""

    def _idx(self, tmp_path):
        return build_script_index(_mini_script(tmp_path / "Script"))

    def _wrap(self, body: str) -> str:
        return "class _W:\n" + body

    def test_bare_call_resolved_to_alias(self, tmp_path):
        src = self._wrap("    def step1(self):\n        set_flag(idn=1)\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        bn = [i for i in issues if i["kind"] == "bare_name"]
        assert bn and "write api.set_flag(...)" in bn[0]["detail"]

    def test_bare_enum_attribute_resolved(self, tmp_path):
        src = self._wrap("    def step1(self):\n        x = Status.OK\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        bn = [i for i in issues if i["kind"] == "bare_name"]
        assert bn and "write api.Status" in bn[0]["detail"]

    def test_bare_lib_symbol_resolved(self, tmp_path):
        src = self._wrap("    def step1(self):\n        delay(2)\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        bn = [i for i in issues if i["kind"] == "bare_name"]
        assert bn and "write lib.delay(...)" in bn[0]["detail"]

    def test_undefined_log_suggests_logger(self, tmp_path):
        src = self._wrap("    def step1(self):\n        _log.info('x')\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        un = [i for i in issues if i["kind"] == "undefined_name"]
        assert un and un[0].get("suggestion") == "logger"

    def test_missing_stdlib_import_hinted(self, tmp_path):
        src = self._wrap("    def step1(self):\n        time.sleep(1)\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        un = [i for i in issues if i["kind"] == "undefined_name"]
        assert un and "add 'import time'" in un[0]["detail"]

    def test_scope_model_negatives(self, tmp_path):
        # locals, params, comprehension targets, nested defs, self/logger — all legal
        src = self._wrap(
            "    def step1(self, count):\n"
            "        total = 0\n"
            "        items = [x for x in range(count)]\n"
            "        def inner(y):\n"
            "            return y + total\n"
            "        total = inner(1)\n"
            "        self.result = items\n"
            "        logger.info(total)\n"
            "        api.set_flag(idn=1)\n")
        assert check_bare_names(src, self._idx(tmp_path)) == []

    def test_extra_imports_respected(self, tmp_path):
        src = self._wrap("    def step1(self):\n        x = cast(int, 1)\n")
        idx = self._idx(tmp_path)
        assert [i for i in check_bare_names(src, idx)]                       # without
        assert check_bare_names(src, idx,
                                extra_imports=["from typing import cast"]) == []

    def test_script_star_import_makes_bare_legal(self, tmp_path):
        # real reference patterns do `from Script.api.ufs_api import *`
        src = ("from Script.api.ufs_api import *\n"
               "class P:\n"
               "    def step1(self):\n"
               "        set_flag(idn=1)\n"
               "        x = Status.OK\n")
        assert check_bare_names(src, self._idx(tmp_path)) == []

    def test_unresolvable_star_import_suppresses_all(self, tmp_path):
        src = ("from somewhere_else import *\n"
               "class P:\n"
               "    def step1(self):\n"
               "        set_flag(idn=1)\n"
               "        _log.info('x')\n")
        assert check_bare_names(src, self._idx(tmp_path)) == []

    def test_one_finding_per_name(self, tmp_path):
        src = self._wrap(
            "    def step1(self):\n"
            "        set_flag(idn=1)\n"
            "        set_flag(idn=2)\n"
            "    def step2(self):\n"
            "        set_flag(idn=3)\n")
        issues = check_bare_names(src, self._idx(tmp_path))
        assert len([i for i in issues if i["symbol"] == "set_flag"]) == 1


class TestAnnotatedSignatures:
    """FEED fidelity: annotated params carry their real type."""

    def test_render_sig_shows_annotations(self, tmp_path):
        idx = build_script_index(_mini_script(tmp_path / "Script"))
        spec = idx["api"].symbols["do_write"]
        sig = render_sig("do_write", spec)
        assert "write_record: list[list]" in sig
        assert "count: int=..." in sig

    def test_api_facts_signature_carries_annotation(self, tmp_path):
        facts = api_facts(_mini_script(tmp_path / "Script"), ("do_write",), "do write")
        assert any("write_record: list[list]" in f for f in facts)
