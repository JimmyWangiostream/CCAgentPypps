"""Pluggable dense embedder (step 3) — optional, import-guarded.

Default model is a light multilingual sentence-transformer (handles the EN+ZH
mix in the wiki). If sentence-transformers / numpy are not installed, `available`
is False and retrieval silently falls back to BM25 + reference-graph traversal.
Nothing in the core path imports torch.
"""
from __future__ import annotations

DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"   # ~100MB; alt: "intfloat/multilingual-e5-small"


class Embedder:
    """Lazy wrapper around a sentence-transformers model.

    Construction never raises on missing deps; check `.available` before use.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._np = None
        self.available = False
        try:                                    # import guard — deps are optional
            import numpy as np
            from sentence_transformers import SentenceTransformer  # noqa: F401
            self._np = np
            self._SentenceTransformer = SentenceTransformer
            self.available = True
        except Exception:
            self.available = False

    def _ensure_model(self):
        if self._model is None:
            self._model = self._SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list):
        """Return an (N, dim) numpy array of L2-normalised embeddings, or None."""
        if not self.available or not texts:
            return None
        model = self._ensure_model()
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return self._np.asarray(vecs, dtype="float32")

    def cosine_rank(self, query: str, doc_stems: list, doc_matrix, top_k=None) -> list:
        """Rank doc_stems by cosine similarity to query. doc_matrix: (N, dim).

        Returns [(stem, score), ...] desc. Empty if dense is unavailable.
        """
        if not self.available or doc_matrix is None or not doc_stems:
            return []
        q = self.encode([query])
        if q is None:
            return []
        sims = (doc_matrix @ q[0])             # normalised → dot == cosine
        order = sims.argsort()[::-1]
        out = [(doc_stems[i], float(sims[i])) for i in order]
        return out[:top_k] if top_k else out
