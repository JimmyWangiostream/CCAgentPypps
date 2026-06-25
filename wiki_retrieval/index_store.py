"""Persist/load the prebuilt wiki indices under wiki/.index/.

reference_graph.json and bm25 are cheap to rebuild in-memory, so persistence is
mainly for the dense embeddings (which need the model at build time). Retrieval
works with no stored index at all: graph + BM25 rebuild from the corpus, and
dense is simply disabled when embeddings.npz is absent.
"""
import json
from pathlib import Path

from wiki_retrieval.corpus import DEFAULT_WIKI


def index_dir(wiki_root=None) -> Path:
    return (Path(wiki_root) if wiki_root else DEFAULT_WIKI) / ".index"


def save_graph(graph_json: dict, wiki_root=None) -> Path:
    d = index_dir(wiki_root)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "reference_graph.json"
    p.write_text(json.dumps(graph_json, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def save_embeddings(stems_by_layer: dict, matrices_by_layer: dict, model_name: str,
                    wiki_root=None):
    """Save dense embeddings. matrices_by_layer: {layer: numpy (N,dim)}.

    Requires numpy (only reached on the dense path). Writes embeddings.npz +
    a manifest recording the model + per-layer stem order.
    """
    import numpy as np
    d = index_dir(wiki_root)
    d.mkdir(parents=True, exist_ok=True)
    arrays = {f"{layer}__vecs": mat for layer, mat in matrices_by_layer.items() if mat is not None}
    np.savez(d / "embeddings.npz", **arrays)
    manifest = {
        "model": model_name,
        "layers": {layer: stems for layer, stems in stems_by_layer.items()},
    }
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                     encoding="utf-8")


def load_embeddings(wiki_root=None):
    """Return (manifest, {layer: (stems, matrix)}) or (None, {}) if absent/unloadable."""
    d = index_dir(wiki_root)
    man_p, emb_p = d / "manifest.json", d / "embeddings.npz"
    if not (man_p.is_file() and emb_p.is_file()):
        return None, {}
    try:
        import numpy as np
    except Exception:
        return None, {}
    manifest = json.loads(man_p.read_text(encoding="utf-8"))
    npz = np.load(emb_p)
    out = {}
    for layer, stems in manifest.get("layers", {}).items():
        key = f"{layer}__vecs"
        if key in npz:
            out[layer] = (stems, npz[key])
    return manifest, out
