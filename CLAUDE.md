# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Generating a pattern from a TC?** A packaged skill at
> `.claude/skills/generate-pattern/SKILL.md` indexes the whole pipeline (any agent can invoke
> it); `AGENTS.md` is the detailed runbook. This file has the command syntax + Step rules.

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
- **Two `Script/` trees (don't confuse them):**
  - `GitNexusMCP/Script/` — the gitnexus-indexed tree (`api/`, `pattern/`,
    `project_api/`, **and now `lib/sdk_lib/`**). Patterns are **generated here**
    (`PGConfig.generated_dir`) and this is what `from Script import api` resolves against
    for **mypy**. `lib/sdk_lib/` (the SDK/HAL) was added here and **is now in the gitnexus
    index** (graph + FTS + embeddings + `context` signatures), so `from Script.lib import
    sdk_lib` symbols are groundable at generation time. It is still **excluded from the
    mypy gate** (see below) — grounded, but not type-checked.
  - repo-root `Script/` — the **full runtime library**: same `api/` etc. **plus
    `lib/sdk_lib/`** (the SDK/HAL). Every pattern imports `from Script.lib import sdk_lib`;
    keep this tree (do not delete it as a "duplicate"). mypy from `GitNexusMCP/`
    ignores/excludes `^Script/lib` in BOTH trees, so `lib/` (HAL, with pre-existing type
    issues) doesn't break the type-check — see the step-6b note below.
  - The `mypy_skip_known_issue.ini` lives in `GitNexusMCP/`; run mypy from that dir.
- **Python dependencies**:
  - The **core pipeline is pure stdlib** — `prepare-ir` / `finalize-ir` / `prepare` /
    `assemble` / `validate` need no third-party packages. `requirements.txt` only pins
    `pytest` (for the test suite).
  - **Dense wiki retrieval is optional** and import-guarded: `requirements-embed.txt`
    (`sentence-transformers` + `numpy`). Without it, retrieval silently falls back to
    pure-Python BM25 + reference-graph traversal.
  - The patterns under `generated/` (and `pattern_generator/stepwise.py`'s `Script` import)
    depend on the `GitNexusMCP/Script/` library's own third-party deps (bitstruct, prettytable,
    pandas, numpy, pywin32, …). Those belong to the **GitNexusMCP** codebase and are only
    needed to *run* a generated pattern on hardware — do NOT add them to this repo's
    `requirements.txt`.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest -q

# Run a single test file
python -m pytest tests/test_parser.py -v

# Pipeline step 1: parse TC markdown → skeleton + enrichment prompt
python generate_pattern.py prepare-ir TC/<tc-file>.md

# Pipeline step 3: merge annotations into final IR
python generate_pattern.py finalize-ir <GEN>/<ID>/ir_skeleton.json <GEN>/<ID>/annotations.json

# Pipeline step 4: IR → scaffold.py + 1_units.json + first unit prompt
python generate_pattern.py prepare <GEN>/<ID>/<id>-ir.json

# Pipeline step 4b: build unit N's prompt (embeds upstream unit methods).
#   ALSO runs the per-unit gate on unit N-1 and, if it failed, prepends a
#   "## FIX UPSTREAM UNIT FIRST" block to unit N's prompt (self-heals upstream bugs).
python generate_pattern.py prepare-unit <GEN>/<ID>/ <N>

# Pipeline step 5b (per-unit gate): after WRITING unit N's methods, run the SAME
# deterministic checks the final gate runs (api_grounding + semantic + citation) on
# THAT unit. On FAIL (exit 1): read the findings, REWRITE unit_NN_<id>_methods.py, re-run;
# then proceed to the next unit. Catches the bug at its source unit, not at end-stage
# review. (pattern_generator.unit_gate.check_unit — same source of truth as `validate`.)
python generate_pattern.py validate-unit <GEN>/<ID>/ <N>   # [--script-root <path>]

# Paths: <GEN> = GitNexusMCP/Script/pattern/generated (the generated base, inside the
# Script/ tree so patterns are mypy-able). Per-run by-products live in <GEN>/<ID>/;
# the final pattern .py is written to <GEN>/ itself (next to real patterns).

# Pipeline step 5c: assemble scaffold + per-unit methods into final .py
#   -> writes <GEN>/<PatternName>.py ; by-products stay in <GEN>/<ID>/
python generate_pattern.py assemble <GEN>/<ID>/ <PatternName>

# Pipeline step 6: validate generated pattern against IR (+ API-reality check vs Script)
python generate_pattern.py validate <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json
#   optional: --script-root <path>  (defaults to PGConfig.script_root = GitNexusMCP/Script)
#   Report keys: syntax, structure, dataflow, api_grounding, semantic, mypy. structure catches
#   methods defined OUTSIDE the pattern class (parses but process() runs nothing = false PASS) +
#   def-after-__main__ + missing planned methods; dataflow flags a consumer that overwrites
#   a consumed var without reading it; api_grounding adds missing_required_arg; semantic adds
#   deterministic MEANING checks api_grounding can't (e.g. WriteBooster support read via the
#   FFU bit u0_ffu instead of u8_write_booster) — pure AST, no Script needed; mypy runs the
#   type-check gate (per-file, from GitNexusMCP/ + its ini) — catches type errors api_grounding
#   can't; "skipped" if mypy/config absent. --no-mypy to disable. Step 6b is now automatic.
#   Appends findings to gate_logs/<id>.gate_log.md (history). --gate-log-dir to override.

# Pipeline step 7 (gate loop): validate -> on FAIL emit a repair prompt (validator findings
# + review), on PASS emit the review prompt; loops to convergence.
python generate_pattern.py finish <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json
#   --max-rounds N (default 3). All by-products + the append-only history land in ONE folder:
#   gate_logs/  ->  <id>.gate_log.md, <id>_repair_prompt.txt, <id>_review_prompt.txt,
#   <id>_gate_state.json. LLM: read the repair/review prompt, rewrite the WHOLE .py, re-run.

# Review prompt only (Stage 2): IR checkpoints (each expected/fail_condition must be asserted)
# + rule pack + the code -> LLM emits a corrected full file.
python generate_pattern.py review <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json

# Pitfall checklist (the prescriptive rule pack used by review/finish):
python generate_pattern.py rules

# Alt grounding (no MCP server): inject candidate symbols straight from Script.
python generate_pattern.py prepare <GEN>/<ID>/<id>-ir.json --grounding direct
#   default is --grounding gitnexus (unchanged). direct writes to generate_without_gitnexus/.

# Stage-3 alternative (whole-file authoring instead of per-unit fragments):
python generate_pattern.py prepare-wholefile <GEN>/<ID>/<id>-ir.json
#   -> one wholefile_prompt.txt (idiom anchors + rule pack + data-flow contract); LLM writes
#   the COMPLETE .py in one coherent pass, then run `finish`.

# Pipeline step 6b: mypy the generated pattern. Run from GitNexusMCP/ — there Script/ is
# the top-level package (so `from Script import api` resolves) and the ini lives in that
# dir. The by-product subfolder Script/pattern/generated/<ID>/ is excluded by the ini (its
# unit_*_methods.py are section-tagged fragments, not valid modules).
#   only the modified pattern (fast, RECOMMENDED — clean output):
cd GitNexusMCP && python -m mypy --config-file mypy_skip_known_issue.ini --follow-imports=silent Script/pattern/generated/<PatternName>.py
#   - passing the file path overrides the ini's `files = .` (checks just that file);
#     --follow-imports=silent resolves Script API types but only reports THIS file's
#     errors. Use --follow-imports=skip for max speed (APIs become Any; the validator's
#     api_grounding check already covers symbol/signature reality).
#   - the bulk form (`... ./`) follows imports into the Script library and surfaces
#     PRE-EXISTING library type errors (adv_rpmb, device_desc, pattern_template) — not
#     your pattern's. Prefer the per-file form above.
#   - NOTE Script.lib/sdk_lib now EXISTS under GitNexusMCP/Script and IS in the gitnexus
#     index (so it's groundable), but the mypy ini still ignores/excludes ^Script/lib, so
#     `from Script.lib import sdk_lib` becomes Any for the type-check. That's fine — the
#     bug-catching imports (Script.api, Script.pattern.*, cmd_seq) all resolve here. See
#     "Environment & Dependencies" for the two Script trees.

# Code grounding: use the gitnexus MCP server (indexes Script/). At generation
# time call its `query` tool (top-N candidate symbols) + `context` (signatures).
# gitnexus is MCP-native — there is no Python CLI for queries.

# Wiki grounding: build the layered index, then query it
python wiki_index.py build              # steps 2+3: reference graph + (optional) dense
python wiki_retrieve.py "<query>"       # steps 4+5: RRF retrieval + extractive essence

# Wiki health check (deterministic; SCHEMA.md's "Lint" operation): dangling [[wikilinks]],
# missing `type:` frontmatter, orphans, stale default.md, conflicts->missing pages, and
# unused source/code trees under wiki/ (code tree = ERROR). Reports only; exit 1 on any error.
python wiki_lint.py                     # [--wiki <path>]  (wiki_retrieval/lint.py)

# Project defaults: merge wiki/UserPrompt + wiki/ModelDefault (+conflicts) -> wiki/default.md
python generate_pattern.py build-defaults
#   default.md = the resolved "what to do when the TC is silent" policy (UserPrompt >
#   ModelDefault, + CustomerReq constraints), with per-line provenance. It is ALWAYS
#   injected into unit/wholefile/review prompts (NOT top-N — policy is cross-cutting).
#   Regenerate after editing wiki/UserPrompt|ModelDefault|conflicts. (Replaced the weak
#   essence "conflict pointer" that named an override but not its resolved value.)
```

## Architecture: TC → Pattern Pipeline

The system converts UFS test case flows (Markdown) into executable Python test patterns. **No external API keys are used**—LLM steps are performed by the current Claude Code session.

```
TC .md  →  [1 prepare-ir]    →  enrich_prompt.txt
        →  [2 LLM Step A]    →  annotations.json
        →  [3 finalize-ir]   →  <id>-ir.json
        →  [4 prepare]       →  scaffold.py + 1_units.json + unit_01_<id>_prompt.txt
        →  [4b prepare-unit] →  unit_NN_<id>_prompt.txt  (embeds upstream unit methods)
        →  [5 LLM Step B×N]  →  unit_NN_<id>_methods.py  (one LLM call per unit)
        →  [5c assemble]     →  <PatternName>.py
        →  [6 validate]      →  validation report
```

Steps 1, 3, 4, 4b, 5c, 6 are deterministic Python CLI commands. Steps 2 and 5 are performed by Claude reading the prompt file and producing the output file.

**Generation granularity = unit, not phase.** A *unit* is the finest dependency-respecting slice:
- every non-loop step is its own unit → one `stepN()` method, one LLM call
- a loop phase is a single unit → one `stepN()` method with the whole loop inlined (control flow cannot span methods, or `process()` would never run the loop)

Step-level `produces`/`consumes` (added by Step A enrichment) drive each unit's `self.*` contract; they do NOT merge steps. Splitting is aggressive (split unless an explicit dependency or loop membership forces grouping).

- **Step 4** (`prepare`) outputs `scaffold.py` (markers `# @@EXTRA_IMPORTS@@` / `# @@PHASE_METHODS@@`), `1_units.json` (the ordered unit plan), and only `unit_01_<id>_prompt.txt` (the first unit has no upstream context).
- **Step 4b** (`prepare-unit N`) builds `unit_NN_<id>_prompt.txt`, **embedding the already-generated upstream unit methods** (continuity) plus the symbols already grounded and helpers already defined. Run it after each upstream unit's methods file exists.
- **Step 5** (LLM, per unit): read `unit_NN_<id>_prompt.txt`, write `unit_NN_<id>_methods.py` (format: `=== GROUNDING LOG ===` / `=== EXTRA IMPORTS ===` / `=== METHODS ===` sections) containing exactly the one `stepN()` method for that unit.
- **Step 5c** (`assemble`) merges imports and injects all `unit_*_methods.py` blocks into the scaffold; also writes `retrieval_debug.md` (per-unit wiki top-5 + gitnexus code top-5 + review flags).

Per-run by-products land in `GitNexusMCP/Script/pattern/generated/<PATTERN_ID>/`; the final
assembled pattern `.py` is written one level up, in `GitNexusMCP/Script/pattern/generated/`,
so it can be type-checked (mypy) and indexed alongside the real patterns.

## Key Architectural Components

### IR Generator (`ir_generator/`)
- `parser.py`: Parses TC `.md` via regex into phase/step skeleton with metadata. Also
  **collapses a cross-phase loop** (`_collapse_loop_region`): when the JIRA 對照表 has a
  `| Loop | … | Loop（Phase 1 → Phase 2 → Phase 3）|` row (no `## Loop` header), the named
  contiguous phases are merged into ONE `type:"loop"` phase so `stepwise.generation_units`
  materializes the burn-in `for` loop. No-op when there's no Loop row / a phase already is a
  loop / the phases aren't contiguous. (Fixes the silently-dropped loop; the `loop_back` edge
  representation is no longer needed.)
