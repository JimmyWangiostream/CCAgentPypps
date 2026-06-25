from pattern_generator.driver import gate_failures, build_repair_prompt, run_gate

IR = {
    "pattern_id": "PFD", "title": "t",
    "phases": [{"phase_id": "phase_0", "type": "sequential", "steps": [
        {"step_id": "s1", "name": "tur", "scsi_cmd": "TEST UNIT READY",
         "expected": "GOOD", "produces": ["max_lba"], "consumes": []},
        {"step_id": "s2", "name": "read", "scsi_cmd": "READ(10)",
         "expected": "GOOD, Data Match", "produces": [], "consumes": ["max_lba"]}]}],
    "dependency_graph": {"nodes": ["phase_0"], "edges": []},
}

GOOD = (
    "class P(UFSTC):\n"
    "    def step1(self) -> None:\n"
    "        self.max_lba = 100\n"
    "    def step2(self) -> None:\n"
    "        x = self.max_lba\n"
)

# step methods defined outside the class -> structural gate failure
BAD = (
    "class P(UFSTC):\n"
    "    def pre_process(self) -> None:\n"
    "        pass\n"
    "if __name__ == '__main__':\n"
    "    P().run()\n"
    "    def step1(self) -> None:\n"
    "        self.max_lba = 1\n"
)


def test_gate_failures_empty_on_pass():
    report = {"syntax": "pass", "structure": "pass", "dataflow": "pass",
              "api_grounding": "skipped"}
    assert gate_failures(report) == {}


def test_gate_failures_collects_problems():
    report = {"syntax": "pass", "structure": ["bad1"], "dataflow": "pass",
              "api_grounding": ["L1: x"]}
    fails = gate_failures(report)
    assert set(fails) == {"structure", "api_grounding"}


def test_run_gate_pass():
    g = run_gate(GOOD, IR)
    assert g["failures"] == {}
    assert g["report"]["structure"] == "pass"


def test_run_gate_fail_on_methods_outside_class():
    g = run_gate(BAD, IR)
    assert "structure" in g["failures"]


def test_repair_prompt_includes_findings_and_review():
    g = run_gate(BAD, IR)
    prompt = build_repair_prompt(BAD, IR, g["report"])
    assert "Validator findings" in prompt
    assert "OUTSIDE the pattern class" in prompt   # the concrete finding
    assert "Checkpoints" in prompt                 # the review content
    assert "raise api.PATTERN_ASSERT_" in prompt   # rule discipline


def test_repair_prompt_without_failures_is_just_review():
    g = run_gate(GOOD, IR)
    prompt = build_repair_prompt(GOOD, IR, g["report"])
    assert "Validator findings" not in prompt
    assert "Checkpoints" in prompt
