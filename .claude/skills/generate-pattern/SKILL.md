---
name: generate-pattern
description: "Use to convert a UFS TC normalized-test-flow markdown (TC/*.md) into an executable Python test pattern via this repo's deterministic CLI pipeline. Examples: \"generate a pattern for TC/PF010_0310-...md\", \"turn this test flow into a pattern\", \"run the IR + pattern pipeline\". This is the canonical entry point for ANY agent (Claude Code or other)."
---

# Generate Pattern (TC → Pattern pipeline)

Convert a UFS test-case flow (`TC/<id>-normalized-test-flow.md`) into an executable Python
pattern. Deterministic Python CLI does the structure; the LLM (you) only fills the
self-contained prompt files the CLI writes. **No external LLM API keys.**

> Full detail lives in [`AGENTS.md`](../../../AGENTS.md) (agent runbook) and
> [`CLAUDE.md`](../../../CLAUDE.md) (command syntax + Step rules + section formats).
> Read both before starting — this skill is the index, those are the manual.

## When to use
A user wants a pattern generated/regenerated from a `TC/*.md` flow, or asks to run the
IR / pattern pipeline. For questions about gitnexus itself, use the gitnexus skills under
`GitNexusMCP/.claude/skills/` instead.

## The flow (run in order; LLM steps read the emitted `.txt` and write the named file)
```
1. python generate_pattern.py prepare-ir TC/<file>.md
2. read <run>/enrich_prompt.txt        -> write <run>/annotations.json        (Step A)
3. python generate_pattern.py finalize-ir <run>/ir_skeleton.json <run>/annotations.json
4. python generate_pattern.py prepare <run>/<id>-ir.json [--grounding direct]
5. for k=1..N:
     python generate_pattern.py prepare-unit <run> k
     read <run>/unit_kk_*_prompt.txt   -> write unit_kk_*_methods.py           (Step B)
       (loop-wrapper units report "skip" — they are auto-written; do NOT hand-write)
     python generate_pattern.py validate-unit <run> k        # per-unit gate
       FAIL (exit 1) -> fix every finding, rewrite unit_kk_*_methods.py, re-run; THEN k+1
6. python generate_pattern.py assemble <run> <PatternName>
7. python generate_pattern.py finish <gen>/<PatternName>.py <run>/<id>-ir.json
     GATE FAIL -> read <id>_repair_prompt.txt, rewrite the WHOLE .py, re-run finish
     GATE PASS -> read <id>_review_prompt.txt, do one rule-level review pass
```
`<run>` = the per-pattern run dir printed by `prepare-ir` (under `PGConfig.generated_dir`);
`<gen>` = its parent (the generated base). An alternative to steps 4–6 is
`prepare-wholefile` (one whole-file authoring prompt) then `finish`.

## Non-negotiable rules (the common failure modes)
- **Ground every API call.** With gitnexus MCP: `query`+`context` (pass `repo="GitNexusMCP"`).
  Without it: `prepare --grounding direct` and confirm signatures by reading
  `GitNexusMCP/Script` source. Never invent a symbol/enum/param — record real refs in
  `=== CODE REFS ===` (a fabricated citation is flagged by the citation audit).
- **Project defaults are auto-injected.** When the TC omits a detail (e.g. which LUN), follow
  `wiki/default.md` — do NOT hardcode `lun=0`; use the MaxCapacity-Enabled-LUN rule and tag
  `# src[wiki]: default.md`.
- **The gate is the source of truth.** `validate`/`finish` report
  `syntax · structure · dataflow · api_grounding · semantic · mypy`. Fix EVERY finding; the
  per-unit gate (`validate-unit`) catches the same issues earlier, at the unit that made them.
- **Target UFS version gates version-only APIs.** Resolved from TC frontmatter `ufs_version:`
  > `wiki/target.md`. A symbol whose struct only exists on another version is dropped from the
  FEED and flagged `version_unavailable` at the gate — don't force a 4.1-only accessor onto a
  3.1 target (see AGENTS.md → "Grounding FEED levers").
- **One method per unit, named exactly as the prompt states** (`stepN`, or a loop helper
  `_loopX_*`). A wrong name = dead code. Loops are ONE `stepN` wrapper + helpers (control
  flow cannot span methods).

## Where to look when something fails
- Fail points + history: `gate_logs/<pattern_id>.gate_log.md`.
- Pitfall rule pack: `python generate_pattern.py rules` (docs in `pattern_generator/review_refs/`).
- What grounding/defaults were offered per unit: `<run>/retrieval_debug.md`,
  `<run>/defaults_debug.md`.

## Related (already in this repo)
- gitnexus MCP usage skills: `GitNexusMCP/.claude/skills/gitnexus/*` (exploring / impact /
  refactoring / debugging / cli / guide) — used for the Step-B code grounding.
