"""Tests for the direct-Script code retriever (no gitnexus).

These run against the real GitNexusMCP/Script tree (PGConfig.script_root) — the
same library the validator's api-grounding check reads.
"""
import pytest

from pattern_generator.config import PGConfig
from code_retrieval.index import build_symbol_index, SymbolDoc, _split_identifier
from code_retrieval.retrieve import retrieve_code

SCRIPT_ROOT = PGConfig().script_root

pytestmark = pytest.mark.skipif(
    not (SCRIPT_ROOT / "api").is_dir(),
    reason="GitNexusMCP/Script not present",
)


def test_index_builds_many_symbols():
    docs = build_symbol_index(SCRIPT_ROOT)
    assert len(docs) > 500
    assert all(isinstance(d, SymbolDoc) for d in docs)
    # every symbol carries a real location + a rendered signature
    for d in docs[:50]:
        assert d.path.endswith(".py")
        assert d.lineno >= 1
        assert d.signature.startswith(d.name + "(") or d.signature.startswith(d.name)


def test_split_identifier_handles_camel_and_snake():
    assert _split_identifier("TestUnitReady") == "Test Unit Ready"
    assert _split_identifier("random_write") == "random write"
    assert _split_identifier("ReadCapacity10") == "Read Capacity 10"


def test_retrieve_finds_test_unit_ready():
    refs = retrieve_code("TEST UNIT READY confirm device ready", SCRIPT_ROOT, k=5)
    names = [r.doc.display for r in refs]
    assert any("TestUnitReady" in n for n in names), names


def test_retrieve_random_write_signature_has_params():
    refs = retrieve_code("random_write WRITE(10) compare cmd_count", SCRIPT_ROOT, k=5)
    top = refs[0]
    assert top.doc.name == "random_write"
    assert "rw_functions.py" in top.doc.path
    # the rendered signature exposes the real parameter list (anti-conflation aid)
    assert "cmd_count" in top.doc.signature
    assert "min_lba" in top.doc.signature


def test_render_includes_path_signature_and_rank():
    refs = retrieve_code("READ CAPACITY 25h max lba", SCRIPT_ROOT, k=3)
    line = refs[0].render()
    assert refs[0].doc.path in line
    assert "(script rank1)" in line
    assert " — " in line  # path: Symbol — signature


def test_empty_query_returns_nothing():
    assert retrieve_code("", SCRIPT_ROOT) == []
    assert retrieve_code("   ", SCRIPT_ROOT) == []
