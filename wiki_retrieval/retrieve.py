"""Step 4 — layered retrieval: Concept index -> graph traversal -> Entity index,
each fusing BM25 (sparse) and optional dense via Reciprocal Rank Fusion (RRF).

Always available: BM25 + reference-graph traversal. Dense is layered on only when
an embedder is available; RRF degrades gracefully to the single BM25 ranking.
"""
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

from wiki_retrieval.corpus import load_corpus, parse_conflicts
from wiki_retrieval.graph import build_graph
from wiki_retrieval.bm25 import BM25Index
from wiki_retrieval.embedder import Embedder
from wiki_retrieval import index_store


def rrf(rankings: list, k: int = 60) -> list:
    """Reciprocal Rank Fusion. rankings: list of [(stem, score), ...].

    Returns fused [(stem, rrf_score), ...] desc. With one ranking this is just
    that ranking re-scored (order preserved).
    """
    fused: dict = defaultdict(float)
    for ranking in rankings:
        for rank, (stem, _score) in enumerate(ranking, start=1):
            fused[stem] += 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


@dataclass
class EssenceResult:
    query: str
    concepts: list                       # [(stem, score), ...]
    entities: list                       # [stem, ...] (direct ⊕ graph-expanded)
    expanded: list                       # [stem, ...] entities reached via graph
    conflicts: list                      # [Conflict, ...] touching a retrieved page
    top: list                            # [stem, ...] top-N overall (the "top 5")
    docs: dict = field(default_factory=dict)
    dense_used: bool = False
    vc: list = field(default_factory=list)   # [(stem, score), ...] verification-criteria band

    @property
    def has_match(self) -> bool:
        return bool(self.concepts or self.entities or self.vc)


class Retriever:
    def __init__(self, wiki_root=None, use_dense: bool = True, embedder: Embedder | None = None):
        self.wiki_root = wiki_root
        self.docs = load_corpus(wiki_root, layer_dirs=("concepts", "entities"))
        self.graph = build_graph(self.docs)
        self.conflicts = parse_conflicts(wiki_root)

        self._by_layer = {"concept": [], "entity": []}
        for stem, d in self.docs.items():
            layer = d.layer if d.layer in self._by_layer else (
                "concept" if d.path.startswith("concepts/") else "entity")
            self._by_layer[layer].append(stem)

        self.bm25 = {
            layer: BM25Index([(s, self.docs[s].search_text()) for s in stems])
            for layer, stems in self._by_layer.items()
        }

        # Dense (optional). Use prebuilt embeddings if present; else compute live
        # when an embedder is available. Disabled entirely when neither holds.
        self.embedder = embedder if embedder is not None else Embedder()
        self.dense = {}
        self.dense_used = False
        if use_dense and self.embedder.available:
            self._init_dense()

        # VC (verification-criteria) band — a flat keyword/dense layer over wiki/VC,
        # surfaced as a small capped section (NOT part of the concept->entity graph).
        from wiki_retrieval.vc import VcIndex
        self.vcindex = VcIndex(self.wiki_root, use_dense=use_dense, embedder=self.embedder)

    def _init_dense(self):
        _manifest, stored = index_store.load_embeddings(self.wiki_root)
        for layer, stems in self._by_layer.items():
            if layer in stored:
                self.dense[layer] = stored[layer]            # (stems, matrix)
            else:
                mat = self.embedder.encode([self.docs[s].search_text() for s in stems])
                if mat is not None:
                    self.dense[layer] = (stems, mat)
        self.dense_used = bool(self.dense)

    def _layer_rank(self, layer: str, query: str) -> list:
        rankings = [self.bm25[layer].rank(query)]
        if layer in self.dense:
            stems, mat = self.dense[layer]
            d = self.embedder.cosine_rank(query, stems, mat)
            if d:
                rankings.append(d)
        return rrf(rankings)

    def retrieve(self, query: str, n_concept: int = 3, n_entity: int = 5,
                 top_n: int = 5, n_vc: int = 0) -> EssenceResult:
        concepts = self._layer_rank("concept", query)[:n_concept]

        expanded: list = []
        for cstem, _ in concepts:
            for e in self.graph.neighbors(cstem, types={"entity"}, hops=2):
                if e not in expanded:
                    expanded.append(e)

        entity_ranked = self._layer_rank("entity", query)
        entities: list = [s for s, _ in entity_ranked[:n_entity]]
        for s in expanded:
            if s not in entities:
                entities.append(s)

        # top-N overall = fuse concept + entity rankings into one list
        overall = rrf([
            [(s, sc) for s, sc in concepts],
            [(s, sc) for s, sc in entity_ranked],
        ])
        top = [s for s, _ in overall][:top_n]
        # ensure graph-expanded entities are representable even if low BM25
        for s in expanded:
            if s not in top and len(top) < top_n:
                top.append(s)

        hit_pages = {s for s, _ in concepts} | set(entities)
        conflicts = [c for c in self.conflicts if hit_pages & set(c.affected)]

        # VC is OFF by default (n_vc=0) — it is verification-purpose (often version-specific)
        # and conflicts with the TC flow at generation; opt in explicitly for a verify pass.
        vc = self.vcindex.rank(query, k=n_vc) if n_vc else []
        docs = dict(self.docs)
        for s, _ in vc:
            docs[s] = self.vcindex.docs[s]            # so essence can render VC hits

        return EssenceResult(
            query=query, concepts=concepts, entities=entities, expanded=expanded,
            conflicts=conflicts, top=top, docs=docs, dense_used=self.dense_used, vc=vc,
        )


@lru_cache(maxsize=8)
def _cached_retriever(wiki_root_str: str | None, use_dense: bool) -> Retriever:
    return Retriever(wiki_root=wiki_root_str, use_dense=use_dense)


def retrieve(query: str, wiki_root=None, use_dense: bool = True,
             n_concept: int = 3, n_entity: int = 5, top_n: int = 5,
             n_vc: int = 0) -> EssenceResult:
    """Convenience entry point with a cached Retriever per (wiki_root, use_dense)."""
    r = _cached_retriever(str(wiki_root) if wiki_root else None, use_dense)
    return r.retrieve(query, n_concept=n_concept, n_entity=n_entity, top_n=top_n, n_vc=n_vc)
