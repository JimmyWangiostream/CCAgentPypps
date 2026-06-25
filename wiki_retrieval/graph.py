"""Reference graph over the wiki (step 2).

Nodes are docs (keyed by stem); a directed edge A -> B means A's body contains a
`[[B]]` wikilink. `[[target]]` is resolved to a real doc by stem, else by alias.
Used to expand a concept hit into its referenced entity pages.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RefGraph:
    nodes: dict                                 # stem -> WikiDoc
    adj: dict = field(default_factory=dict)     # stem -> [stem, ...] (outgoing)
    radj: dict = field(default_factory=dict)    # stem -> [stem, ...] (incoming)

    def neighbors(self, stem: str, types=None, hops: int = 1) -> list:
        """Outgoing-reachable stems within `hops`, optionally filtered by layer.

        Returns stems in BFS order, excluding the start node. `types` is a set of
        layer names (e.g. {"entity"}) to keep; None keeps all.
        """
        seen = {stem}
        frontier = [stem]
        out: list = []
        for _ in range(max(0, hops)):
            nxt = []
            for s in frontier:
                for t in self.adj.get(s, []):
                    if t in seen:
                        continue
                    seen.add(t)
                    nxt.append(t)
                    node = self.nodes.get(t)
                    if types is None or (node and node.layer in types):
                        out.append(t)
            frontier = nxt
            if not frontier:
                break
        return out


def _alias_index(docs: dict) -> dict:
    """Map lowercased stem/alias/title-slug -> stem, for resolving [[wikilinks]]."""
    idx: dict = {}
    for stem, doc in docs.items():
        idx.setdefault(stem.lower(), stem)
        for a in doc.aliases:
            idx.setdefault(a.lower(), stem)
            idx.setdefault(a.lower().replace(" ", "-"), stem)
    return idx


def build_graph(docs: dict) -> RefGraph:
    """Build the reference graph from each doc's wikilink refs."""
    alias = _alias_index(docs)
    adj: dict = {s: [] for s in docs}
    radj: dict = {s: [] for s in docs}
    for stem, doc in docs.items():
        for target in doc.refs:
            tstem = target if target in docs else alias.get(target.lower())
            if not tstem or tstem == stem:
                continue
            if tstem not in adj[stem]:
                adj[stem].append(tstem)
                radj.setdefault(tstem, []).append(stem)
    return RefGraph(nodes=docs, adj=adj, radj=radj)


def to_json(graph: RefGraph) -> dict:
    """Serialise the reference graph to a nodes/edges dict."""
    nodes = [
        {"id": s, "type": d.layer, "title": d.title, "path": d.path,
         "tags": d.tags, "aliases": d.aliases, "sources": d.sources}
        for s, d in graph.nodes.items()
    ]
    edges = [{"source": s, "target": t, "type": "reference"}
             for s, targets in graph.adj.items() for t in targets]
    return {"nodes": nodes, "edges": edges}
