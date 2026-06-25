#!/usr/bin/env python3
"""Build the wiki retrieval indices (pipeline steps 2 + 3).

    python wiki_index.py build [--wiki wiki] [--no-dense]

Always writes wiki/.index/reference_graph.json. If a dense embedder is available
(sentence-transformers installed), also writes embeddings.npz + manifest.json.
BM25 + graph rebuild in-memory at query time, so this step is only strictly
required to enable the dense (semantic) ranker.
"""
import argparse
import sys

from wiki_retrieval.corpus import load_corpus
from wiki_retrieval.graph import build_graph, to_json
from wiki_retrieval.embedder import Embedder
from wiki_retrieval import index_store


def build(wiki_root=None, use_dense=True) -> None:
    docs = load_corpus(wiki_root, layer_dirs=("concepts", "entities"))
    graph = build_graph(docs)
    gpath = index_store.save_graph(to_json(graph), wiki_root)
    n_edges = sum(len(v) for v in graph.adj.values())
    print(f"reference graph: {len(docs)} nodes, {n_edges} edges -> {gpath}")

    if not use_dense:
        print("dense: skipped (--no-dense)")
        return

    embedder = Embedder()
    if not embedder.available:
        print("dense: embedder unavailable (sentence-transformers/numpy not installed) "
              "— retrieval will use BM25 + graph only")
        return

    by_layer = {"concept": [], "entity": []}
    for stem, d in docs.items():
        layer = d.layer if d.layer in by_layer else (
            "concept" if d.path.startswith("concepts/") else "entity")
        by_layer[layer].append(stem)
    stems_by_layer, mats = {}, {}
    for layer, stems in by_layer.items():
        stems_by_layer[layer] = stems
        mats[layer] = embedder.encode([docs[s].search_text() for s in stems])
    index_store.save_embeddings(stems_by_layer, mats, embedder.model_name, wiki_root)
    print(f"dense embeddings: model={embedder.model_name}, "
          f"{sum(len(s) for s in stems_by_layer.values())} docs -> {index_store.index_dir(wiki_root)}")


def main():
    ap = argparse.ArgumentParser(description="Build wiki retrieval indices (graph + dense)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build reference graph + (optional) dense embeddings")
    b.add_argument("--wiki", default=None, help="wiki root (default: ./wiki)")
    b.add_argument("--no-dense", action="store_true", help="skip dense embeddings")
    args = ap.parse_args()
    if args.cmd == "build":
        build(wiki_root=args.wiki, use_dense=not args.no_dense)


if __name__ == "__main__":
    sys.exit(main())
