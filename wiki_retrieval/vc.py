"""VC (Verification Criteria) corpus — the per-pattern test specs under wiki/VC/.

Each VC doc is `# Test Spec` + `## Verification Criterion (VC)` + `## Test Case Checkpoints`
(actions + expected results, rich in real API idioms). They have NO frontmatter and are keyed
to the real PSW_F_P3_* patterns, so they don't fit the concept/entity `type:` model — this
module loads them as a flat `layer="vc"` corpus with its own BM25 (+ optional dense) ranker.

Reused by BOTH consumers: generation-time retrieval (wiki_retrieval.retrieve surfaces a small
VC band in the essence) and review-time injection (pattern_generator.review adds the matched
VC checkpoints). Keeping it here keeps prevent + review on one source of truth.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from wiki_retrieval.corpus import DEFAULT_WIKI, load_doc
from wiki_retrieval.bm25 import BM25Index
from wiki_retrieval.embedder import Embedder
from wiki_retrieval import index_store

VC_DIR = "VC"


def load_vc(wiki_root=None) -> dict:
    """Load wiki/VC/*.md as {stem: WikiDoc} with layer forced to 'vc' (no frontmatter)."""
    root = (Path(wiki_root) if wiki_root else DEFAULT_WIKI) / VC_DIR
    docs: dict = {}
    if not root.is_dir():
        return docs
    for md in sorted(root.glob("*.md")):
        doc = load_doc(md, VC_DIR)      # title falls back to the `# H1`; body = full text
        doc.layer = "vc"
        docs[doc.stem] = doc
    return docs


def _fuse(rankings: list, k: int = 60) -> list:
    """Reciprocal Rank Fusion (local copy to avoid importing retrieve -> no import cycle)."""
    fused: dict = defaultdict(float)
    for ranking in rankings:
        for rank, (stem, _score) in enumerate(ranking, start=1):
            fused[stem] += 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


class VcIndex:
    """BM25 (+ optional dense) ranker over the VC corpus."""

    def __init__(self, wiki_root=None, use_dense: bool = True, embedder: Embedder | None = None):
        self.docs = load_vc(wiki_root)
        stems = list(self.docs)
        self.bm25 = BM25Index([(s, self.docs[s].search_text()) for s in stems])
        self.embedder = embedder if embedder is not None else Embedder()
        self.dense = None
        if use_dense and self.embedder.available and stems:
            # Prefer prebuilt embeddings (wiki_index build saves the 'vc' layer); only
            # live-encode as a cold fallback (361 docs — avoid doing this per run when possible).
            _m, stored = index_store.load_embeddings(wiki_root)
            if "vc" in stored:
                self.dense = stored["vc"]
            else:
                mat = self.embedder.encode([self.docs[s].search_text() for s in stems])
                if mat is not None:
                    self.dense = (stems, mat)

    def rank(self, query: str, k: int = 3) -> list:
        """Top-k VC stems for the query as [(stem, score), …].

        Gated on a BM25 keyword hit: an unrelated query (no keyword overlap) returns []
        so VC never surfaces as noise. Dense, when available, only re-orders the hits."""
        bm = self.bm25.rank(query)
        if not bm:
            return []
        rankings = [bm]
        if self.dense:
            stems, mat = self.dense
            d = self.embedder.cosine_rank(query, stems, mat)
            if d:
                bm_set = {s for s, _ in bm}
                rankings.append([(s, sc) for s, sc in d if s in bm_set])
        return _fuse(rankings)[:k]


@lru_cache(maxsize=8)
def _cached_index(wiki_root_str: str | None, use_dense: bool) -> VcIndex:
    return VcIndex(wiki_root=wiki_root_str, use_dense=use_dense)


def get_index(wiki_root=None, use_dense: bool = True) -> VcIndex:
    return _cached_index(str(wiki_root) if wiki_root else None, use_dense)


def select_vc(query: str, pattern_id: str = "", cap: int = 3, wiki_root=None,
              use_dense: bool = True) -> list:
    """Top VC docs for `query` as [WikiDoc, …] (possibly empty).

    If a VC stem matches `pattern_id` (the exact spec for this pattern), it is prioritized
    first regardless of keyword score."""
    idx = get_index(wiki_root, use_dense)
    ranked = [idx.docs[s] for s, _ in idx.rank(query, k=cap)]
    pid = (pattern_id or "").strip().lower()
    if pid:
        exact = next((d for s, d in idx.docs.items() if s.lower() == pid), None)
        if exact and exact not in ranked:
            ranked = [exact] + ranked
        elif exact:
            ranked = [exact] + [d for d in ranked if d is not exact]
    return ranked[:cap]
