"""BM25 ranking over the Script symbol index.

Reuses the always-on pure-Python BM25 from `wiki_retrieval.bm25` (same ranker the
wiki side uses), so code grounding has no extra dependency and ranks consistently.
"""
from __future__ import annotations

from code_retrieval.index import SymbolDoc, build_symbol_index
from wiki_retrieval.bm25 import BM25Index


class CodeSearcher:
    """In-memory BM25 searcher over a Script symbol index."""

    def __init__(self, docs: list[SymbolDoc]):
        self.by_uid: dict[str, SymbolDoc] = {d.uid: d for d in docs}
        self._bm25 = BM25Index([(d.uid, d.search_text()) for d in docs])

    @classmethod
    def from_script_root(cls, script_root) -> "CodeSearcher":
        return cls(build_symbol_index(script_root))

    def search(self, query: str, k: int = 5) -> list[SymbolDoc]:
        ranked = self._bm25.rank(query, top_k=k)
        return [self.by_uid[uid] for uid, _score in ranked]
