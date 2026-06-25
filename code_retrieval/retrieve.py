"""Public retrieval entry: top-N candidate Script symbols for a query.

`retrieve_code(query, script_root, k)` returns ranked `CodeRef`s suitable for
prompt injection and for the `=== CODE REFS ===` log. The searcher is built once
per `script_root` and cached (the index over ~440 files is cheap but not free).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from code_retrieval.index import SymbolDoc
from code_retrieval.search import CodeSearcher

_SEARCHER_CACHE: dict[str, CodeSearcher] = {}


@dataclass
class CodeRef:
    doc: SymbolDoc
    rank: int

    def render(self) -> str:
        return self.doc.render(rank=self.rank)


def _get_searcher(script_root) -> CodeSearcher:
    key = str(Path(script_root).resolve())
    if key not in _SEARCHER_CACHE:
        _SEARCHER_CACHE[key] = CodeSearcher.from_script_root(script_root)
    return _SEARCHER_CACHE[key]


def retrieve_code(query: str, script_root, k: int = 5) -> list[CodeRef]:
    """Top-k candidate Script symbols for `query` (empty list if no query/match)."""
    if not query or not query.strip():
        return []
    docs = _get_searcher(script_root).search(query, k=k)
    return [CodeRef(doc=d, rank=i + 1) for i, d in enumerate(docs)]
