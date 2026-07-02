# AGENTS.md

Guidance for AI agents working in this repository (TC → Pattern pipeline).
Claude Code reads `CLAUDE.md`; this file mirrors the key environment facts for other agents.

## Environment & Dependencies (read first)

- **Code grounding (gitnexus)**: the gitnexus MCP server's index lives at the relative path
  `GitNexusMCP/` (it contains the `Script/` library being grounded). **Embedding is already
  built** (local model; semantic search works, exact-scan fallback — no VECTOR extension).
  Two repos are indexed, so every gitnexus tool call **must pass `repo="GitNexusMCP"`**
  (the other repo, `BrandNewGitNexus`, is unrelated). Canonical API idioms live in
  `GitNexusMCP/Script/pattern/sample_code/`.
  - Rebuild the index from `GitNexusMCP/`: `node .gitnexus/run.cjs analyze --embeddings --skip-git`
    (`--skip-git` because it is not a git repo; omit `--drop-embeddings` to keep existing
    embeddings for an incremental update).

- **Python dependencies**:
  - The **core pipeline is pure stdlib** — `prepare-ir` / `finalize-ir` / `prepare` /
    `assemble` / `validate` need no third-party packages. `requirements.txt` only pins
    `pytest` (for the test suite). Install: `pip install -r requirements.txt`.
  - **Dense wiki retrieval is optional** and import-guarded: `requirements-embed.txt`
    (`sentence-transformers` + `numpy`). Without it, retrieval silently falls back to
    pure-Python BM25 + reference-graph traversal. Install only if needed:
    `pip install -r requirements-embed.txt`.
  - The patterns under `generated/` (and `pattern_generator/stepwise.py`'s `Script` import)
    depend on the `GitNexusMCP/Script/` library's own third-party deps (bitstruct, prettytable,
    pandas, numpy, pywin32, …). Those belong to the **GitNexusMCP** codebase and are only
    needed to *run* a generated pattern on hardware — do NOT add them to this repo's
    `requirements.txt`.

## Pipeline (full detail in CLAUDE.md)

`TC .md → prepare-ir → (Step A: annotations.json) → finalize-ir → prepare →
prepare-unit ×N → (Step B: unit_NN_*_methods.py) → assemble → finish (gate loop)`.
Deterministic Python CLI: prepare-ir / finalize-ir / prepare / prepare-unit /
assemble / validate / review / finish. LLM steps (Step A, Step B, repairs) are
performed by the agent. No external LLM API keys are used.

**Loops:** `prepare-ir` auto-collapses a cross-phase loop written as a JIRA 對照表
`| Loop | … | Loop（Phase 1 → Phase 2 → Phase 3）|` row into ONE `type:"loop"` phase, which
becomes a single `stepN` loop-wrapper (+ one helper per sub-step) — so the burn-in `for` loop
is materialized, not dropped. You just generate the helpers; the wrapper is auto-written.

**Key design for agents: every LLM step's instructions are in a self-contained
`.txt` prompt the CLI writes.** You don't need a meta-prompt — run the command,
read the emitted prompt file, write the named output. The prompt files are:
`enrich_prompt.txt` (Step A), `unit_NN_*_prompt.txt` (Step B per unit),
`<id>_repair_prompt.txt` / `<id>_review_prompt.txt` (the `finish` gate loop),
`wholefile_prompt.txt` (the Stage-3 whole-file alternative).

### Packaged skill (discoverable entry point)
A repo-local skill at `.claude/skills/generate-pattern/SKILL.md` packages this whole flow so
any agent's skill mechanism can find + run it. It indexes back to this file and CLAUDE.md.

### Feed-once runbook prompt
`HERMES_GEN_PROMPT.md` (repo root) is a self-contained agent prompt: feed that one file to
an agent, then just name the target ("gen PF010_0310" or a TC path). It waits for the
target, cleans stale run artifacts, runs the full pipeline with the per-unit gate
discipline, and reports rounds + surviving finding classes.

### Quick start — onboarding ANY agent (incl. non-Claude-Code)

Prerequisites for the agent:
- Read **AGENTS.md AND CLAUDE.md** (CLAUDE.md has the command syntax + Step rules +
  the `unit_NN_*_methods.py` section format).
- **Python** (core pipeline is pure stdlib) + this repo checked out. Can run shell
  commands and read/write files.
