import json
from pathlib import Path
import pytest
from pattern_generator.config import PGConfig
from pattern_generator.prepare import (
    prepare_pattern, prepare_unit, _unit_query, _unit_code_query,
)

# IR with two phases connected by a dependency edge: phase_0 -> phase_1.
# phase_1 is listed FIRST in the phases array so we can confirm topo order
# overrides natural list order (phase_0 must still come first).
# Step-level produces/consumes drive the self.* contract: phase_0/s1 produces
# "lun", phase_1/s2 consumes it.
IR_WITH_DEPS = {
    "pattern_id": "PFTEST_0001",
    "title": "Topo Test",
    "description": "Tests that phase_0 steps precede phase_1 steps",
    "tags": [],
    "phases": [
        {
            "phase_id": "phase_1",
            "name": "Second Phase",
            "type": "sequential",
            "loop_type": None,
            "loop_count": None,
            "steps": [
                {"step_id": "s2", "scsi_cmd": "READ(10)", "ufs_query": None,
                 "opcode": "0x28", "query_opcode": None, "idn": None, "expected": "GOOD",
                 "produces": [], "consumes": ["lun"]}
            ],
            "inputs": ["lun"],
            "outputs": [],
        },
        {
            "phase_id": "phase_0",
            "name": "First Phase",
            "type": "sequential",
            "loop_type": None,
            "loop_count": None,
            "steps": [
                {"step_id": "s1", "scsi_cmd": "WRITE(10)", "ufs_query": None,
                 "opcode": "0x2A", "query_opcode": None, "idn": None, "expected": "GOOD",
                 "produces": ["lun"], "consumes": []}
            ],
            "inputs": [],
            "outputs": ["lun"],
        },
    ],
    "dependency_graph": {
        "nodes": ["phase_0", "phase_1"],
        "edges": [{"from": "phase_0", "to": "phase_1", "data_flow": ["lun"]}],
    },
}


# IR with a sequential phase followed by a loop phase (2 sub-steps), to exercise
# loop expansion: 1 seq step + 2 sub-step helpers + 1 deterministic wrapper = 4 units.
IR_WITH_LOOP = {
    "pattern_id": "PFLOOP_0001",
    "title": "Loop Test",
    "description": "Tests loop expansion into helpers + a deterministic wrapper",
    "tags": [],
    "phases": [
        {
            "phase_id": "phase_0",
            "name": "Init",
            "type": "sequential",
            "loop_type": None,
            "loop_count": None,
            "steps": [
                {"step_id": "s1", "scsi_cmd": "TEST UNIT READY", "ufs_query": None,
                 "opcode": "0x00", "query_opcode": None, "idn": None, "expected": "GOOD",
                 "produces": [], "consumes": []}
            ],
            "inputs": [],
            "outputs": [],
        },
        {
            "phase_id": "loop_4",
            "name": "Burn",
            "type": "loop",
            "loop_type": "condition",
            "loop_count": None,
            "steps": [
                {"step_id": "step_1_1", "scsi_cmd": None, "ufs_query": None, "opcode": None,
                 "query_opcode": None, "idn": None, "expected": "", "produces": [], "consumes": []},
                {"step_id": "step_1_2", "scsi_cmd": None, "ufs_query": None, "opcode": None,
                 "query_opcode": None, "idn": None, "expected": "", "produces": [], "consumes": []},
            ],
            "inputs": [],
            "outputs": [],
        },
    ],
    "dependency_graph": {
        "nodes": ["phase_0", "loop_4"],
        "edges": [{"from": "phase_0", "to": "loop_4", "data_flow": []}],
    },
}


def _write_ir(tmp_path, ir=IR_WITH_DEPS, name="pftest-0001-ir.json"):
    ir_path = tmp_path / name
    ir_path.write_text(json.dumps(ir), encoding="utf-8")
    return ir_path


def _cfg(tmp_path):
    return PGConfig(generated_dir=tmp_path / "generated")


# ---------------------------------------------------------------------------
# Code/api-fact retrieval query enrichment (FEED query fix — see diagnosis):
# raw protocol tokens ("WRITE(10)", "POR") retrieve the wrong abstraction layer;
# the unit's data-flow var names ("write_record_p1" -> "write record") bridge to
# the high-level api idioms. Only the CODE-facing query is enriched; the wiki
# query (_unit_query) is unchanged.
# ---------------------------------------------------------------------------

