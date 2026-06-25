"""Pure-Python BM25 (no external deps) — the always-available sparse ranker.

One index per layer (concepts, entities). Tokenisation is lowercase word/number
runs; the corpus per doc is title + tags + aliases + body (see WikiDoc.search_text).
"""
import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _stem(tok: str) -> str:
    """Cheap symmetric plural→singular fold (attributes→attribute, flags→flag).

    Applied to both corpus and query so the fold is consistent; over-folds like
    status→statu are harmless because they collapse identically on both sides.
    """
    if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text: str) -> list:
    return [_stem(t) for t in _TOKEN_RE.findall(text.lower())]


class BM25Index:
    """Okapi BM25 over a fixed list of (stem, text) docs."""

    def __init__(self, docs: list, k1: float = 1.5, b: float = 0.75):
        # docs: list of (stem, text)
        self.k1 = k1
        self.b = b
        self.stems = [s for s, _ in docs]
        self.tokens = [tokenize(t) for _, t in docs]
        self.doc_len = [len(toks) for toks in self.tokens]
        self.N = len(docs)
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tf = [Counter(toks) for toks in self.tokens]
        df: Counter = Counter()
        for toks in self.tokens:
            for term in set(toks):
                df[term] += 1
        self.df = df

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        if n == 0:
            return 0.0
        # BM25+ style non-negative idf
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def rank(self, query: str, top_k: int | None = None) -> list:
        """Return [(stem, score), ...] sorted by score desc (score>0 only)."""
        q_terms = tokenize(query)
        scores: list = []
        for i in range(self.N):
            tf = self.tf[i]
            if not any(t in tf for t in q_terms):
                continue
            dl = self.doc_len[i] or 1
            s = 0.0
            for term in q_terms:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                idf = self._idf(term)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (f * (self.k1 + 1)) / denom
            if s > 0:
                scores.append((self.stems[i], s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k] if top_k else scores

    def to_json(self) -> dict:
        return {
            "k1": self.k1, "b": self.b, "stems": self.stems,
            "doc_len": self.doc_len, "df": dict(self.df),
            "tf": [dict(c) for c in self.tf],
        }