- **Grounding:** the default path tells the agent to call the **gitnexus MCP** tools.
  An agent WITHOUT gitnexus MCP must use **`prepare --grounding direct`** (pure-Python
  retrieval; no MCP) and confirm signatures by reading `GitNexusMCP/Script` source.

Kickoff message to paste to another agent (no-MCP / portable form):
```
Read AGENTS.md and CLAUDE.md to understand this TC→Pattern pipeline. Then generate a
pattern from TC/<file>.md following the Orchestration steps below. Use
`prepare --grounding direct` (you have no gitnexus MCP); ground each API call on the
injected candidates and by reading GitNexusMCP/Script source. Run `finish` repeatedly,
fixing every finding in its repair prompt, until GATE PASS.
Project defaults (default.md) are auto-injected: when the TC omits a detail (e.g. which
LUN), follow them — do NOT hardcode lun=0 (use the MaxCapacity Enabled LUN rule); tag any
default you use as `# src[wiki]: default.md`, and see <run>/defaults_debug.md for what was
offered. Fail points accumulate in gate_logs/<id>.gate_log.md; the pitfall checklist is
`python generate_pattern.py rules`.
```
(If the agent HAS gitnexus MCP, drop `--grounding direct` to use the default path.)

### Orchestration prompt (copy-paste for another agent)
```
Generate a UFS test pattern for TC/<file>.md. Run, in order:
1. python generate_pattern.py prepare-ir TC/<file>.md
2. read <run>/enrich_prompt.txt  -> write <run>/annotations.json
3. python generate_pattern.py finalize-ir <run>/ir_skeleton.json <run>/annotations.json
4. python generate_pattern.py prepare <run>/<id>-ir.json [--grounding direct]   # direct = no MCP
5. for k=1..N: python generate_pattern.py prepare-unit <run> k
                read <run>/unit_kk_*_prompt.txt -> write unit_kk_*_methods.py
                (loop-wrapper units report "skip" — do NOT hand-write them)
                python generate_pattern.py validate-unit <run> k   # per-unit gate
                GATE FAIL -> rewrite unit_kk_*_methods.py fixing every finding, re-run
                             validate-unit until PASS, THEN move to k+1. Catches the
                             bug at its source unit (cheaper than end-stage repair).
6. python generate_pattern.py assemble <run> <PatternName>
7. python generate_pattern.py finish <gen>/<PatternName>.py <run>/<id>-ir.json
      GATE FAIL -> read the printed <id>_repair_prompt.txt, rewrite the WHOLE .py
                   fixing every finding, re-run finish (until GATE PASS or max-rounds).
      GATE PASS -> read <id>_review_prompt.txt, do one rule-level review pass.
