"""Tests for procedure idioms (pattern_generator.procedure_idioms) — the anti-fake guard
for multi-step intents where no single API exists (the LUN-selection bug class)."""
from pattern_generator.procedure_idioms import match_procedures
from pattern_generator.stepwise import generation_units, build_one_unit_prompt


def test_max_capacity_lun_fires():
    g = match_procedures("select the max capacity enabled lun")
    assert len(g) == 1
    assert "get_max_number_of_lun" in g[0]        # names the wrong single API to avoid
    assert "get_unit_descriptor" in g[0]          # anchors the real procedure


def test_no_fire_when_tokens_incomplete():
    assert match_procedures("enable write booster on the lun") == []   # no 'capacity'
    assert match_procedures("max transfer size") == []                 # no 'lun'


def test_procedure_block_rendered_in_prompt():
    ir = {"pattern_id": "PF999", "title": "t", "phases": [{"phase_id": "phase_0", "name": "p",
          "type": "sequential", "steps": [{"step_id": "step_0_1", "name": "pick capacity lun",
          "ufs_query": None, "produces": ["max_capacity_lun"], "consumes": []}]}]}
    u = generation_units(ir)[0]
    p = build_one_unit_prompt(ir, u, procedures=match_procedures("capacity lun max_capacity_lun"))
    assert "## Procedure idioms (AUTHORITATIVE" in p
    assert "get_max_number_of_lun" in p
