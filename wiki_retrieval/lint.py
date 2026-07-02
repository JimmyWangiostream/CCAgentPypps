"""Wiki lint -- a deterministic health check over the layered wiki (SCHEMA.md's third
operation: "Lint -- Health check for structure and semantic issues").

The wiki is injected into every generation prompt, so mechanical rot silently degrades
what the model sees: a dangling `[[wikilink]]` is dropped by the reference graph (the
concept→entity expansion misses it), a page missing `type:` isn't routed by the layered
retriever, a stale `default.md` injects outdated always-on policy, and an unused code/source
tree under wiki/ bloats the repo and muddies provenance.

This is the STRUCTURAL layer (deterministic, reuses corpus.py + graph.py). Factual/semantic
correctness of page CONTENT is a separate, heavier LLM pass (not done here).
"""
from __future__ import annotations

from pathlib import Path

from wiki_retrieval.corpus import (
    DEFAULT_WIKI, load_corpus, parse_conflicts, extract_wikilinks,
)
from wiki_retrieval.graph import build_graph, _alias_index

# Dirs the pipeline actually consumes (everything else under wiki/ is unused by tooling).
_RETRIEVAL_ORDER = ("concepts", "entities", "sources")         # deterministic load order
_RETRIEVAL_DIRS = set(_RETRIEVAL_ORDER)                         # membership checks
_POLICY_DIRS = {"UserPrompt", "ModelDefault", "CustomerReq", "ProNoun"}  # build-defaults / conflicts
# VC = verification-criteria corpus, consumed by wiki_retrieval.vc (retrieval + review).
_KNOWN_DIRS = _RETRIEVAL_DIRS | _POLICY_DIRS | {"VC", ".index"}
_VALID_TYPES = {"concept", "entity", "source"}
_STUB_BODY_CHARS = 200
_LARGE_DIR_FILES = 20          # a wiki/<dir> with more files than this counts as "large"

# default.md is rebuilt from these; if it predates any of them it is stale.
_DEFAULT_SOURCES = ("UserPrompt", "ModelDefault", "conflicts.md")


def _finding(level: str, kind: str, page: str, detail: str) -> dict:
    return {"level": level, "kind": kind, "page": page, "detail": detail}


def lint_wiki(wiki_root=None) -> list:
    """Return a list of structural findings for the wiki (possibly empty).

    Each finding: {level: 'error'|'warn', kind, page, detail}."""
    root = Path(wiki_root) if wiki_root else DEFAULT_WIKI
    findings: list = []
    if not root.is_dir():
        return [_finding("error", "missing_wiki", str(root), "wiki root does not exist")]

    docs = load_corpus(root, layer_dirs=_RETRIEVAL_ORDER)
    alias = _alias_index(docs)
    graph = build_graph(docs)
    # A [[link]] may also target a top-level wiki file (conflicts/default/index/...),
    # not only a layered concept/entity/source doc.
    toplevel = {p.stem.lower() for p in root.glob("*.md")}

    # Per-doc structural checks.
    for stem, doc in docs.items():
        # dangling wikilinks -- same resolution build_graph uses (stem then alias),
        # plus top-level wiki files. A link to a page that was never created degrades
        # the reference-graph expansion but does NOT feed wrong info — it's a wiki GAP
        # (an enrichment TODO), so it is a WARN, not an ERROR.
        dangling = [t for t in doc.refs
                    if t not in docs and alias.get(t.lower()) is None
                    and t.lower() not in toplevel]
        if dangling:
            findings.append(_finding(
                "warn", "dangling_wikilink", doc.path,
                f"[[{']], [['.join(dangling)}]] -- page(s) not created yet (wiki gap)"))
        # type/frontmatter routing
        if not doc.layer:
            findings.append(_finding("error", "missing_type", doc.path,
                                     "no `type:` frontmatter -- not routed by the retriever"))
        elif doc.layer not in _VALID_TYPES:
            findings.append(_finding(
                "error", "bad_type", doc.path,
                f"type='{doc.layer}' not in {sorted(_VALID_TYPES)}"))
        # title fallback
        if not doc.title or doc.title == stem:
            findings.append(_finding("warn", "missing_title", doc.path,
                                     "no `title:` and no `# H1` -- title fell back to the stem"))
        # orphan (no in- and no out-edges) -- only BM25-reachable, never graph-expanded
        if not graph.adj.get(stem) and not graph.radj.get(stem):
            findings.append(_finding("warn", "orphan_page", doc.path,
                                     "no in/out [[links]] -- unreachable via reference-graph expansion"))
        # stub
        if len((doc.body or "").strip()) < _STUB_BODY_CHARS:
            findings.append(_finding("warn", "stub_page", doc.path,
                                     f"body under {_STUB_BODY_CHARS} chars (low-information page)"))

    # duplicate stems across layers (load_corpus keys by stem, so a dup is silently shadowed)
    seen: dict = {}
    for layer_dir in _RETRIEVAL_ORDER:
        d = root / layer_dir
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            seen.setdefault(md.stem, []).append(f"{layer_dir}/{md.name}")
    for stem, paths in seen.items():
        if len(paths) > 1:
            findings.append(_finding("warn", "duplicate_stem", ", ".join(paths),
                                     f"stem '{stem}' appears in multiple layers (ambiguous resolution)"))

    # conflicts.md affected pages that no longer exist
    for c in parse_conflicts(root):
        missing = [a for a in c.affected if a not in docs and alias.get(a.lower()) is None
                   and a.lower() not in toplevel]
        if missing:
            findings.append(_finding(
                "warn", "stale_conflict", "conflicts.md",
                f"conflict '{c.title}' lists missing page(s): {', '.join(missing)}"))

    findings.extend(_lint_default_staleness(root))
    findings.extend(_lint_unused_trees(root))
    return findings


