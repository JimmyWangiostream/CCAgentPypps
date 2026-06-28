"""Prescriptive review knowledge = the markdown docs in `review_refs/`.

Adding a review rule = dropping a `.md` into `review_refs/` (NO code change). This
replaced a hand-coded `Rule` list that didn't scale (every new pitfall needed code).
Selection is content/keyword based (BM25, capped) so the folder can grow to hundreds
of docs while any single review prompt only carries the few relevant ones — review
is a single prompt, so a cap of ~6 small docs is cheap. (See plan Stage 12.)

This is the SEMANTIC layer (protocol/logic/discipline). The DETERMINISTIC API-detail
layer (param names, enum members, signatures) stays in api_grounding — the two are
complementary; an LLM review guesses API details, the AST index never does.
"""
from __future__ import annotations

from pathlib import Path

from wiki_retrieval.bm25 import BM25Index

REFS_DIR = Path(__file__).resolve().parent / "review_refs"


def _load() -> list:
    if not REFS_DIR.is_dir():
        return []
    return [(p.stem, p.read_text(encoding="utf-8", errors="ignore"))
            for p in sorted(REFS_DIR.glob("*.md"))]


def select_refs(text: str, extra_terms: tuple = (), cap: int = 6) -> list:
    """The <=cap most relevant review-reference docs for `text` (+ extra IR terms).

    BM25 over (filename + content); only docs that actually score a keyword hit are
    returned, so a simple step gets 2-3 and a feature-rich pattern gets ~6, never all."""
    docs = _load()
    if not docs:
        return []
    by = dict(docs)
    bm = BM25Index([(stem, f"{stem.replace('-', ' ')} {body}") for stem, body in docs])
    query = (text or "") + " " + " ".join(extra_terms)
    return [(stem, by[stem]) for stem, _ in bm.rank(query, top_k=cap)]


def format_refs(refs: list) -> str:
    """Render selected reference docs for prompt injection."""
    if not refs:
        return "(no matching review references)"
    return "\n\n".join(f"### {stem}\n{body.strip()}" for stem, body in refs)


def all_ref_names() -> list:
    return [stem for stem, _ in _load()]
