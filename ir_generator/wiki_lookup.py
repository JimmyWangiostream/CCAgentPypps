"""IR-stage wiki lookup. Uses the layered retriever (reference graph + BM25 +
optional dense + RRF) over the INGESTED llm-wiki (conflict-resolved
entities/concepts + conflicts.md) — NOT the raw Spec catalog. This ensures the IR
enrichment step sees CustomerReq>Spec / UserPrompt>ModelDefault overrides.

Output contract (unchanged): dict[phase_id -> [{title, file, excerpt}]] plus a
global "__conflicts__" entry carrying the conflict-resolved overrides.
"""
import re
from pathlib import Path

from ir_generator.config import Config
from wiki_retrieval.retrieve import retrieve

EXCERPT_CHARS = 1200
MAX_REFS_PER_PHASE = 12


def _step_terms(step: dict) -> list[str]:
    """Query terms from a single step's SCSI/UFS command + IDN entity name."""
    terms = []
    for field in ("scsi_cmd", "ufs_query"):
        val = step.get(field)
        if val:
            terms.extend(w for w in re.sub(r'[()（）]', ' ', val).lower().split()
                         if len(w) > 2)
    idn = step.get("idn") or ""
    if idn:
        terms.extend(w for w in re.sub(r'[()（）]', ' ', idn).lower().split()
                     if len(w) > 2)
    return terms


def extract_commands(phase: dict) -> list[str]:
    """Terms from a phase's SCSI/UFS commands + IDN entity names (e.g. bBootLunEn)."""
    terms = []
    for step in phase.get("steps", []):
        terms.extend(_step_terms(step))
    return list(set(terms))


def load_conflicts(wiki_path: Path) -> dict | None:
    p = Path(wiki_path) / "conflicts.md"
    if not p.exists():
        return None
    return {
        "title": "Conflict-Resolved Overrides (CustomerReq>Spec, UserPrompt>ModelDefault)",
        "file": "conflicts.md",
        "excerpt": p.read_text(encoding="utf-8", errors="ignore")[:EXCERPT_CHARS],
    }


def lookup_wiki(skeleton: dict, config: Config) -> dict[str, list[dict]]:
    """Per-phase ingested-wiki refs via layered retrieval. Each step retrieves its
    own top hits and the phase unions them (so a step's strongest page is never
    diluted by sibling steps). Always includes a global '__conflicts__' entry
    carrying the conflict-resolved overrides (highest authority)."""
    refs: dict[str, list[dict]] = {}
    for phase in skeleton.get("phases", []):
        pid = phase["phase_id"]
        # Per step take its top concepts + top entities (entities = concrete
        # grounding pages, always represented), then round-robin merge so every
        # step's strongest pages survive the cap.
        per_step: list[list] = []
        docs_by_stem: dict = {}
        for step in phase.get("steps", []):
            query = " ".join(_step_terms(step))
            if not query.strip():
                continue
            result = retrieve(query, wiki_root=config.wiki_path)
            hits = [s for s, _ in result.concepts[:2]] + result.entities[:2]
            per_step.append(hits)
            docs_by_stem.update(result.docs)

        seen: set = set()
        merged: list[dict] = []
        for col in range(4):
            for hits in per_step:
                if col >= len(hits):
                    continue
                doc = docs_by_stem.get(hits[col])
                if not doc or doc.path in seen:
                    continue
                seen.add(doc.path)
                merged.append({"title": doc.title, "file": doc.path,
                               "excerpt": doc.body[:EXCERPT_CHARS]})
        refs[pid] = merged[:MAX_REFS_PER_PHASE]

    conflicts = load_conflicts(config.wiki_path)
    if conflicts:
        refs["__conflicts__"] = [conflicts]
    return refs
