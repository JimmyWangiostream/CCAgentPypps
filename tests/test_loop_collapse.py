"""Cross-phase loop collapse: the Tree Diagram's `Loop (...)` node over Phase 1-3 must
become a single loop-type phase that stepwise materializes as a `for` loop (Defect A).
Loop topology is read from the Tree Diagram (## 測試架構), not the JIRA 對照表."""
from pathlib import Path

from ir_generator.parser import (
    parse_tc, _collapse_loop_region, _find_loop_phase_numbers,
)
from pattern_generator.stepwise import generation_units, build_loop_wrapper_method

TC = Path("TC/PF010_0310-normalized-test-flow.md")
# This fixture declares its loop with a `## Loop` header (count 100) — the back-compat case.
FIXTURE_LOOP_HEADER = Path("tests/fixtures/pf002-0098-normalized-test-flow.md")

_TREE = "## 測試架構（Tree Diagram — 含 Expected）\n\n```\n"


def test_tree_diagram_loop_phase_numbers():
    assert _find_loop_phase_numbers(TC.read_text(encoding="utf-8")) == [1, 2, 3]


def test_cross_phase_loop_collapsed():
    phases = parse_tc(TC)["phases"]
    assert [p["phase_id"] for p in phases] == ["phase_0", "loop_1"]
    pre, loop = phases
    assert pre["type"] == "sequential" and len(pre["steps"]) == 2
    assert loop["type"] == "loop"
    assert loop["loop_type"] == "condition" and loop["loop_count"] is None
    assert [s["step_id"] for s in loop["steps"]] == [
        "step_1_1", "step_1_2", "step_1_3", "step_1_4",
        "step_2_1", "step_2_2", "step_2_3", "step_2_4",
        "step_3_1", "step_3_2", "step_3_3", "step_3_4", "step_3_5",
    ]


def test_collapsed_loop_materializes_as_for_loop():
    units = generation_units(parse_tc(TC))
    wrappers = [u for u in units if u["kind"] == "loop_wrapper"]
    substeps = [u for u in units if u["kind"] == "loop_substep"]
    assert len(wrappers) == 1
    assert len(substeps) == 13  # one helper per looped step
    assert "for loop_idx in range(" in build_loop_wrapper_method(wrappers[0])


def test_noop_when_loop_already_a_phase():
    # A `## Loop`-header TC already has a loop phase -> collapse must not touch it.
    ir = parse_tc(FIXTURE_LOOP_HEADER)
    assert len(ir["phases"]) == 3
    loop = next(p for p in ir["phases"] if p["type"] == "loop")
    assert loop["loop_type"] == "count" and loop["loop_count"] == 100


def test_noop_when_no_loop_node():
    # A Tree Diagram with no `Loop` node -> no cross-phase loop -> no collapse.
    phases = [
        {"phase_id": "phase_0", "type": "sequential", "steps": [{"step_id": "step_0_1"}]},
        {"phase_id": "phase_1", "type": "sequential", "steps": [{"step_id": "step_1_1"}]},
    ]
    text = _TREE + "Flow\n├── Phase 0: A\n├── Phase 1: B\n```\n"
    assert _find_loop_phase_numbers(text) == []
    assert _collapse_loop_region(phases, text) is phases  # unchanged


def test_noop_when_named_phases_not_contiguous():
    # Tree Diagram Loop node names Phase 1 and Phase 3 but not 2 -> not a clean run -> no collapse.
    phases = [
        {"phase_id": "phase_1", "type": "sequential", "steps": []},
        {"phase_id": "phase_2", "type": "sequential", "steps": []},
        {"phase_id": "phase_3", "type": "sequential", "steps": []},
    ]
    text = _TREE + "Flow\n└── Loop (iterations)\n    ├── Phase 1: X\n    └── Phase 3: Z\n```\n"
    assert _find_loop_phase_numbers(text) == [1, 3]
    assert _collapse_loop_region(phases, text) is phases
