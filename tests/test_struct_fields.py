"""Struct-field grounding gap (Hermes l85 bug): index struct fields, inject them (api_facts),
and catch fabricated field access (check_struct_fields) — precise, false-positive-free."""
from pattern_generator.api_grounding import (
    build_script_index, check_struct_fields, resolve_fields, api_facts,
)


def _mini_script(tmp_path):
    """A tiny Script root: an api/ package with a struct-returning function."""
    root = tmp_path / "Script"
    (root / "api").mkdir(parents=True)
    (root / "api" / "__init__.py").write_text(
        "from .desc import get_wb_support, WbSupport\n", encoding="utf-8")
    (root / "api" / "desc.py").write_text(
        "class WbSupport:\n"
        "    def __init__(self):\n"
        "        self.u0_write_booster_buffer_resize = 0\n"
        "        self.u1_fifo_partial_flush_mode = 0\n"
        "def get_wb_support() -> WbSupport:\n"
        "    return WbSupport()\n",
        encoding="utf-8")
    return root


def _idx(tmp_path):
    return build_script_index(_mini_script(tmp_path))


def test_index_captures_struct_fields_and_returns(tmp_path):
    idx = _idx(tmp_path)
    assert "u0_write_booster_buffer_resize" in idx["_all_struct_fields"]
    assert resolve_fields(idx, "WbSupport") == {
        "u0_write_booster_buffer_resize", "u1_fifo_partial_flush_mode"}
    assert idx["api"].symbols["get_wb_support"].returns == "WbSupport"


def test_catch_fabricated_field_var_origin(tmp_path):
    idx = _idx(tmp_path)
    src = ("class P:\n"
           "    def step(self):\n"
           "        wb = api.get_wb_support()\n"
           "        x = wb.l85_num_shared_write_booster_buffer_alloc_units\n")
    issues = check_struct_fields(src, idx)
    assert len(issues) == 1 and issues[0]["kind"] == "unknown_struct_field"
    assert "l85_num_shared_write_booster_buffer_alloc_units" in issues[0]["symbol"]


def test_catch_inline_call_attr(tmp_path):
    idx = _idx(tmp_path)
    src = ("class P:\n    def step(self):\n"
           "        y = api.get_wb_support().l85_bogus_field\n")
    assert any(i["kind"] == "unknown_struct_field" for i in check_struct_fields(src, idx))


def test_real_field_not_flagged(tmp_path):
    idx = _idx(tmp_path)
    src = ("class P:\n    def step(self):\n"
           "        wb = api.get_wb_support()\n"
           "        x = wb.u0_write_booster_buffer_resize\n")
    assert check_struct_fields(src, idx) == []


def test_no_false_positive_on_methods_and_self(tmp_path):
    idx = _idx(tmp_path)
    # logger.debug / .append / self.* / subscript chains must never flag
    src = ("class P:\n    def step(self):\n"
           "        wb = api.get_wb_support()\n"
           "        self.logger.debug('x')\n"
           "        items = []\n"
           "        items.append(1)\n"
           "        self.write_record_p1 = wb\n"
           "        z = self.config[0].header.l18_num_shared_write_booster_buffer_alloc_units\n")
    assert check_struct_fields(src, idx) == []


def test_api_facts_injects_struct_fields(tmp_path):
    facts = api_facts(_mini_script(tmp_path), symbol_names=("get_wb_support",),
                      query="write booster support")
    assert any("WbSupport fields" in f and "u0_write_booster_buffer_resize" in f for f in facts)