```

### New commands (since the original pipeline)
- `prepare --grounding {gitnexus,direct}` — `direct` injects candidate symbols from
  `Script` via `code_retrieval` (no MCP server); default `gitnexus` is unchanged.
- `validate` — reports the full key set **`syntax · structure · dataflow · api_grounding
  · semantic · mypy`**. `structure` = every stepN/helper is a class member (no method
  outside the class / after `if __name__`); `dataflow` = a consumer must not re-derive a
  var it should inherit; `api_grounding` adds `missing_required_arg` / `unknown_enum_member`
  / **`version_unavailable`** (a symbol whose return struct doesn't exist on the target UFS
  version — see FEED levers below); `semantic` = deterministic MEANING checks
  (`semantic_checks.py`, e.g. `wb_support_path`); `mypy` = per-file type-check gate.
  **mypy runs by default** (from `GitNexusMCP/` with `mypy_skip_known_issue.ini`); pass
  `--no-mypy` to disable. The old "manual step 6b" is now automatic.
- `finish` — gate driver: validate (incl. mypy unless `--no-mypy`); on FAIL emit a repair
  prompt (validator findings + review) and loop (`--max-rounds`, default 3); on PASS emit
  the review prompt.
- `review` — build the review→repair prompt: IR checkpoints + the **relevant review
  references** (keyword-selected pitfall docs, cap 6) + the **normalized TC flow**
  (cross-checked for step compliance) + code.
- `rules` — list the review-reference pitfall docs in `pattern_generator/review_refs/`
  (add a rule = drop a `.md` there; no code change — see "Two review layers" below).
- `prepare-wholefile` — Stage-3 alternative: one whole-file authoring prompt
  (idiom anchors + review references + data-flow contract) instead of per-unit fragments.
- `build-defaults` — merge `wiki/UserPrompt` + `wiki/ModelDefault` (+ `conflicts.md`) →
  `wiki/default.md`: the resolved "what to do when the TC is silent" policy
  (UserPrompt > ModelDefault + CustomerReq constraints). Regenerate after editing those.
- `python wiki_lint.py` — deterministic wiki health check (dangling `[[wikilinks]]`, missing
  `type:`, orphans, stale `default.md`, conflicts→missing pages, unused source/code trees).
  Run after editing the wiki; exit 1 on any error. Code-only grounding stays in gitnexus/Script
  — NO code tree belongs under `wiki/` (the lint errors on one).
- **VC (Verification Criteria, `wiki/VC/`, `wiki_retrieval/vc.py`)** — 361 per-pattern test
  specs (criterion + checkpoints + expected results). Auto-used: a capped, BM25-gated VC band
  is surfaced in unit-prompt wiki essence; `review`/`finish` injects matched VC docs (keyword +
  exact `pattern_id`) as checkpoints the pattern must implement+assert. `wiki_index.py build`
  embeds the `vc` layer for dense.

### Project defaults (what to do when the TC omits a detail)
`wiki/default.md` is split by trigger and injected automatically — you do NOT retrieve it:
- **Overrides (§1-§3: UserPrompt LUN rule, CustomerReq constraints)** are ALWAYS injected
  into every unit/wholefile prompt (they fire on *absence* of info — e.g. "TC didn't say
  which LUN", which has no keyword to retrieve on). So: don't hardcode `lun=0` — use the
  MaxCapacity-Enabled-LUN rule when the TC is silent.
- **ModelDefault base (§4)** is retrieved per step (top-1 topic) to save tokens.
- The model only APPLIES a default when the TC is silent; if the TC specifies it, follow
  the TC. Tag any default you use as `# src[wiki]: default.md`.

### Where to see fail points / pitfalls / provenance
- **Fail points (per run + history):** `gate_logs/<pattern_id>.gate_log.md` —
  append-only, timestamped, every `validate`/`finish` run's findings. The same folder
  holds the transient `<id>_repair_prompt.txt` / `_review_prompt.txt` / `_gate_state.json`.
- **Pitfall checklist (the review references):** `python generate_pattern.py rules`,
  docs in `pattern_generator/review_refs/*.md` (loader: `pattern_generator/rules.py`).

### Two rule layers (advisory LLM-review vs deterministic gate — complementary)
Rules split into two layers, each doing only what it is uniquely good at:
- **Advisory layer = references-driven LLM review** (`review`/`finish`). Protocol path,
  volatile-flag asserts, reset determinism, exception naming, TC-step compliance, … live
  as markdown pitfall docs in `pattern_generator/review_refs/`. **Adding a rule = adding a
  `.md`** (no hand-coded check); the relevant docs are keyword-selected per pattern (cap 6)
  so the folder can grow without bloating any one prompt. This layer *suggests* — it is
  BM25-selected and may not fire.
