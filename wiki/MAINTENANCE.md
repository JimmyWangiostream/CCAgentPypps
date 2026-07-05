# Wiki Maintenance Runbook (agent-agnostic)

How to maintain the LLM wiki **going forward**. Any agent (Hermes, Claude Code, other)
performing wiki work follows this file. The one-time Script-source retirement is DONE
(2026-07-02, commit `1e7e044`; prose finished in `237a151`) — no further retirements are
expected; this runbook covers the steady state.

## Invariants (never violate)

1. **The wiki does not carry code.** No code trees, no code snippets, no
   "call `api.X(...)`" examples in NEW pages. Code knowledge is grounded exclusively via
   the **gitnexus index** over `GitNexusMCP/Script/` (`query`/`context`/`cypher`,
   always `repo="GitNexusMCP"`). Enforced: `wiki_lint.py` errors on a code tree under
   `wiki/`. Rationale: wiki-held code drifts against the real Script tree — the
   "confidently wrong" class that passes every gate.
   - Legacy code refs inside old entity/concept pages (18 pages, from the 2026-06-21
     ingest) are grandfathered and DORMANT: `essence.py` extracts lead sentences only, so
     page-body code never reaches unit prompts. Do not add more. If the wiki ever gets
     full-page agentic access, cleaning these becomes a prerequisite.
2. **One authority per fact.** Wiki owns SPEC (what/why: opcode tables, payload layouts,
   protocol behavior, customer constraints). gitnexus owns CODE (how: signatures, callers,
   idioms). A spec-vs-code contradiction is a SIGNAL (one side is wrong about hardware —
   surface it, never silently align); a duplicated-code contradiction is NOISE (that's why
   invariant 1 exists).
3. **Sources are raw and immutable.** Never edit files under `Spec/ CustomerReq/
   UserPrompt/ ProNoun/ ModelDefault/ VC/` — new knowledge = new file + re-ingest.

## Where does a new document go? (decision table)

Classify by CONTENT NATURE, not by who sent it (one customer doc often splits into rows):

| Content | Destination | Reaches prompts via |
|---|---|---|
| Behavioral constraint ("LUN must be 0–7 else invalid INDEX") | `wiki/CustomerReq/` + run `build-defaults` | `default.md` — ALWAYS injected |
| Definition / knowledge (VU command spec, payload layout, feature behavior) | `wiki/CustomerReq/` (raw) → Ingest → `wiki/entities/` or `concepts/` page | retrieval (RRF top-N essence) |
| Multi-step procedure with NO single API, or doc-without-code bootstrap recipe | `pattern_generator/procedure_idioms.py` registry entry | deterministic trigger-token injection |
| Review lesson (recurring generation mistake) | `pattern_generator/review_refs/*.md` | BM25-selected at review/finish |

TCs stay WHAT-only — never write implementation knowledge into `TC/*.md`.

## The Ingest operation (LLM-performed; no automation exists)

When a new source document arrives:

1. Drop the raw file under the matching source dir (usually `wiki/CustomerReq/`).
2. Synthesize the knowledge page(s) under `wiki/entities/` (concrete things: commands,
   descriptors, attributes) or `wiki/concepts/` (mechanisms, test methodologies).
   Frontmatter requirements:
   - `type: entity|concept`, `title:`, `tags:`, `created:`/`updated:`
   - `sources: [customerreq]` (provenance)
   - `aliases:` — include every name the page might be queried by (opcode `0xB1`, command
     name, struct name). Aliases get **3× BM25/dense weight** (`wiki_retrieval/corpus.py`),
     so this is the main retrieval lever.
   - `[[wikilinks]]` to existing related pages (dangling links = lint warning).
   - **Spec content only** (invariant 1): parameter tables, byte offsets, expected values,
     authority notes. If code for it does not exist yet, say so in ONE line and register
     the compose recipe in `procedure_idioms.py` — NOT in the page.
3. Backlink: add the new page to `wiki/sources/<source>.md` frontmatter (`entities:`/`concepts:`).
4. Conflict check: if the doc contradicts Spec (Rule 1) or ModelDefault (Rule 2), record
   the resolution in `wiki/conflicts.md` (quote the raw source text).
5. If any row of the doc was a CONSTRAINT: `python generate_pattern.py build-defaults`.
6. Rebuild retrieval index: `python wiki_index.py build`.
7. Health check: `python wiki_lint.py` (must exit 0).

## Verification (after every ingest)

- `python wiki_retrieve.py "<expected query>"` — the new page must appear in top-5
  (if not: enrich `aliases:`/`tags:`, rebuild index, retry).
- `python wiki_lint.py` exit 0.
- For constraints: check the resolved line appears in `wiki/default.md`.

## Promotion (when code for a documented capability lands later)

1. Implement in `GitNexusMCP/Script/` (helper + struct, next to its siblings).
2. Reindex gitnexus **from `GitNexusMCP/`**: `node .gitnexus/run.cjs analyze --embeddings --skip-git`.
3. DELETE the bootstrap entry from `procedure_idioms.py` (its mission is over; a stale
   recipe is drift risk).
4. The wiki page keeps its spec table (it is the arbitration source if the code is ever
   suspected wrong — a real case: `micron_vu_40B1.l16_die` reads byte[16..17] while the
   customer spec says byte[16..19]). Do NOT add the new helper's code/usage to the page.
