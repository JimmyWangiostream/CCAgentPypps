"""Direct-Script code retrieval — the no-gitnexus code-grounding source.

Counterpart to `wiki_retrieval`: instead of asking the gitnexus MCP server for
candidate symbols at generation time, scan the `GitNexusMCP/Script` tree once
(AST, pure stdlib) and surface the top-N candidate symbols per unit query via
pure-Python BM25. The generating model then confirms exact signatures by reading
the real source files.
"""
from code_retrieval.index import SymbolDoc, build_symbol_index
from code_retrieval.retrieve import CodeRef, retrieve_code

__all__ = ["SymbolDoc", "build_symbol_index", "CodeRef", "retrieve_code"]