- **Deterministic layer = gate-enforced, two enforcers.** These are machine-decidable and
  FAIL the gate, so high-value rules belong here, not the advisory `.md`:
  - **`api_grounding.py`** — one AST index over `Script`, used FOUR ways. It FEEDS at
    generation (Phase B — exact signatures / enum members / struct fields of return types)
    and CATCHES at the gate via (1) `check_api_calls`
    (symbol/kwarg/positional/`missing_required_arg`/`unknown_enum_member`),
    (3) `check_struct_fields` (a field not on the call's return struct, e.g. a
    `DeviceDescriptor` field read off the WriteBooster-support union), (4) `check_citations`
    (a `=== CODE REFS ===` citation whose symbol exists nowhere — audit). Its sibling
    **`capability_resolver.check_version_availability`** adds the `version_unavailable`
    CATCH (a symbol whose return struct has no variant for the target UFS version).
  - **`semantic_checks.py`** — a deterministic MEANING layer (the `semantic` gate key) for
    invariants `api_grounding` can't decide (attribute access / value logic). Active rule
    `wb_support_path` (WriteBooster support must be
    `get_extended_ufs_features_support().u8_write_booster`, not the FFU bit `u0_ffu`). It is
    CATCH (`check_semantics`) + PREVENT (`CANONICAL_IDIOMS`, injected at generation) from one
    source of truth. It also runs `check_ir_protocol_paths(ir)` (Lever #4) — **report-only**,
    surfaced by `prepare` to `<run>/ir_lint.md` (a TC step whose stated protocol path
    contradicts a canonical idiom; never rewrites the TC).
  The LLM review must NOT invent API; if unsure it reads real `Script` source, and these
  deterministic enforcers catch any residual guess.

### Generation grounding: top-3 + injected exact API facts (Phase B)
Per-unit prompts inject **top-3** wiki essence + **top-3** code candidates (token-sensitive
×N path) — AND, from the same AST index the gate uses, the **exact signatures + valid enum
members + struct fields (of return types)** for the unit's likely symbols (`api_grounding.api_facts`, via `prepare._unit_api_facts`,
both gitnexus and direct modes). So the model COPIES `read_attribute(idn, index=…, selector=…)`
and `AttributeIDN` members verbatim instead of guessing `lun=` / wrong enum case. This is
additive: wiki (flow meaning) and gitnexus/code-candidate discovery still run; the facts only
nail the exact form. Correctness comes from these deterministic facts, not from more candidate names.
- **Code query ≠ wiki query** (`prepare._unit_code_query`): the symbols FEED resolves facts for
  come from a query enriched with the unit's `produces`/`consumes`/`set_vars` var names
  (`write_record_p1`→`write record`), NOT the raw protocol tokens (`WRITE(10)`, `POR`) — those
  match low-level CDB classes, so FEED would inject facts for the wrong abstraction layer.
  This helps where the var names carry API vocabulary; pure-operation steps with no data-flow
  vars (e.g. bare POR) still need gitnexus's semantic/graph layer to bridge the vocabulary gap.
- **Mode-aware fact authority:** in **gitnexus** mode the injected facts are a CROSS-CHECK
  (retrieved by the weaker code_retrieval proxy → may be sibling/wrong-layer); the signature
  the model confirms via its own gitnexus `context()` is PRIMARY and wins on conflict. In
  **direct** mode (no gitnexus) they stay AUTHORITATIVE. So the FEED never out-ranks the
  model's own gitnexus discovery when the two disagree.
- **Grounding FEED levers (target-version + idiom force-feed):** the FEED is made
  deterministic where it can be, not just heuristic top-N:
  - **Target UFS version** (`pattern_generator/ufs_version.py`) is a first-class input,
    resolved TC-frontmatter `ufs_version:` > `wiki/target.md` (`ufs_version: X.Y`). It gates
    version-only APIs both ways: `capability_resolver.version_gate` DROPS a FEED candidate
    whose return struct exists only on another version (e.g. a 4.1-only accessor on a 3.1
    target), and `check_version_availability` CATCHES it at the gate (`version_unavailable`).
    This kills the "4.1 API leaks into a 3.1 pattern" class of bug at its source.
  - **Canonical-symbol force-feed** (`capability_resolver.canonical_symbols`): the accessor a
    canonical idiom points at is force-added to the FEED symbol list, so the CORRECT
    accessor's real signature + struct fields anchor the model — not just idiom prose beside
    a wrong sibling's fields.
  - **Procedure idioms** (`pattern_generator/procedure_idioms.py`, `match_procedures`): when
    the correct implementation is a multi-step PROCEDURE with no single API (seed:
    `max_capacity_lun`), an authoritative guard is injected — do NOT substitute a
    name-similar single call; ground each step; emit a fail-loud `TODO human-confirm` rather
    than fabricate a value.
  - **Per-unit micro-gate:** `prepare-unit N` re-runs the deterministic checks
    (`unit_gate.check_unit`) on the upstream unit N-1 and prepends any failure to unit N's
    prompt — self-healing even if you skipped the explicit `validate-unit` step.
- **Defaults provenance:** `<run>/defaults_debug.md` (deterministic — which default
  overrides + ModelDefault topic were OFFERED to each unit) + `retrieval_debug.md` (which
  embeds it, alongside the model's self-reported `# src[wiki]` usage).

See `CLAUDE.md` for command syntax and Step rules.
