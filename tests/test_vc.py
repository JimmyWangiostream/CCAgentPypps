"""Tests for the VC (verification-criteria) corpus integration (wiki_retrieval.vc)."""
from wiki_retrieval.vc import load_vc, VcIndex, select_vc


def _write_vc(root, stem, title, body):
    d = root / "VC"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.md").write_text(f"# Test Spec: {title}\n\n{body}\n", encoding="utf-8")


def _mini(tmp_path):
    _write_vc(tmp_path, "PSW_F_P3_APL_0011_Rebuild_EM1_HECC_Test",
              "EM1 HECC SPOR",
              "## Verification Criterion (VC)\nHECC injection then HW_RESET; spor write fail "
              "counter must increment by 1 and LWP pointer must change.\n## Checkpoints\n"
              "verify spor_write_fail_count and collect_lwp_checks after init_tester_to_unit_ready.")
    _write_vc(tmp_path, "PSW_F_P3_Refresh_0001_Refresh_Execute_Test",
              "Refresh Execute",
              "## Verification Criterion (VC)\nTrigger refresh via SSU power conditions and "
              "confirm refresh count advances.")
    return tmp_path


def test_load_vc_forces_vc_layer_and_title(tmp_path):
    docs = load_vc(_mini(tmp_path))
    assert len(docs) == 2
    d = docs["PSW_F_P3_APL_0011_Rebuild_EM1_HECC_Test"]
    assert d.layer == "vc"
    assert "EM1 HECC SPOR" in d.title
    assert d.path.startswith("VC/")


def test_vcindex_keyword_gate(tmp_path):
    idx = VcIndex(_mini(tmp_path), use_dense=False)
    # relevant query -> the HECC/SPOR doc ranks
    hits = idx.rank("HECC spor write fail counter LWP reset", k=3)
    assert hits and hits[0][0] == "PSW_F_P3_APL_0011_Rebuild_EM1_HECC_Test"
    # unrelated query (no keyword overlap) -> no VC surfaced (no noise)
    assert idx.rank("xyzzy nonexistent qqq", k=3) == []


def test_select_vc_prioritizes_pattern_id(tmp_path):
    root = _mini(tmp_path)
    # pattern_id exactly matches the refresh spec stem -> it comes first even on a weak query
    docs = select_vc("refresh", pattern_id="PSW_F_P3_Refresh_0001_Refresh_Execute_Test",
                     cap=3, wiki_root=root, use_dense=False)
    assert docs and docs[0].stem == "PSW_F_P3_Refresh_0001_Refresh_Execute_Test"


def test_select_vc_empty_on_unrelated(tmp_path):
    assert select_vc("zzz qqq nothing", cap=3, wiki_root=_mini(tmp_path), use_dense=False) == []