def _lint_default_staleness(root: Path) -> list:
    """default.md is ALWAYS injected; flag it if it predates its source inputs."""
    dflt = root / "default.md"
    if not dflt.is_file():
        return [_finding("warn", "default_missing", "default.md",
                         "default.md absent -- run `generate_pattern.py build-defaults`")]
    dflt_mtime = dflt.stat().st_mtime
    newer: list = []
    for src in _DEFAULT_SOURCES:
        p = root / src
        if not p.exists():
            continue
        mtime = (max((f.stat().st_mtime for f in p.rglob("*") if f.is_file()), default=0)
                 if p.is_dir() else p.stat().st_mtime)
        if mtime > dflt_mtime:
            newer.append(src)
    if newer:
        return [_finding("warn", "default_stale", "default.md",
                         f"older than {', '.join(newer)} -- re-run `build-defaults`")]
    return []


def _lint_unused_trees(root: Path) -> list:
    """Flag wiki/<dir> trees the pipeline never reads (bloat / portability / provenance
    confusion). A code tree (.py present) is an ERROR so it can't creep back in."""
    out: list = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in _KNOWN_DIRS or d.name.startswith("."):
            continue
        files = [f for f in d.rglob("*") if f.is_file()]
        has_py = any(f.suffix == ".py" for f in files)
        if has_py:
            out.append(_finding(
                "error", "unused_code_tree", f"{d.name}/",
                f"code tree ({sum(f.suffix == '.py' for f in files)} .py) under wiki/ -- NOT read "
                "by retrieval; code grounding is gitnexus/Script. Remove for portability."))
        elif len(files) > _LARGE_DIR_FILES:
            out.append(_finding(
                "warn", "unused_source_tree", f"{d.name}/",
                f"{len(files)} files under wiki/ -- NOT consumed by retrieval/build-defaults "
                "(raw ingest source). Consider removing for portability."))
    return out


def format_findings(findings: list) -> list:
    """Render findings as `[level] kind -- page: detail` lines."""
    return [f"[{f['level']}] {f['kind']} -- {f['page']}: {f['detail']}" for f in findings]


def summary(findings: list) -> dict:
    errors = sum(1 for f in findings if f["level"] == "error")
    return {"total": len(findings), "errors": errors,
            "warnings": len(findings) - errors}
