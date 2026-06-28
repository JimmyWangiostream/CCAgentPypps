from pattern_generator.config import PGConfig
from wiki_retrieval.defaults import (
    build_defaults_md, load_defaults, write_defaults,
    load_overrides, retrieve_modeldefault, modeldefault_block,
)
from pattern_generator.stepwise import build_one_unit_prompt, generation_units
from pattern_generator.review import build_review_prompt
from pattern_generator.wholefile import build_wholefile_prompt

WIKI = PGConfig().wiki_path

SMALL_IR = {
    "pattern_id": "PFD", "title": "t",
    "phases": [{"phase_id": "phase_0", "name": "P", "type": "sequential",
                "loop_type": None, "loop_count": None, "steps": [
        {"step_id": "s1", "scsi_cmd": "TUR", "ufs_query": None, "opcode": "0x00",
         "query_opcode": None, "idn": None, "expected": "GOOD",
         "produces": [], "consumes": []}],
        "inputs": [], "outputs": []}],
    "dependency_graph": {"nodes": ["phase_0"], "edges": []},
}


# --- the deterministic merge (against the real wiki/) ---

def test_merge_userprompt_override_before_modeldefault():
    md = build_defaults_md(WIKI)
    assert md.index("UserPrompt overrides") < md.index("ModelDefault base")
    assert "MaxCapacity" in md
    assert "_← UserPrompt" in md


def test_merge_customerreq_constraint():
    md = build_defaults_md(WIKI)
    assert "CustomerReq constraints" in md
    assert "WriteBooster LUN Restriction" in md
    assert "_← CustomerReq_" in md


def test_merge_marks_supersede_with_both_values():
    md = build_defaults_md(WIKI)
    assert "SUPERSEDED" in md
    assert "TestNormalLun = 0" in md            # the DELETED ModelDefault value, named
    assert "MaxCapacity Enabled LUN" in md      # the KEPT UserPrompt value


def test_merge_includes_modeldefault_topics():
    md = build_defaults_md(WIKI)
    assert "_← ModelDefault_" in md
    assert "### data_operations" in md


def test_load_builds_if_missing(tmp_path):
    (tmp_path / "UserPrompt").mkdir()
    (tmp_path / "UserPrompt" / "u.md").write_text("- LUN: pick-max", encoding="utf-8")
    (tmp_path / "ModelDefault").mkdir()
    (tmp_path / "ModelDefault" / "m.md").write_text("base default stuff", encoding="utf-8")
    (tmp_path / "conflicts.md").write_text("# Conflict Log\n", encoding="utf-8")
    out = load_defaults(tmp_path)  # no default.md yet -> builds on the fly
    assert "LUN: pick-max" in out and "base default stuff" in out


def test_write_then_load(tmp_path):
    (tmp_path / "UserPrompt").mkdir()
    (tmp_path / "UserPrompt" / "u.md").write_text("- LUN: pick-max", encoding="utf-8")
    (tmp_path / "ModelDefault").mkdir()
    (tmp_path / "ModelDefault" / "m.md").write_text("dd", encoding="utf-8")
    p = write_defaults(tmp_path)
    assert p.name == "default.md" and p.exists()
    assert "LUN: pick-max" in load_defaults(tmp_path)


# --- always-injection into the prompt builders ---

def test_unit_prompt_injects_defaults():
    p = build_one_unit_prompt(SMALL_IR, generation_units(SMALL_IR)[0],
                              defaults="MYDEFAULTS-XYZ")
    assert "Project defaults (default.md)" in p
    assert "MYDEFAULTS-XYZ" in p
    assert "Do NOT hardcode" in p


def test_review_prompt_injects_defaults_with_enforcement():
    p = build_review_prompt("class P(UFSTC):\n    pass\n", SMALL_IR,
                            defaults="MYDEFAULTS-XYZ")
    assert "MYDEFAULTS-XYZ" in p
    assert "MUST comply" in p


def test_wholefile_injects_defaults():
    p = build_wholefile_prompt(SMALL_IR, "no/such/script", defaults="MYDEFAULTS-XYZ")
    assert "MYDEFAULTS-XYZ" in p


# --- Stage 6: split injection (overrides always, ModelDefault base retrieved) ---

def test_load_overrides_has_overrides_not_base():
    ov = load_overrides(WIKI)
    assert "MaxCapacity" in ov                 # the LUN override is present
    assert "WriteBooster LUN Restriction" in ov
    assert "## (4) ModelDefault base" not in ov  # the bulky base is excluded
    assert "### data_operations" not in ov
    # overrides are a small fraction of the full doc
    assert len(ov) < len(load_defaults(WIKI)) / 5


def test_retrieve_modeldefault_picks_topic_for_write():
    hits = retrieve_modeldefault("WRITE(10) random LBA data", WIKI, k=1)
    assert hits, "expected a ModelDefault topic"
    stem, body = hits[0]
    assert stem == "data_operations"
    assert body


def test_modeldefault_block_renders_provenance():
    blk = modeldefault_block("WRITE(10) random LBA", WIKI, k=1)
    assert "ModelDefault base (retrieved" in blk
    assert "_← ModelDefault_" in blk


def test_retrieve_modeldefault_empty_query():
    assert retrieve_modeldefault("", WIKI) == []
