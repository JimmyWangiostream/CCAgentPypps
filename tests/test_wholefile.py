from pattern_generator.wholefile import build_wholefile_prompt, _dataflow_contract, _unit_plan
from pattern_generator.stepwise import generation_units

SMALL_IR = {
    "pattern_id": "PFW", "title": "Whole-file test",
    "phases": [{"phase_id": "phase_0", "name": "P", "type": "sequential",
                "loop_type": None, "loop_count": None, "steps": [
        {"step_id": "s1", "scsi_cmd": "TEST UNIT READY", "ufs_query": None,
         "opcode": "0x00", "query_opcode": None, "idn": None, "expected": "GOOD",
         "produces": ["max_lba"], "consumes": []},
        {"step_id": "s2", "scsi_cmd": "READ(10)", "ufs_query": None, "opcode": "0x28",
         "query_opcode": None, "idn": None, "expected": "GOOD, Data Match",
         "produces": [], "consumes": ["max_lba"]}],
        "inputs": [], "outputs": ["max_lba"]}],
    "dependency_graph": {"nodes": ["phase_0"], "edges": []},
}


def test_dataflow_contract_lists_produce_consume():
    units = generation_units(SMALL_IR)
    out = _dataflow_contract(units)
    assert "produces self.max_lba" in out
    assert "consumes self.max_lba" in out


def test_unit_plan_lists_methods():
    out = _unit_plan(generation_units(SMALL_IR))
    assert "step1" in out and "step2" in out


def test_build_wholefile_prompt_structure():
    # script_root may be absent -> idiom anchors just omitted; the rest must be present
    p = build_wholefile_prompt(SMALL_IR, "no/such/script")
    assert "Unit plan" in p
    assert "Data-flow contract" in p and "self.max_lba" in p
    assert "Review references" in p
    assert "COMPLETE file" in p
    assert "INSIDE the pattern class" in p
    assert "# @@PHASE_METHODS@@" in p          # scaffold embedded
    assert "raise api.PATTERN_ASSERT_" in p    # assert-discipline instruction


def test_wholefile_instructions_carry_namespace_rule():
    from pattern_generator.wholefile import WHOLEFILE_INSTRUCTIONS
    assert "Namespace rule (AUTHORITATIVE" in WHOLEFILE_INSTRUCTIONS
    assert "api.init_tester_to_unit_ready" in WHOLEFILE_INSTRUCTIONS
