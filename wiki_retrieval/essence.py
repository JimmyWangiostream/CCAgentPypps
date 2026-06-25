"""Step 5 — deterministic extractive essence.

Assembles retrieved docs into a compact "concept -> entity -> reference -> conflict
override" index. No LLM: principles/details are pulled extractively from each file.
"""
import re

_SKIP = ("#", "|", "---", "```", ">")


def _lead(body: str, limit: int = 220) -> str:
    """First meaningful prose line (skips headings, tables, rules, code fences)."""
    for ln in body.split("\n"):
        s = ln.strip()
        if not s or s.startswith(_SKIP):
            continue
        s = re.sub(r"\s+", " ", s)
        return s[:limit]
    return ""


def format_top_refs(result) -> list:
    """The wiki top-N as provenance lines: 'concepts/psa.md (rank1)'."""
    out = []
    for i, stem in enumerate(result.top, start=1):
        doc = result.docs.get(stem)
        path = doc.path if doc else stem
        out.append(f"{path} (rank{i})")
    return out


def _ref_source(result, entity_stem: str) -> str:
    """Which retrieved concept references this entity (for the expansion line)."""
    for cstem, _ in result.concepts:
        doc = result.docs.get(cstem)
        if doc and entity_stem in doc.refs:
            cpath = doc.path
            return cpath
    return ""


def build_essence(result, max_concepts: int = 3, max_entities: int = 5,
                  max_expanded: int = 4) -> str:
    """Render the extractive essence block (capped to stay concise, not noisy)."""
    if not result.has_match:
        return f"## Wiki essence — query: {result.query}\n(NO MATCH — no relevant wiki page)"

    lines = [f"## Wiki essence — query: {result.query}"]

    if result.concepts:
        lines.append("principles (concepts):")
        for stem, _ in result.concepts[:max_concepts]:
            doc = result.docs.get(stem)
            if doc:
                lines.append(f"- {doc.title}: {_lead(doc.body)} ({doc.path})")

    if result.entities:
        lines.append("entities:")
        for stem in result.entities[:max_entities]:
            doc = result.docs.get(stem)
            if doc:
                lines.append(f"- {doc.title}: {_lead(doc.body)} ({doc.path})")

    expanded_shown = [s for s in result.expanded if s in set(result.entities[:max_entities])]
    if expanded_shown:
        lines.append("reference expansion:")
        for stem in expanded_shown[:max_expanded]:
            doc = result.docs.get(stem)
            if not doc:
                continue
            src = _ref_source(result, stem)
            via = f"  ← referenced by {src}" if src else ""
            lines.append(f"- {doc.path}{via}")

    if result.conflicts:
        lines.append("authority overrides (conflicts win):")
        for c in result.conflicts:
            affected = ", ".join(f"[[{a}]]" for a in c.affected)
            lines.append(f"- [{c.rule}] {c.title} → affects {affected}")

    return "\n".join(lines)
