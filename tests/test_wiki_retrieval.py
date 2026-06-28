"""Tests for the layered wiki retrieval package (graph + BM25 + RRF + essence).

All run with dense disabled (BM25 + graph), so no model/network is needed.
"""
import pytest

from wiki_retrieval.corpus import (
    load_corpus, parse_conflicts, extract_wikilinks, WikiDoc,
)
from wiki_retrieval.graph import build_graph
from wiki_retrieval.bm25 import BM25Index, tokenize, _stem
from wiki_retrieval.retrieve import rrf, Retriever
from wiki_retrieval.essence import build_essence, format_top_refs


# ---------------------------------------------------------------------------
# corpus + graph (step 2)
# ---------------------------------------------------------------------------

class TestCorpusGraph:

    def test_extract_wikilinks_dedupes(self):
        body = "see [[lun]] and [[lun]] and [[psa-state]]"
        assert extract_wikilinks(body) == ["lun", "psa-state"]

    def test_corpus_loads_layers(self):
        docs = load_corpus()
        assert docs, "wiki corpus should load"
        layers = {d.layer for d in docs.values()}
        assert "concept" in layers and "entity" in layers

    def test_graph_resolves_wikilink_to_edge(self):
        a = WikiDoc(stem="a", path="concepts/a.md", layer="concept", title="A",
                    refs=["b"])
        b = WikiDoc(stem="b", path="entities/b.md", layer="entity", title="B")
        g = build_graph({"a": a, "b": b})
        assert "b" in g.adj["a"]
        assert "a" in g.radj["b"]

    def test_graph_resolves_alias(self):
        a = WikiDoc(stem="a", path="concepts/a.md", layer="concept", title="A",
                    refs=["WB"])
        wb = WikiDoc(stem="write-booster", path="entities/write-booster.md",
                     layer="entity", title="WB", aliases=["WB"])
        g = build_graph({"a": a, "write-booster": wb})
        assert "write-booster" in g.adj["a"]

    def test_neighbors_filters_by_layer_and_hops(self):
        a = WikiDoc("a", "concepts/a.md", "concept", "A", refs=["b"])
        b = WikiDoc("b", "entities/b.md", "entity", "B", refs=["c"])
        c = WikiDoc("c", "entities/c.md", "entity", "C")
        g = build_graph({"a": a, "b": b, "c": c})
        assert g.neighbors("a", types={"entity"}, hops=1) == ["b"]
        assert set(g.neighbors("a", types={"entity"}, hops=2)) == {"b", "c"}

    def test_conflicts_parsed_with_affected_pages(self):
        conflicts = parse_conflicts()
        assert conflicts, "real wiki has conflicts"
        assert any("write-booster" in c.affected for c in conflicts)
        # two independent rules represented
        rules = " ".join(c.rule for c in conflicts)
        assert "Rule 1" in rules and "Rule 2" in rules


# ---------------------------------------------------------------------------
# BM25 (step 4 sparse)
# ---------------------------------------------------------------------------

class TestBM25:

    def test_stem_folds_plurals(self):
        assert _stem("attributes") == "attribute"
        assert _stem("flags") == "flag"
        assert _stem("ss") == "ss"          # too short / -ss untouched

    def test_tokenize_applies_stem(self):
        assert "attribute" in tokenize("READ ATTRIBUTE")
        assert "attribute" in tokenize("UFS Attributes")

    def test_ranks_relevant_doc_first(self):
        docs = [("a", "write booster flush buffer enable"),
                ("b", "power management hibernate"),
                ("c", "garbage collection background")]
        idx = BM25Index(docs)
        ranked = idx.rank("write booster flush")
        assert ranked[0][0] == "a"

    def test_no_match_returns_empty(self):
        idx = BM25Index([("a", "alpha beta")])
        assert idx.rank("zzzznothing") == []


# ---------------------------------------------------------------------------
# RRF + retrieve (step 4) + essence (step 5)
# ---------------------------------------------------------------------------

class TestRetrieve:

    def test_rrf_fuses_two_rankings(self):
        r1 = [("a", 9), ("b", 8)]
        r2 = [("b", 9), ("a", 8)]
        fused = dict(rrf([r1, r2]))
        assert set(fused) == {"a", "b"}

    def test_rrf_single_ranking_preserves_order(self):
        fused = [s for s, _ in rrf([[("a", 9), ("b", 8), ("c", 7)]])]
        assert fused == ["a", "b", "c"]

    def test_retrieve_finds_write_booster_pages(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("write booster flush enable", top_n=5)
        assert res.has_match
        # write-booster surfaces as a direct/expanded entity
        assert "write-booster" in res.entities

    def test_retrieve_surfaces_conflict_on_affected_page(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("write booster set flag", top_n=5)
        assert res.conflicts, "WB pages are conflict-affected"

    def test_retrieve_no_match(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("zzzz nonsense qqqq", top_n=5)
        assert not res.has_match

    def test_essence_has_concept_and_entity(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("write booster set flag", top_n=5)
        text = build_essence(res)
        assert "Wiki essence" in text
        assert "entities:" in text
        # The weak conflict pointer was removed from essence — the RESOLVED overrides
        # now live in wiki/default.md (always-injected). See test_defaults.py.
        assert "authority overrides" not in text

    def test_essence_no_match_message(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("zzzz nonsense qqqq", top_n=5)
        assert "NO MATCH" in build_essence(res)

    def test_format_top_refs_has_rank_and_path(self):
        r = Retriever(use_dense=False)
        res = r.retrieve("PSA production state", top_n=5)
        refs = format_top_refs(res)
        assert refs and "rank1" in refs[0]
        assert refs[0].endswith(".md (rank1)")


# Dense smoke test — only runs if the optional embedder is installed.
def test_dense_path_smoke():
    pytest.importorskip("sentence_transformers")
    r = Retriever(use_dense=True)
    res = r.retrieve("write booster flush", top_n=5)
    assert res.has_match
