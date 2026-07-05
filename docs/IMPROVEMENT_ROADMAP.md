# Pipeline Improvement Roadmap (grounding & retrieval)

Re-assessed 2026-07-06 against VERIFIED facts (each checked in-repo, not assumed).
Agent-agnostic: any agent picking up one of these items starts here.

## Verified facts the ranking rests on

- (a) gitnexus already ships `cypher` (raw graph queries, LadybugDB/Cypher), `trace`
  (shortest call path) and the `gitnexus://repo/{name}/schema` resource. The MCP server is
  registered for this project. Infra cost of lever #5: zero.
- (b) `pattern_generator/stepwise.py` generation instructions mention NONE of
  `cypher`/`trace`/`wiki_retrieve` (0 grep hits) — the gap is purely prompt-side.
- (c) `python wiki_retrieve.py "<query>"` works as a standalone CLI and returns
  **essence-only** output (lead extracts; verified to contain zero code even when
  code-heavy pages are hit) — agentic wiki pull cannot wake the legacy code residue.
- (d) Constraint: a Hermes agent session mounts ONE MCP server — a second (wiki) MCP is
  not viable; agentic wiki access must be CLI-based.
- (e) `gate_logs/` holds history for only 2 TCs — too little data for frequency mining.
- (f) Retrieval quality is imperfect today: query "write booster flush" does NOT surface
  `entities/write-booster.md` in top-5; the dense layer is OFF unless
  `requirements-embed.txt` is installed (BM25-only fallback).

## Ranking

| # | Lever | Priority | Status |
|---|---|---|---|
| 5 | Teach `cypher`/`trace` in generation prompts | **NOW (merged with #1)** | infra done per (a); prompt patch pending |
| 1 | Agentic wiki pull via `wiki_retrieve.py` CLI | **NOW (merged with #5)** | safe per (c), Hermes-compatible per (d) |
| 2 | HippoRAG-style Personalized PageRank over the `[[wikilink]]` graph | second wave | value evidenced by (f); ~100–200 lines pure Python in `wiki_retrieval/` |
| 4 | Gate-log miner → auto-draft `review_refs/` rules (ACE-style promotion loop) | deferred | blocked by (e); start after 10+ TC runs |
| 3 | LSP layer (pyright/jedi references/hover) beside gitnexus | last | `cypher` caller-reverse-lookup covers most of the need; revisit only if it proves insufficient |

## Status update (2026-07-06, second pass)

The NOW patch below is IMPLEMENTED, plus a hardening the user's review demanded:
instruction-only cypher/trace is advisory — a non-Claude model (Hermes may mount one)
can ignore it and keep using only query/context. So caller evidence is now **FED
deterministically**: `api_grounding.build_call_sites()` (AST reverse index over Script,
`generated/` excluded to prevent self-poisoning) → `api_facts(call_sites=...)` emits
`real callers of X(): path:line, ...` (top-3, sample_code > pattern > rest) →
injected via `prepare._unit_api_facts` in BOTH grounding modes. cypher/trace in the
prompt is demoted to fallback for symbols the FEED didn't cover.
Deferred follow-up (B): a gate-audited disambiguation record (model must state which
caller it read when ≥2 siblings were injected) — start it when gate logs show a
wrong-API-chosen finding surviving this FEED.

## The NOW patch (one change, two levers)

Edit the grounding-instruction blocks in `pattern_generator/stepwise.py`
(`UNIT_GEN_INSTRUCTIONS` gitnexus variant; mirror what applies into the direct variant):

1. **#5-lite** — in IDIOM & SELECTION: when 2+ sibling symbols look plausible,
   disambiguate by reverse-looking-up REAL callers via `cypher`
   (template: `MATCH (c)-[:CodeRelation {type:'CALLS'}]->(f:Function {name:"<sym>"})
   RETURN c.name, c.filePath` — read `gitnexus://repo/GitNexusMCP/schema` first),
   and use `trace` for "how does A reach B" call chains.
2. **#1-lite** — WIKI section: keep the injected essence + `default.md` push as-is, but
   when a protocol question is NOT covered by the injected block, run
   `python wiki_retrieve.py "<query>"` (repo root) and record any page used in
   `=== WIKI REFS ===`. Never free-read wiki page bodies (essence only).

Acceptance: regenerate one unit of an existing TC; the emitted prompt contains both
instructions; a deliberate sibling-ambiguity case resolves via a cypher caller lookup.

## Rejected / not planned

- Full GraphRAG/LightRAG over the wiki: curated + already-structured corpus; LLM-side
  graph extraction is redundant cost (see arXiv 2506.05690).
- Embedding-only retrieval as primary: loses symbol/graph precision; the AST-derived
  approach is the validated one for codebases (arXiv 2601.08773).
- Fine-tuning a model on Script: API evolution would bake stale knowledge into weights;
  RAG + deterministic gates keep updates zero-cost.