def test_unit_code_query_enriches_with_dataflow_vars():
    unit = {
        "steps": [{"scsi_cmd": "WRITE(10) (2Ah)", "ufs_query": None,
                   "idn": None, "name": "random write"}],
        "produces": ["write_record_p1"],
        "consumes": [],
        "set_vars": ["write_record_p1"],
    }
    base = _unit_query(unit)
    enriched = _unit_code_query(unit)
    # base (wiki) query has only protocol tokens, NOT the api-intent vocabulary
    assert "write record" not in base.lower()
    # enriched (code) query adds underscore-split var vocabulary
    assert "write record" in enriched.lower()
    # and still preserves the original protocol tokens
    assert "WRITE(10)" in enriched


def test_unit_code_query_dedupes_and_handles_empty_vars():
    # produces & set_vars overlap -> token appears once; empty lists are fine.
    unit = {
        "steps": [{"scsi_cmd": None, "ufs_query": "SET FLAG (0x02)",
                   "idn": None, "name": "enable wb"}],
        "produces": ["wb_support_info"],
        "consumes": [],
        "set_vars": ["wb_support_info"],
    }
    q = _unit_code_query(unit).lower()
    assert q.count("wb support info") == 1
    # a unit with no data-flow vars degrades to exactly the base query
    bare = {"steps": [{"scsi_cmd": None, "ufs_query": None, "idn": None,
                       "name": "por reset"}], "produces": [], "consumes": [],
            "set_vars": []}
    assert _unit_code_query(bare) == _unit_query(bare)


def test_prepare_writes_scaffold_units_and_first_prompt(tmp_path):
    """prepare_pattern writes scaffold.py, 1_units.json, and ONLY unit_01 prompt."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    assert (run / "1_units.json").exists()
    assert (run / "scaffold.py").exists()
    prompts = sorted(run.glob("unit_*_prompt.txt"))
    assert len(prompts) == 1, f"Expected only the first unit prompt, got {prompts}"
    assert prompts[0].name.startswith("unit_01_")


def test_prepare_returns_units_and_count(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    assert isinstance(out["units"], list)
    assert out["unit_count"] == 2  # one step per phase = two units
    assert "UFSTC" in out["scaffold"]
    assert out["first_prompt_file"].startswith("unit_01_")
    assert "run_dir" in out


def test_units_named_step1_step2_in_topo_order(tmp_path):
    """Despite phase_1 first in the list, phase_0's step is unit 1 (step1)."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    units = out["units"]
    assert [u["method"] for u in units] == ["step1", "step2"]
    assert units[0]["phase_id"] == "phase_0"
    assert units[1]["phase_id"] == "phase_1"


