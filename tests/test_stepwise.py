"""Tests for pattern_generator.stepwise: topo_order_phases and ordered_steps."""
import pytest
from pattern_generator.stepwise import (
    topo_order_phases,
    ordered_steps,
    generation_units,
    build_one_unit_prompt,
    build_loop_wrapper_method,
    build_loop_wrapper_section,
    extract_helper_signatures,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_phase(phase_id, steps=1, loop_type=None, loop_count=None,
                inputs=None, outputs=None, name=None, ptype="sequential"):
    return {
        "phase_id": phase_id,
        "name": name or phase_id,
        "type": ptype,
        "loop_type": loop_type,
        "loop_count": loop_count,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "steps": [{"step_id": f"{phase_id}_s{i}"} for i in range(steps)],
    }


def _make_ir(phases, edges=None):
    return {
        "pattern_id": "TEST",
        "title": "test",
        "description": "",
        "phases": phases,
        "dependency_graph": {
            "nodes": [p["phase_id"] for p in phases],
            "edges": edges or [],
        },
    }


# ---------------------------------------------------------------------------
# topo_order_phases
# ---------------------------------------------------------------------------

class TestTopoOrderPhases:

    def test_no_edges_returns_natural_order(self):
        """With no dependency edges, phases come back in IR list order."""
        ir = _make_ir([_make_phase("a"), _make_phase("b"), _make_phase("c")])
        assert topo_order_phases(ir) == ["a", "b", "c"]

    def test_missing_dependency_graph_falls_back(self):
        """IR with no dependency_graph key returns natural order."""
        ir = {
            "pattern_id": "X",
            "phases": [_make_phase("x"), _make_phase("y")],
        }
        assert topo_order_phases(ir) == ["x", "y"]

    def test_empty_phases_returns_empty(self):
        ir = _make_ir([])
        assert topo_order_phases(ir) == []

    def test_single_edge_orders_dependency_first(self):
        """a -> b means a must come before b."""
        # Present b first in the list to prove topo overrides list order.
        ir = _make_ir(
            [_make_phase("b"), _make_phase("a")],
            edges=[{"from": "a", "to": "b"}],
        )
        order = topo_order_phases(ir)
        assert order.index("a") < order.index("b")

    def test_chain_a_b_c(self):
        """a -> b -> c: must come out [a, b, c]."""
        ir = _make_ir(
            [_make_phase("c"), _make_phase("b"), _make_phase("a")],
            edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
        )
        assert topo_order_phases(ir) == ["a", "b", "c"]

    def test_two_roots_converge(self):
        """a -> c and b -> c: a and b come before c (order between a/b not fixed)."""
        ir = _make_ir(
            [_make_phase("c"), _make_phase("b"), _make_phase("a")],
            edges=[{"from": "a", "to": "c"}, {"from": "b", "to": "c"}],
        )
        order = topo_order_phases(ir)
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("c")

    def test_cycle_safety_all_phases_present(self):
        """Even with a cycle (a->b, b->a), all phase_ids appear in output."""
        ir = _make_ir(
            [_make_phase("a"), _make_phase("b")],
            edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
        )
        order = topo_order_phases(ir)
        assert set(order) == {"a", "b"}


# ---------------------------------------------------------------------------
# ordered_steps
# ---------------------------------------------------------------------------

class TestOrderedSteps:

    def test_empty_ir_returns_empty(self):
        ir = _make_ir([])
        assert ordered_steps(ir) == []

    def test_single_phase_single_step(self):
        ir = _make_ir([_make_phase("p0", steps=1)])
        steps = ordered_steps(ir)
        assert len(steps) == 1
        s = steps[0]
        assert s["seq"] == 1
        assert s["method"] == "step1"
        assert s["phase_id"] == "p0"

    def test_sequential_method_naming(self):
        """Three phases with 1 step each: method names step1, step2, step3."""
        ir = _make_ir([
            _make_phase("a", steps=1),
            _make_phase("b", steps=1),
            _make_phase("c", steps=1),
        ])
        steps = ordered_steps(ir)
        assert [s["method"] for s in steps] == ["step1", "step2", "step3"]
        assert [s["seq"] for s in steps] == [1, 2, 3]

    def test_multi_step_phase_flattens_correctly(self):
        """A phase with 3 steps produces 3 entries with consecutive seqs."""
        ir = _make_ir([_make_phase("p", steps=3)])
        steps = ordered_steps(ir)
        assert len(steps) == 3
        assert [s["method"] for s in steps] == ["step1", "step2", "step3"]
        assert all(s["phase_id"] == "p" for s in steps)

    def test_phase_context_carried_on_each_step(self):
        """Every step carries phase_name, phase_type, loop_type, loop_count,
        phase_inputs, phase_outputs."""
        ir = _make_ir([
            _make_phase("loop_ph", steps=2, ptype="loop",
                        loop_type="count", loop_count=50,
                        inputs=["lun"], outputs=["result"],
                        name="Stress Loop"),
        ])
        steps = ordered_steps(ir)
        for s in steps:
            assert s["phase_name"] == "Stress Loop"
            assert s["phase_type"] == "loop"
            assert s["loop_type"] == "count"
            assert s["loop_count"] == 50
            assert s["phase_inputs"] == ["lun"]
            assert s["phase_outputs"] == ["result"]

    def test_topological_order_in_ordered_steps(self):
        """phase_0 -> phase_1: phase_0's steps come before phase_1's steps
        even when phase_1 appears first in the phases list."""
        ir = _make_ir(
            [_make_phase("phase_1", steps=1), _make_phase("phase_0", steps=1)],
            edges=[{"from": "phase_0", "to": "phase_1"}],
        )
        steps = ordered_steps(ir)
        assert steps[0]["phase_id"] == "phase_0"
        assert steps[1]["phase_id"] == "phase_1"
        # method names must still be step1/step2 in emission order
        assert steps[0]["method"] == "step1"
        assert steps[1]["method"] == "step2"

    def test_step_payload_is_preserved(self):
        """The raw step dict from the IR must appear as steps[i]['step']."""
        raw_step = {"step_id": "s99", "scsi_cmd": "INQUIRY", "opcode": "0x12"}
        ir = _make_ir([{
            "phase_id": "p",
            "name": "p",
            "type": "sequential",
            "loop_type": None,
            "loop_count": None,
            "inputs": [],
            "outputs": [],
            "steps": [raw_step],
        }])
        steps = ordered_steps(ir)
        assert steps[0]["step"] == raw_step


# ---------------------------------------------------------------------------
# generation_units — the by-unit (aggressive) granularity
# ---------------------------------------------------------------------------

def _step(step_id, produces=None, consumes=None, name=""):
    return {"step_id": step_id, "name": name,
            "produces": produces or [], "consumes": consumes or []}


def _ir_with_steps(phases, edges=None):
    return {
        "pattern_id": "TEST", "title": "test", "description": "",
        "phases": phases,
        "dependency_graph": {"nodes": [p["phase_id"] for p in phases], "edges": edges or []},
    }


class TestGenerationUnits:

    def test_sequential_phase_splits_per_step(self):
        """A 3-step sequential phase yields 3 separate units (aggressive split)."""
        ir = _ir_with_steps([{
            "phase_id": "phase_0", "name": "init", "type": "sequential",
            "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("s1"), _step("s2"), _step("s3")],
        }])
        units = generation_units(ir)
        assert len(units) == 3
        assert [u["method"] for u in units] == ["step1", "step2", "step3"]
        assert all(u["kind"] == "step" for u in units)
        assert [u["unit_id"] for u in units] == ["s1", "s2", "s3"]

    def test_loop_phase_expands_to_helpers_plus_wrapper(self):
        """A loop phase expands into one helper unit per sub-step + a deterministic
        stepN wrapper that drives the for-loop over them."""
        ir = _ir_with_steps([{
            "phase_id": "loop_4", "name": "burn", "type": "loop",
            "loop_type": "condition", "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("a"), _step("b"), _step("c")],
        }])
        units = generation_units(ir)
        assert len(units) == 4
        assert [u["kind"] for u in units] == [
            "loop_substep", "loop_substep", "loop_substep", "loop_wrapper"]
        assert [u["method"] for u in units] == [
            "_loop4_a", "_loop4_b", "_loop4_c", "step1"]
        wrapper = units[-1]
        assert wrapper["method"] == "step1"
        assert wrapper["unit_id"] == "loop_4"
        assert wrapper["helper_methods"] == ["_loop4_a", "_loop4_b", "_loop4_c"]
        assert all(u["loop_idx_param"] for u in units[:3])
        assert [u["index"] for u in units] == [1, 2, 3, 4]

    def test_pf010_like_shape_six_steps_plus_loop(self):
        """phase_0 (6 steps) + loop_4 (3 sub-steps) -> 6 step units + 3 helper
        units + 1 wrapper = 10; wrapper is step7 (step_no skips helpers)."""
        ir = _ir_with_steps(
            [
                {"phase_id": "phase_0", "name": "init", "type": "sequential",
                 "loop_type": None, "loop_count": None, "inputs": [],
                 "outputs": ["max_lba"],
                 "steps": [_step(f"step_0_{i}") for i in range(1, 7)]},
                {"phase_id": "loop_4", "name": "burn", "type": "loop",
                 "loop_type": "condition", "loop_count": None,
                 "inputs": ["max_lba"], "outputs": [],
                 "steps": [_step(f"step_1_{i}") for i in range(1, 4)]},
            ],
            edges=[{"from": "phase_0", "to": "loop_4", "data_flow": ["max_lba"]}],
        )
        units = generation_units(ir)
        assert len(units) == 10
        assert [u["method"] for u in units] == (
            [f"step{i}" for i in range(1, 7)]
            + ["_loop4_step_1_1", "_loop4_step_1_2", "_loop4_step_1_3"]
            + ["step7"]
        )
        assert [u["kind"] for u in units[:6]] == ["step"] * 6
        assert [u["kind"] for u in units[6:9]] == ["loop_substep"] * 3
        assert units[9]["kind"] == "loop_wrapper"
        assert units[9]["method"] == "step7"
        assert [u["index"] for u in units] == list(range(1, 11))

    def test_loop_expansion_step_no_skips_helpers(self):
        """Wrapper's stepN number counts only real steps + wrappers; file indices
        stay contiguous across helpers."""
        ir = _ir_with_steps(
            [
                {"phase_id": "phase_0", "name": "init", "type": "sequential",
                 "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
                 "steps": [_step("step_0_1"), _step("step_0_2")]},
                {"phase_id": "loop_4", "name": "burn", "type": "loop",
                 "loop_type": "condition", "loop_count": None, "inputs": [], "outputs": [],
                 "steps": [_step(f"step_1_{i}") for i in range(1, 4)]},
            ],
            edges=[{"from": "phase_0", "to": "loop_4"}],
        )
        units = generation_units(ir)
        helpers = [u for u in units if u["kind"] == "loop_substep"]
        wrappers = [u for u in units if u["kind"] == "loop_wrapper"]
        assert len(helpers) == 3 and len(wrappers) == 1
        assert wrappers[0]["helper_methods"] == [h["method"] for h in helpers]
        assert wrappers[0]["method"] == "step3"   # 2 seq steps -> step1,step2; wrapper -> step3
        assert [u["index"] for u in units] == [1, 2, 3, 4, 5, 6]
        assert [u["method"] for u in units if u["kind"] != "loop_substep"] == [
            "step1", "step2", "step3"]

    def test_self_contract_set_and_available(self):
        """A producer step exposes self.X (set_vars); a downstream consumer sees
        self.X in available_vars."""
        ir = _ir_with_steps([{
            "phase_id": "p", "name": "p", "type": "sequential",
            "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
            "steps": [
                _step("s1", produces=["max_alloc_units"]),
                _step("s2"),
                _step("s3", consumes=["max_alloc_units"]),
            ],
        }])
        units = generation_units(ir)
        # s1 produces a var consumed downstream -> must set self.max_alloc_units
        assert "max_alloc_units" in units[0]["set_vars"]
        # s3 sees it as available from upstream
        assert "max_alloc_units" in units[2]["available_vars"]
        # s3 declares the need
        assert "max_alloc_units" in units[2]["consumes"]

    def test_produces_not_consumed_downstream_is_not_set(self):
        """A produced var that nobody downstream consumes and is not a phase output
        is NOT forced into self.* (set_vars empty)."""
        ir = _ir_with_steps([{
            "phase_id": "p", "name": "p", "type": "sequential",
            "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("s1", produces=["scratch"]), _step("s2")],
        }])
        units = generation_units(ir)
        assert units[0]["set_vars"] == []

    def test_phase_output_forces_set_var(self):
        """A produced var that is a phase output must be set even if no later step
        in this IR consumes it (it crosses the phase boundary)."""
        ir = _ir_with_steps([{
            "phase_id": "p", "name": "p", "type": "sequential",
            "loop_type": None, "loop_count": None, "inputs": [],
            "outputs": ["max_lba"],
            "steps": [_step("s1", produces=["max_lba"])],
        }])
        units = generation_units(ir)
        assert "max_lba" in units[0]["set_vars"]


# ---------------------------------------------------------------------------
# build_one_unit_prompt + extract_helper_signatures
# ---------------------------------------------------------------------------

class TestBuildOneUnitPrompt:

    def _units(self):
        ir = _ir_with_steps([{
            "phase_id": "p", "name": "p", "type": "sequential",
            "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
            "steps": [
                _step("s1", produces=["max_lba"]),
                _step("s2", consumes=["max_lba"]),
            ],
        }])
        return ir, generation_units(ir)

    def test_prompt_states_single_method_name(self):
        ir, units = self._units()
        prompt = build_one_unit_prompt(ir, units[0])
        assert "Method name: step1" in prompt
        assert "=== WIKI REFS ===" in prompt
        assert "=== CODE REFS ===" in prompt
        assert "=== REVIEW FLAGS ===" in prompt
        assert "=== METHODS ===" in prompt
        assert "gitnexus" in prompt

    def test_loop_substep_prompt_mentions_helper_signature(self):
        """The first loop unit is a sub-step helper; its prompt states the helper
        name + loop_idx signature and forbids writing the loop itself."""
        ir = _ir_with_steps([{
            "phase_id": "loop_4", "name": "burn", "type": "loop",
            "loop_type": "condition", "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("a"), _step("b")],
        }])
        units = generation_units(ir)
        assert units[0]["kind"] == "loop_substep"
        prompt = build_one_unit_prompt(ir, units[0])
        assert "_loop4_a" in prompt
        assert "loop_idx" in prompt
        assert "do NOT write the for" in prompt

    def test_loop_wrapper_unit_has_no_prompt(self):
        """A loop_wrapper is deterministic — asking for its prompt must raise."""
        ir = _ir_with_steps([{
            "phase_id": "loop_4", "name": "burn", "type": "loop",
            "loop_type": "condition", "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("a"), _step("b")],
        }])
        units = generation_units(ir)
        wrapper = units[-1]
        assert wrapper["kind"] == "loop_wrapper"
        with pytest.raises(ValueError):
            build_one_unit_prompt(ir, wrapper)

    def test_legacy_loop_unit_prompt_still_inlines(self):
        """Back-compat: a hand-built kind='loop' unit (old 1_units.json snapshot)
        still renders the inlined-loop instructions."""
        ir = _ir_with_steps([{
            "phase_id": "loop_4", "name": "burn", "type": "loop",
            "loop_type": "condition", "loop_count": None, "inputs": [], "outputs": [],
            "steps": [_step("a"), _step("b")],
        }])
        unit = {
            "index": 1, "method": "step1", "kind": "loop", "unit_id": "loop_4",
            "phase_id": "loop_4", "phase_name": "burn", "phase_type": "loop",
            "loop_type": "condition", "loop_count": None,
            "steps": [_step("a"), _step("b")],
            "produces": [], "consumes": [], "helper_methods": [],
            "loop_idx_param": False, "set_vars": [], "available_vars": [],
        }
        prompt = build_one_unit_prompt(ir, unit)
        assert "loop body inlined" in prompt
        assert "do NOT create loopN" in prompt

    def test_set_contract_in_prompt(self):
        ir, units = self._units()
        prompt = build_one_unit_prompt(ir, units[0])
        assert "self.max_lba" in prompt
        assert "MUST set" in prompt

    def test_available_contract_in_downstream_prompt(self):
        ir, units = self._units()
        prompt = build_one_unit_prompt(ir, units[1])
        assert "self.max_lba" in prompt
        assert "available from upstream" in prompt

    def test_upstream_methods_embedded(self):
        ir, units = self._units()
        upstream = "    def step1(self) -> None:\n        self.max_lba = 100"
        prompt = build_one_unit_prompt(
            ir, units[1],
            upstream_methods=upstream,
            upstream_code_refs=["Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus rank1)"],
            upstream_helpers=["def _parse_rc(self, rsp)"],
        )
        assert "STAY CONSISTENT" in prompt
        assert "self.max_lba = 100" in prompt
        assert "ReadCapacity10" in prompt
        assert "_parse_rc" in prompt

    def test_wiki_injection_and_no_match(self):
        ir, units = self._units()
        with_wiki = build_one_unit_prompt(
            ir, units[0], wiki_essence="## Wiki essence — query: x\nprinciples",
            wiki_top=["concepts/psa.md (rank1)"], wiki_has_match=True)
        assert "Wiki references (RRF top-5)" in with_wiki
        assert "concepts/psa.md" in with_wiki

        no_wiki = build_one_unit_prompt(ir, units[0], wiki_has_match=False)
        assert "Wiki references: NO MATCH" in no_wiki
        assert "TODO-REVIEW-NO-WIKI" in no_wiki

    def test_extract_helper_signatures_skips_steps(self):
        methods = (
            "    def step1(self) -> None:\n        pass\n\n"
            "    def _parse_rc(self, rsp) -> int:\n        return 0\n"
        )
        sigs = extract_helper_signatures(methods)
        assert any("_parse_rc" in s for s in sigs)
        assert not any("step1" in s for s in sigs)


# ---------------------------------------------------------------------------
# build_loop_wrapper_method / build_loop_wrapper_section
# ---------------------------------------------------------------------------

class TestLoopWrapper:

    def _wrapper(self, loop_type="condition", loop_count=None):
        ir = _ir_with_steps([{
            "phase_id": "loop_4", "name": "burn", "type": "loop",
            "loop_type": loop_type, "loop_count": loop_count, "inputs": [], "outputs": [],
            "steps": [_step("step_1_1"), _step("step_1_2")],
        }])
        units = generation_units(ir)
        return units[-1]

    def test_condition_loop_emits_todo_constant_and_helper_calls(self):
        m = build_loop_wrapper_method(self._wrapper())
        assert "def step1(self) -> None:" in m
        assert "for loop_idx in range(_LOOP_ITERATIONS):" in m
        assert "TODO human-confirm" in m
        assert "self._loop4_step_1_1(loop_idx)" in m
        assert "self._loop4_step_1_2(loop_idx)" in m

    def test_count_loop_emits_literal_for_validator(self):
        m = build_loop_wrapper_method(self._wrapper(loop_type="count", loop_count=50))
        # the validator's structure check requires the literal loop_count in source
        assert "range(50)" in m
        assert "TODO human-confirm" not in m

    def test_wrapper_section_is_parseable_methods_block(self):
        from pattern_generator.assemble import _parse_unit_methods
        section = build_loop_wrapper_section(self._wrapper())
        parsed = _parse_unit_methods(section)
        assert "def step1(self) -> None:" in parsed.methods
        assert "self._loop4_step_1_1(loop_idx)" in parsed.methods

    def test_wrapper_not_flagged_no_code_ref(self):
        """The pure-glue wrapper has no API call, so it must not raise a review flag."""
        from pattern_generator.assemble import _parse_unit_methods, _derive_review_flags
        parsed = _parse_unit_methods(build_loop_wrapper_section(self._wrapper()))
        assert _derive_review_flags(parsed) == []
