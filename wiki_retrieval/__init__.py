"""Layered wiki retrieval: reference graph + BM25 + optional dense + RRF + essence.

Pure-Python core (corpus / graph / bm25 / retrieve / essence). The dense embedder
is optional and import-guarded; when its model libs are absent, retrieval degrades
to BM25 + reference-graph traversal with no loss of availability.
"""
from wiki_retrieval.retrieve import retrieve, Retriever
from wiki_retrieval.essence import build_essence

__all__ = ["retrieve", "Retriever", "build_essence"]