def test_units_json_on_disk_matches_return(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    on_disk = json.loads((run / "1_units.json").read_text(encoding="utf-8"))
    assert on_disk == out["units"]


def test_scaffold_contains_class_and_markers(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    scaffold = out["scaffold"]
    assert "import package_root" in scaffold
    assert "UFSTC" in scaffold
    assert "# @@EXTRA_IMPORTS@@" in scaffold
    assert "# @@PHASE_METHODS@@" in scaffold
    assert "pre_process" in scaffold
    assert "post_process" in scaffold
    assert "__main__" in scaffold


def test_first_unit_prompt_contains_grounding_rules(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    prompt = (run / out["first_prompt_file"]).read_text(encoding="utf-8")
    assert "gitnexus" in prompt
    assert "call the `query` tool" in prompt  # gitnexus-specific instruction
    assert "## Code candidates" not in prompt  # injected only in direct mode
    assert "=== WIKI REFS ===" in prompt
    assert "=== CODE REFS ===" in prompt
    assert "=== REVIEW FLAGS ===" in prompt
    assert "=== METHODS ===" in prompt


# ---------------------------------------------------------------------------
# Direct grounding mode (no gitnexus): inject candidates from the Script tree
# ---------------------------------------------------------------------------

def _cfg_direct(tmp_path):
    """Direct mode; script_root defaults to the real GitNexusMCP/Script tree."""
    return PGConfig(generated_dir=tmp_path / "generated", grounding_mode="direct")


_HAS_SCRIPT = (PGConfig().script_root / "api").is_dir()
_skip_no_script = pytest.mark.skipif(not _HAS_SCRIPT, reason="GitNexusMCP/Script not present")


def test_prepare_writes_ir_lint(tmp_path):
    """Lever #4: prepare writes ir_lint.md (report-only protocol-path contradictions)."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    lint = Path(out["run_dir"]) / "ir_lint.md"
    assert lint.exists()
    # IR_WITH_DEPS has no WB-support step -> clean
    assert "no contradictions" in lint.read_text(encoding="utf-8")


def test_prepare_ir_lint_does_not_flag_wb_support_descriptor_path(tmp_path):
    # WB support via READ DESCRIPTOR of the Device Descriptor is the CORRECT path, so the
    # ir_lint must NOT flag it (the false-premised _ir_wb_support_path rule was retired).
    ir = {
        "pattern_id": "PFWB_0001", "title": "wb", "description": "", "tags": [],
        "phases": [{"phase_id": "phase_0", "name": "p", "type": "sequential",
                    "loop_type": None, "loop_count": None, "inputs": [], "outputs": [],
                    "steps": [{"step_id": "step_0_1", "name": "check Write Booster support",
                               "scsi_cmd": None, "ufs_query": "READ DESCRIPTOR (0x07)",
                               "opcode": None, "query_opcode": None,
                               "idn": "0x00 (Device Descriptor)", "expected": "",
                               "produces": [], "consumes": []}]}],
        "dependency_graph": {"nodes": ["phase_0"], "edges": []},
    }
    ir_path = tmp_path / "pfwb-0001-ir.json"
    ir_path.write_text(json.dumps(ir), encoding="utf-8")
    out = prepare_pattern(ir_path, _cfg(tmp_path))
    txt = (Path(out["run_dir"]) / "ir_lint.md").read_text(encoding="utf-8")
    assert "no contradictions" in txt
    assert "ir_wrong_protocol_path" not in txt


def test_prepare_writes_defaults_debug(tmp_path):
    """prepare records, deterministically, which defaults were OFFERED to each unit."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    dbg = run / "defaults_debug.md"
    assert dbg.exists()
    txt = dbg.read_text(encoding="utf-8")
    assert "Defaults offered per unit" in txt
    assert "overrides=always" in txt
    assert "modeldefault=" in txt
    # a downstream unit appends another line
    (run / "unit_01_s1_methods.py").write_text(UPSTREAM_METHODS, encoding="utf-8")
    prepare_unit(run, 2, _cfg(tmp_path))
    assert dbg.read_text(encoding="utf-8").count("overrides=always") >= 2


def test_prepare_persists_grounding_meta(tmp_path):
    """Both modes record _run_meta.json so prepare-unit can recover the mode."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    meta = json.loads((Path(out["run_dir"]) / "_run_meta.json").read_text(encoding="utf-8"))
    assert meta["grounding_mode"] == "gitnexus"


@_skip_no_script
def test_prepare_direct_injects_candidates_and_swaps_instructions(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg_direct(tmp_path))
    run = Path(out["run_dir"])
    meta = json.loads((run / "_run_meta.json").read_text(encoding="utf-8"))
    assert meta["grounding_mode"] == "direct"

    prompt = (run / out["first_prompt_file"]).read_text(encoding="utf-8")
    # direct instructions swapped in; gitnexus query instruction gone
    assert "Do NOT use gitnexus" in prompt
    assert "call the `query` tool" not in prompt
    # candidate block injected with real Script symbols (phase_0/s1 = WRITE(10))
    assert "## Code candidates" in prompt
    assert "script rank1" in prompt
    # parsed section headers are unchanged (assemble still works)
    assert "=== CODE REFS ===" in prompt


@_skip_no_script
def test_prepare_unit_recovers_direct_mode_from_meta(tmp_path):
    """prepare-unit (separate CLI call, default gitnexus config) honors the run's
    persisted direct mode and still injects candidates."""
    out = prepare_pattern(_write_ir(tmp_path), _cfg_direct(tmp_path))
    run = Path(out["run_dir"])
    (run / "unit_01_s1_methods.py").write_text(UPSTREAM_METHODS, encoding="utf-8")

    # NB: default config (gitnexus) — mode must come from _run_meta.json.
    res = prepare_unit(run, 2, _cfg(tmp_path))
    prompt = (run / res["prompt_file"]).read_text(encoding="utf-8")
    assert "## Code candidates" in prompt
    assert "Do NOT use gitnexus" in prompt


# ---------------------------------------------------------------------------
# prepare_unit — lazy downstream prompt with upstream continuity
# ---------------------------------------------------------------------------

UPSTREAM_METHODS = """\
=== WIKI REFS ===
- entities/lun.md
=== CODE REFS ===
- Script/api/cmd_seq/cmds.py: Write10 (gitnexus rank1)
=== REVIEW FLAGS ===
=== EXTRA IMPORTS ===
=== METHODS ===
    def step1(self) -> None:
        self.lun = 3
"""


def test_prepare_unit_embeds_upstream_methods_and_contract(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    # Simulate the LLM having produced unit 1's methods.
    (run / "unit_01_s1_methods.py").write_text(UPSTREAM_METHODS, encoding="utf-8")

    res = prepare_unit(run, 2, _cfg(tmp_path))
    prompt = (run / res["prompt_file"]).read_text(encoding="utf-8")

    # upstream method source is embedded
    assert "self.lun = 3" in prompt
    assert "STAY CONSISTENT" in prompt
    # upstream grounded symbol carried over
    assert "Write10" in prompt
    # self.* contract: unit 2 consumes lun, available from upstream
    assert "self.lun" in prompt
    assert "available from upstream" in prompt
    assert res["prompt_file"].startswith("unit_02_")


def test_prepare_unit_fails_when_upstream_missing(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    # unit_01 methods NOT written -> preparing unit 2 must fail fast
    with pytest.raises(FileNotFoundError):
        prepare_unit(run, 2, _cfg(tmp_path))


def test_prepare_unit_rejects_out_of_range(tmp_path):
    out = prepare_pattern(_write_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    with pytest.raises(ValueError):
        prepare_unit(run, 99, _cfg(tmp_path))


# ---------------------------------------------------------------------------
# Loop expansion: helpers + a deterministic, pre-written wrapper
# ---------------------------------------------------------------------------

def _write_loop_ir(tmp_path):
    return _write_ir(tmp_path, IR_WITH_LOOP, name="pfloop-0001-ir.json")


def test_prepare_loop_expands_and_prewrites_wrapper(tmp_path):
    """A loop phase expands into 1 seq + 2 sub-step helpers + 1 wrapper = 4 units;
    the wrapper's methods file is written deterministically up front, and only the
    first (seq) unit gets a prompt."""
    out = prepare_pattern(_write_loop_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    assert out["unit_count"] == 4
    assert [u["kind"] for u in out["units"]] == [
        "step", "loop_substep", "loop_substep", "loop_wrapper"]

    wrappers = list(run.glob("unit_*_wrapper_methods.py"))
    assert len(wrappers) == 1
    assert wrappers[0].name == "unit_04_loop_4_wrapper_methods.py"

    prompts = sorted(run.glob("unit_*_prompt.txt"))
    assert len(prompts) == 1
    assert prompts[0].name.startswith("unit_01_")


def test_prepare_unit_wrapper_is_skipped(tmp_path):
    """prepare_unit on the wrapper index re-writes the methods file and reports
    skipped (no LLM prompt) instead of raising."""
    out = prepare_pattern(_write_loop_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    res = prepare_unit(run, 4, _cfg(tmp_path))
    assert res.get("skipped") is True
    assert res["prompt_file"] is None
    assert (run / "unit_04_loop_4_wrapper_methods.py").exists()


def test_prepare_unit_after_loop_helper_embeds_upstream(tmp_path):
    """A loop helper unit can be prepared once its upstream (seq step) methods exist,
    and the wrapper file pre-written by prepare counts as 'existing' upstream."""
    out = prepare_pattern(_write_loop_ir(tmp_path), _cfg(tmp_path))
    run = Path(out["run_dir"])
    (run / "unit_01_s1_methods.py").write_text(UPSTREAM_METHODS, encoding="utf-8")
    res = prepare_unit(run, 2, _cfg(tmp_path))  # first loop sub-step helper
    assert res["prompt_file"].startswith("unit_02_")
    prompt = (run / res["prompt_file"]).read_text(encoding="utf-8")
    assert "_loop4_step_1_1" in prompt
    assert "loop_idx" in prompt
