# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
  - `GitNexusMCP/Script/` — the gitnexus-indexed **subset** (`api/`, `pattern/`,
    `project_api/`). Patterns are **generated here** (`PGConfig.generated_dir`) and this is
    what `from Script import api` resolves against for **mypy**. It has **no `lib/`**.
  - repo-root `Script/` — the **full runtime library**: same `api/` etc. **plus
    `lib/sdk_lib/`** (the SDK/HAL). Every pattern imports `from Script.lib import sdk_lib`,
    which only resolves here, so **keep it** (do not delete it as a "duplicate"). mypy from
    `GitNexusMCP/` ignores/excludes `^Script/lib`, so the missing `lib/` doesn't break the
    type-check — see the step-6b note below.
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

# Pipeline step 4b: build unit N's prompt (embeds upstream unit methods)
python generate_pattern.py prepare-unit <GEN>/<ID>/ <N>

# Paths: <GEN> = GitNexusMCP/Script/pattern/generated (the generated base, inside the
# Script/ tree so patterns are mypy-able). Per-run by-products live in <GEN>/<ID>/;
# the final pattern .py is written to <GEN>/ itself (next to real patterns).

# Pipeline step 5c: assemble scaffold + per-unit methods into final .py
#   -> writes <GEN>/<PatternName>.py ; by-products stay in <GEN>/<ID>/
python generate_pattern.py assemble <GEN>/<ID>/ <PatternName>

# Pipeline step 6: validate generated pattern against IR (+ API-reality check vs Script)
python generate_pattern.py validate <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json
#   optional: --script-root <path>  (defaults to PGConfig.script_root = GitNexusMCP/Script)
#   Report keys: syntax, structure, dataflow, api_grounding, mypy. structure catches methods
#   defined OUTSIDE the pattern class (parses but process() runs nothing = false PASS) +
#   def-after-__main__ + missing planned methods; dataflow flags a consumer that overwrites
#   a consumed var without reading it; api_grounding adds missing_required_arg; mypy runs the
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
#   - NOTE Script.lib has no copy under GitNexusMCP/Script (it's the gitnexus-indexed
#     subset); the ini ignores/excludes ^Script/lib so `from Script.lib import sdk_lib`
#     becomes Any. That's fine — the bug-catching imports (Script.api, Script.pattern.*,
#     cmd_seq) all resolve here. See "Environment & Dependencies" for the two Script trees.

# Code grounding: use the gitnexus MCP server (indexes Script/). At generation
# time call its `query` tool (top-N candidate symbols) + `context` (signatures).
# gitnexus is MCP-native — there is no Python CLI for queries.

# Wiki grounding: build the layered index, then query it
python wiki_index.py build              # steps 2+3: reference graph + (optional) dense
python wiki_retrieve.py "<query>"       # steps 4+5: RRF retrieval + extractive essence

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
- `parser.py`: Parses TC `.md` via regex into phase/step skeleton with metadata
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
- `stepwise.py`: Orders phases topologically and flattens to generation **units** (`generation_units`); builds `scaffold.py` and per-unit prompts (`build_one_unit_prompt`) — injects wiki RRF top-5 essence + `self.*` contracts + upstream continuity, and instructs the agent to call gitnexus for code refs
- `prepare.py`: `prepare_pattern` writes `scaffold.py` + `1_units.json` + first unit prompt; `prepare_unit` lazily builds unit N's prompt (wiki essence injected, upstream `unit_*_methods.py` embedded)
- `assemble.py`: Merges scaffold + `unit_NN_*_methods.py` into the final `.py` (+ `retrieval_debug.md`)
- `validator.py`: Validates `.py` against IR — `syntax` + `structure` (every stepN/helper is a class member; no method outside the class / after `if __name__`; planned methods present; loop_count) + `dataflow` (a consumer must not overwrite a `consumes` var without reading it) + `api_grounding`
- `api_grounding.py`: AST reality check of `api.`/`ExecuteCMD.`/`lib.` calls vs Script — unknown symbol / unknown kwarg / too-many-positional / **missing_required_arg**
- `rules.py`: loader over `review_refs/*.md` — the pitfall docs ARE the rule pack (add a rule = add a `.md`, no code). `select_refs(text, cap=6)` keyword-selects the relevant docs (BM25, score>0 only), `format_refs` renders them. This is the SEMANTIC layer; the deterministic API-detail layer is `api_grounding.py` (the two are complementary — an LLM review guesses param/enum/signature, the AST index never does).
- `review_refs/`: markdown pitfall docs (volatile-flag-assert-discipline, step03-query-vs-descriptor-trap, exception-naming-convention, writebooster-ssu-reset-pitfalls, …) ported from the external code-review agent. Drop a new `.md` here to add a review rule.
- `review.py`: `build_review_prompt` — IR checkpoints (each `expected`/`fail_condition` must be implemented AND asserted) + keyword-selected review references + the normalized TC flow (step-compliance cross-check) + whole file → LLM emits a corrected file. `find_tc_flow(ir, tc_dir)` loads `TC/<id>-normalized-test-flow.md`.
- `wholefile.py`: `build_wholefile_prompt` — Stage-3 coherent authoring (unit plan + `self.*` contract + `idioms.py` worked-snippet anchors + review references)
- `driver.py` + `gate_log.py`: the `finish` gate loop — validate→repair-prompt→re-validate; every run's findings appended to `gate_logs/<id>.gate_log.md` (all by-products in that one folder)

### Grounding Sources
- **Code (default)** — the **gitnexus** MCP server (indexes `Script/`). The agent calls its `query`/`context` tools at generation time to get real symbols.
- **Code (alt, `--grounding direct`)** — `code_retrieval/` (AST index over `Script` + reused BM25) injects top-N candidate symbols / worked idioms; no MCP server. The `validator` api-grounding check always reads `Script` directly regardless of mode.
- **LLM-Wiki** (`wiki/`): layered retriever (above). The pipeline injects the RRF top-5 essence into each unit prompt; conflict overrides win.

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