- `prepare_ir.py`: Orchestrates TC → `ir_skeleton.json` + `enrich_prompt.txt`
- `enrich_prompt.py`: Builds the LLM Step A prompt (asks for phase data flow)
- `wiki_lookup.py`: Per-phase wiki refs via the layered retriever (`wiki_retrieval.retrieve`); applies conflict-resolved overrides

### Wiki Retrieval (`wiki_retrieval/`)
Layered retrieval over the ingested wiki (`wiki/concepts/` + `wiki/entities/`):
- `corpus.py`/`graph.py`: parse frontmatter + `[[wikilinks]]` → reference graph (step 2)
- `bm25.py`/`embedder.py`: pure-Python BM25 (always on) + optional dense embedder (step 3, import-guarded; `pip install -r requirements-embed.txt`)
- `retrieve.py`: Concept→graph→Entity, fusing BM25+dense via RRF; surfaces conflicts (step 4)
- `essence.py`: deterministic extractive "concept → entity → reference → conflict" essence (step 5)

### Pattern Generator (`pattern_generator/`)
- `stepwise.py`: Orders phases topologically and flattens to generation **units** (`generation_units`); builds `scaffold.py` and per-unit prompts (`build_one_unit_prompt`) — injects wiki RRF top-5 essence + `self.*` contracts + upstream continuity, and instructs the agent to call gitnexus for code refs. The gitnexus grounding instructions carry an **IDIOM & SELECTION** block: `query` returns not just candidate names but PROCESSES + `sample_code`/real-pattern files, and when several sibling symbols look plausible the model must disambiguate by READING a real caller/sample idiom (not by name similarity / rank1) — the protocol *path* is the test (e.g. WriteBooster support = `get_extended_ufs_features_support().u8_write_booster`, not a descriptor field). This attacks the wrong-API-chosen trap that `context`-signature-confirmation alone cannot.
- `prepare.py`: `prepare_pattern` writes `scaffold.py` + `1_units.json` + first unit prompt; `prepare_unit` lazily builds unit N's prompt (wiki essence injected, upstream `unit_*_methods.py` embedded). **Two query builders:** `_unit_query` (wiki/defaults — protocol tokens) and `_unit_code_query` (code candidates + api-facts FEED — `_unit_query` PLUS the unit's `produces`/`consumes`/`set_vars` var names, underscore-split into intent words). Raw protocol tokens (`WRITE(10)`, `POR`) retrieve the WRONG abstraction layer (low-level CDB classes); var names like `write_record_p1`→`write record` bridge to the high-level api idiom (surfaces `get_empty_write_record` rank2 where the raw query missed). Keep code retrieval on `_unit_code_query`, not `_unit_query`. **Canonical idioms are passed SEPARATELY** (`_unit_canonical` → `build_one_unit_prompt(canonical_facts=…)`): they are the PREVENT half of an enforced gate rule, so they ride their OWN authoritative block (override any contradicting IR-step path) and are NOT bundled into the mode-aware-demoted heuristic `api_facts`. `prepare` also writes `<run>/ir_lint.md` (Lever #4 protocol-path contradictions). **FEED levers:** `_unit_api_facts` now threads a resolved `_target_version(ir, config)` (`ufs_version.resolve`) so it runs `capability_resolver.version_gate` (drops version-unavailable sibling candidates) and force-feeds `canonical_symbols` (prepends the canonical idiom's accessor); `_unit_procedures` injects `procedure_idioms.match_procedures` guards. **Per-unit micro-gate:** `prepare_unit` runs `unit_gate.check_unit` on the immediately-upstream unit and prepends any failure to the current unit's prompt (self-heals even if `validate-unit` was skipped).
- `assemble.py`: Merges scaffold + `unit_NN_*_methods.py` into the final `.py` (+ `retrieval_debug.md`)
- `validator.py`: Validates `.py` against IR — `syntax` + `structure` (every stepN/helper is a class member; no method outside the class / after `if __name__`; planned methods present; loop_count) + `dataflow` (a consumer must not overwrite a `consumes` var without reading it) + `api_grounding` (which now also runs `capability_resolver.check_version_availability` → `version_unavailable` against the resolved target version) + `semantic` + `mypy` (opt-in, default on; `--no-mypy` to skip — see Commands)
- `semantic_checks.py`: deterministic SEMANTIC layer (sibling to `api_grounding`) — catches MEANING-level bugs the AST symbol-check deliberately skips (attribute access / value logic). Rule registry; findings reuse the `check_api_calls` issue-dict shape so `format_issues` + the gate (`validator` `semantic` key, `driver._GATE_KEYS`) handle them unchanged. CATCH (`check_semantics`) + PREVENT (`CANONICAL_IDIOMS`/`canonical_facts`, injected via `prepare._unit_api_facts`), one source of truth. Active rule `wb_support_path` (WriteBooster support must be `get_extended_ufs_features_support().u8_write_booster`, not the FFU bit `u0_ffu`). **IR-level flag (Lever #4):** `check_ir_protocol_paths(ir)` (registry `IR_PATH_RULES`, same idiom source) flags a STEP whose stated protocol path contradicts a canonical idiom (e.g. a WB-support step grounded to READ DESCRIPTOR / Device Descriptor) — **report-only** (never rewrites the TC; surfaced by `prepare` to `<run>/ir_lint.md`), while the generation prompt's authoritative canonical block OVERRIDES the contradiction. Conservative/false-negative bias like `api_grounding`. (`_device_init_polarity` is written but DORMANT — readiness polarity disputed across artifacts; do not enforce until confirmed.) Add a rule = add a matcher fn + register in `RULES` + a test.
- `api_grounding.py`: the AST index over Script, used FOUR ways. (1) **CHECK** (`check_api_calls`): reality-check `api.`/`ExecuteCMD.`/`lib.` calls — unknown symbol / unknown kwarg / too-many-positional / **missing_required_arg** / **unknown_enum_member**; findings carry the real signature. (2) **FEED** (`api_facts`, Phase B): inject the exact signatures + relevant enum members for a unit's likely symbols INTO the generation prompt (via `prepare._unit_api_facts`, both grounding modes) so the model copies (`index=`, `IDLE`) instead of guessing. The "likely symbols" are resolved by `code_retrieval` over `prepare._unit_code_query` (the data-flow-var-enriched query — protocol-token-only queries surface wrong-layer symbols, so FEED would otherwise inject facts for the wrong API; see `prepare.py`). **Mode-aware authority** (`build_one_unit_prompt`): in **direct** mode code_retrieval is the only code source so the facts are labelled AUTHORITATIVE (copy verbatim, confirm by reading source); in **gitnexus** mode they are labelled a CROSS-CHECK — the model's own gitnexus `context()` on the symbol IT picked is PRIMARY and wins on conflict (model-side FEED↔discovery alignment, since Python can't query the MCP-only gitnexus at prepare time). (3) **CITATION REALITY** (`check_citations`): audit the agent's self-reported `=== CODE REFS ===` — flag a cited `path.py:symbol` whose symbol exists NOWHERE in Script (fabricated grounding citation, e.g. `random_read_and_compare`); surfaced per-unit in `retrieval_debug.md` by `assemble` (the harmful case — a fake symbol actually USED in code — is already a gate failure via CHECK). (4) **STRUCT FIELDS** (`check_struct_fields` + `_build_struct_fields`/`resolve_fields`, fed via `api_facts`): the index also captures each function's return-type (`SigSpec.returns`) and every struct's field set (`self.x=` + class-level + `@property`, merged across base classes). FEED injects `<ReturnType> fields: …` so the model copies the real field; CATCH flags `var.field`/`api.F().field` where the field isn't on that return struct (e.g. reading a `DeviceDescriptor` field `l85_…` off the WriteBooster-support union) — precise via var-origin (single-assignment) + inline-call, conservative (skips chains/`self.*`, global fallback when a type can't be resolved → ~0 false positives over the real pattern corpus). Single AST source of truth for prevent + catch + audit.
- `ufs_version.py`: target UFS spec version as a first-class deterministic input. `resolve(ir, config)` picks TC frontmatter `ufs_version:` > project default `wiki/target.md` (`ufs_version: X.Y`) > None (no gating). `struct_suffix`/`normalize` map `"4.1"`→`"410"` (the versioned struct suffix `api_grounding` uses). Rationale: a 4.1-only accessor (e.g. `get_extended_write_booster_support` → `DeviceDescriptor410`) must not leak into a 3.1 pattern (the Hermes WB bug); knowing the target version lets the pipeline exclude version-unavailable symbols deterministically.
- `capability_resolver.py`: deterministic, version-aware capability resolution over the SAME `api_grounding` AST index — replaces name-similarity guessing where it can decide, conservative fallback where it can't. `version_gate(index, names, version)` DROPS a FEED candidate whose return struct exists only on a non-target version. `canonical_symbols(canonical_facts)` parses the accessor a canonical idiom points at (`api.get_extended_ufs_features_support().u8_write_booster` → `get_extended_ufs_features_support`) and force-feeds it so the CORRECT accessor's real signature + struct fields anchor the model. `check_version_availability(py_source, index, version)` is the CATCH complement — flags `api./ExecuteCMD./lib.X()` whose return struct has no variant for the target version (`validator` finding kind `version_unavailable`).
- `procedure_idioms.py`: `PROCEDURE_IDIOMS` registry (same shape as `semantic_checks.CANONICAL_IDIOMS`) + `match_procedures(query)` — fires when ALL a rule's trigger tokens appear in the data-flow-enriched unit query. For intents that are a MULTI-STEP PROCEDURE with no single API (seed `max_capacity_lun`: enumerate enabled LUNs via `b3_lu_enable`, read each `get_unit_descriptor`, pick largest — do NOT substitute `get_max_number_of_lun()` + fabricate `count-1`), it injects an AUTHORITATIVE guard: ground each real step, and emit a fail-loud `TODO human-confirm` rather than fabricate a field. Injected into every unit prompt via `prepare._unit_procedures`.
- `rules.py`: loader over `review_refs/*.md` — the pitfall docs ARE the rule pack (add a rule = add a `.md`, no code). `select_refs(text, cap=6)` keyword-selects the relevant docs (BM25, score>0 only), `format_refs` renders them. This is the ADVISORY semantic layer (LLM review, BM25-selected, may not fire). The DETERMINISTIC layers are `api_grounding.py` (symbol/signature reality) and `semantic_checks.py` (machine-decidable MEANING invariants, enforced by the gate). High-value rules should be promoted from the advisory `.md` to `semantic_checks.py` so they are enforced, not merely suggested (when promoting, trim the `.md` to a pointer so prose can't contradict the enforcer).
- `review_refs/`: markdown pitfall docs (volatile-flag-assert-discipline, step03-query-vs-descriptor-trap, exception-naming-convention, writebooster-ssu-reset-pitfalls, …) ported from the external code-review agent. Drop a new `.md` here to add a review rule.
- `review.py`: `build_review_prompt` — IR checkpoints (each `expected`/`fail_condition` must be implemented AND asserted) + keyword-selected review references + the normalized TC flow (step-compliance cross-check) + whole file → LLM emits a corrected file. `find_tc_flow(ir, tc_dir)` loads `TC/<id>-normalized-test-flow.md`.
- `wholefile.py`: `build_wholefile_prompt` — Stage-3 coherent authoring (unit plan + `self.*` contract + `idioms.py` worked-snippet anchors + review references)
- `driver.py` + `gate_log.py`: the `finish` gate loop — validate→repair-prompt→re-validate; every run's findings appended to `gate_logs/<id>.gate_log.md` (all by-products in that one folder)

### Grounding Sources
- **Code (default)** — the **gitnexus** MCP server (indexes `Script/`). The agent calls its `query`/`context` tools at generation time to get real symbols.
- **Code (alt, `--grounding direct`)** — `code_retrieval/` (AST index over `Script` + reused BM25) injects top-N candidate symbols / worked idioms; no MCP server. The `validator` api-grounding check always reads `Script` directly regardless of mode.
- **LLM-Wiki** (`wiki/`): layered retriever (above). The pipeline injects the RRF top-5 essence into each unit prompt; conflict overrides win.
- **Target version** (`wiki/target.md`, `ufs_version: X.Y`): the project-wide default UFS spec version (TC frontmatter `ufs_version:` overrides per-TC). Read by `ufs_version.resolve`; gates version-only APIs at FEED (`version_gate`) and CATCH (`version_unavailable`). Not retrieved — it's a deterministic input, not essence.
- **VC — Verification Criteria** (`wiki/VC/`, `wiki_retrieval/vc.py`): 361 per-pattern test specs (criterion + checkpoints + expected results, rich in real API idioms; no frontmatter, layer forced to `vc`). Used TWICE, like the other deterministic-vs-LLM split: (1) a small capped **retrieval band** in the unit-prompt essence (`Retriever`/`build_essence`, `n_vc=2`, BM25-gated so an unrelated query surfaces none); (2) **review injection** — `review.build_review_prompt` adds matched VC docs (keyword-selected + exact `pattern_id` prioritized) as checkpoints the pattern must implement+assert. `wiki_index build` embeds the `vc` layer for dense.

### Pattern Base (`pattern_template_wizard/pattern_template.py`)
Generated patterns subclass `UFSTC`, implementing `step1()`, `step2()`, ... methods that are auto-run by `process()`. Data flows across steps via `self.var_name` attributes. Override `pre_process()` / `post_process()` for device setup/teardown.

## LLM Step Rules (Critical)

### LLM Step A — Enrichment (`annotations.json`)
- Input: `enrich_prompt.txt` (phase skeleton + wiki excerpts)
- Output schema (phase-level **and** step-level data flow):
  `{"phases": [{phase_id, inputs, outputs, "steps": [{step_id, produces, consumes}]}], "edges": [{"from", "to", "data_flow"}]}`
- Step-level `produces`/`consumes` are essential: each step is generated as its own unit, so they define the `self.*` contract wiring steps together.

### LLM Step B — Generation (one `unit_NN_*_methods.py` per unit)
Each unit emits sections in order: `=== WIKI REFS ===` / `=== CODE REFS ===` /
`=== REVIEW FLAGS ===` / `=== EXTRA IMPORTS ===` / `=== METHODS ===`. Constraints:
- Exactly one method named `stepN` (the prompt states which); any other name = dead code.
- Data shared between steps via `self.var_name` attributes (per the injected `self.*` contract).
- **Code grounding**: call the gitnexus MCP `query` tool (top-5 candidate symbols) and
  `context` to confirm signatures; record the top-5 used in `=== CODE REFS ===`.
- **Wiki grounding**: use ONLY the injected wiki essence (RRF top-5); record pages used in
  `=== WIKI REFS ===`. Conflict overrides win.
- Tag grounded elements `# src[code]: <gitnexus path>:<sym>` or `# src[wiki]: wiki/path.md`.
- **Review flags** (also inline-comment on the method's first line):
  `TODO-REVIEW-NO-WIKI` (wiki empty, code found) · `TODO-REVIEW-NO-CODE-REF` (wiki found,
  gitnexus empty) · `TODO-REVIEW-BOTH-MISS` (neither). `assemble` aggregates these into
  `retrieval_debug.md`.

## Wiki Authority — two independent rules

Conflicts are resolved by TWO SEPARATE pairwise rules (not one merged chain), and every
conflict is recorded in `wiki/conflicts.md`:
- **Rule 1**: `CustomerReq` > `Spec`
- **Rule 2**: `UserPrompt` > `ModelDefault`

The two orders are independent of each other. The RESOLVED overrides (the actual values to
use, with their how-to-apply) are merged into `wiki/default.md` (`build-defaults`) and
**always injected** into every prompt — so the generator gets "default LUN = MaxCapacity
Enabled LUN, do NOT hardcode lun=0" as an imperative, not just a pointer that an override
exists. `wiki/default.md` = ModelDefault base + UserPrompt overrides + CustomerReq
constraints, per-line provenance; `wiki/conflicts.md` stays as the audit record.

## Tests

Tests live in `tests/` and use pytest. Fixtures (sample TC files, IR JSON) are in `tests/fixtures/`. `test_no_anthropic.py` asserts no `anthropic` SDK import exists anywhere—keep it that way.
