# UFS Pattern Generator (self-contained)

Generate UFS test patterns (`.py`) from test-case flows (`TC/*.md`).

The pipeline is **TC → IR → pattern.py**. Deterministic work is Python; the
reasoning steps run on the **current model** (no API key, no `anthropic`
dependency — `pip install` only needs pytest). Every step grounds itself in two
real sources:

- **Code** — the **gitnexus** MCP server, which indexes `Script/` (`api/` Spec
  APIs, `pattern/` real patterns, `project_api/` customer APIs, `lib/` libs).
  The agent calls its `query`/`context` tools at generation time. Answers
  *how to implement* (real functions, call chains, signatures).
  - **Location & status**: the index lives at the relative path `GitNexusMCP/`
    (which contains the `Script/` library). **Embedding is already built** (local
    model; semantic search works, exact-scan fallback). Two repos are indexed, so
    every gitnexus tool call **must pass `repo="GitNexusMCP"`** (the other repo,
    `BrandNewGitNexus`, is unrelated). Canonical API idioms live in
    `GitNexusMCP/Script/pattern/sample_code/`.
  - Rebuild from `GitNexusMCP/`: `node .gitnexus/run.cjs analyze --embeddings --skip-git`
    (`--skip-git` because it is not a git repo; omit `--drop-embeddings` to keep
    existing embeddings for an incremental update).
- **Wiki** — the **ingested llm-wiki** (`wiki/`), queried by a layered retriever
  (reference graph + BM25 + optional dense + RRF + extractive essence). Answers
  *spec / customer constraints*. Two independent conflict rules: **CustomerReq >
  Spec** and **UserPrompt > ModelDefault**; every conflict logged in `conflicts.md`.

## Layout

| Path | Role |
|------|------|
| `Script/api lib pattern project_api` | pattern source = gitnexus code-grounding base |
| gitnexus MCP server | code grounding (indexes `Script/`; agent calls `query`/`context`) |
| `wiki/` | ingested llm-wiki (entities/ concepts/ conflicts.md + raw sources) |
| `wiki_retrieval/` + `wiki_index.py` + `wiki_retrieve.py` | layered wiki retrieval (graph+BM25+dense+RRF+essence) |
| `ir_generator/` | TC `.md` → IR JSON (parser + ingested-wiki lookup + agent annotation) |
| `pattern_generator/` | IR → step plan → generation prompt → validate |
| `TC/` | input test cases |
| `GitNexusMCP/Script/pattern/generated/` | **output base** — final pattern `.py` lands here (beside real patterns, so it is mypy-able / indexable); per-run by-products go in the `<PATTERN_ID>/` subfolder (see docs/AGENT_WORKFLOW.md) |
| `generate_pattern.py` | CLI for the deterministic stages |
| `docs/AGENT_WORKFLOW.md` | step-by-step contract + output-file reference |

## Install

```bash
pip install -r requirements.txt   # pytest only — no API key, no anthropic SDK
```

- The **core pipeline is pure stdlib**; `requirements.txt` only pins `pytest`.
- **Dense wiki retrieval is optional** and import-guarded:
  `pip install -r requirements-embed.txt` (`sentence-transformers` + `numpy`).
  Without it, retrieval falls back to pure-Python BM25 + reference graph.
- The generated patterns (under `GitNexusMCP/Script/pattern/generated/`, and
  `pattern_generator/stepwise.py`'s `Script`
  import) depend on the **`GitNexusMCP/Script/`** library's own deps (bitstruct,
  prettytable, pandas, numpy, pywin32, …). Those belong to the GitNexusMCP codebase
  and are only needed to *run* a generated pattern on hardware — do **not** add them
  to this repo's `requirements.txt`.

## How it works — the pipeline

Deterministic Python CLI steps alternate with two agent (LLM) steps, done by the
current model. **Generation granularity = unit** (the finest dependency-respecting
slice): every non-loop step → its own `stepN()` method (one Step-B call); a whole
loop phase → one `stepN()` method with the loop inlined.

**Output layout** — let `<GEN>` = `GitNexusMCP/Script/pattern/generated`. Per-run
by-products land in `<GEN>/<ID>/`; the final assembled `<PatternName>.py` is written
one level up in `<GEN>/` itself, so it sits beside the real patterns and can be
type-checked (mypy) and gitnexus-indexed.

```
TC .md  →  [1 prepare-ir]    →  <GEN>/<ID>/ir_skeleton.json + enrich_prompt.txt
        →  [2 Step A]        →  <GEN>/<ID>/annotations.json        (agent)
        →  [3 finalize-ir]   →  <GEN>/<ID>/<id>-ir.json
        →  [4 prepare]       →  <GEN>/<ID>/scaffold.py + 1_units.json + unit_01 prompt
        →  [4b prepare-unit] →  <GEN>/<ID>/unit_NN_<id>_prompt.txt  (embeds upstream unit methods)
        →  [5 Step B ×N]     →  <GEN>/<ID>/unit_NN_<id>_methods.py  (agent, one per unit)
        →  [5c assemble]     →  <GEN>/<PatternName>.py  (+ <GEN>/<ID>/retrieval_debug.md)
        →  [6 validate]      →  validation report (syntax + IR structure + API reality)
        →  [6b mypy]         →  type-check the final .py (see Type-checking below)
```

Replace the placeholders with the TC you are actually generating:
`<tc-file>` = the TC markdown filename, `<ID>` = the run folder (the pattern id,
e.g. derived from the TC), `<id>` = its lowercase form, `<PatternName>` = the
output class/file name, `<GEN>` = `GitNexusMCP/Script/pattern/generated`.
Do **not** hardcode any specific example id.

```bash
# <GEN> = GitNexusMCP/Script/pattern/generated

# 1. TC -> IR skeleton + enrich prompt (Python)
python generate_pattern.py prepare-ir TC/<tc-file>.md

# 2. Step A (agent): read <GEN>/<ID>/enrich_prompt.txt, write
#    <GEN>/<ID>/annotations.json  (phase + step-level produces/consumes + edges)

# 3. annotations -> final IR (Python)
python generate_pattern.py finalize-ir \
    <GEN>/<ID>/ir_skeleton.json <GEN>/<ID>/annotations.json

# 4. IR -> scaffold.py + 1_units.json + first unit prompt (Python)
python generate_pattern.py prepare <GEN>/<ID>/<id>-ir.json

# 4b. build unit N's prompt — embeds already-generated upstream unit methods (Python).
#     Run after each upstream unit's *_methods.py exists, for N = 2..(num units).
python generate_pattern.py prepare-unit <GEN>/<ID>/ <N>

# 5. Step B (agent, once per unit): read unit_NN_<id>_prompt.txt, write
#    unit_NN_<id>_methods.py  — sections: === WIKI REFS / CODE REFS / REVIEW FLAGS /
#    EXTRA IMPORTS / METHODS ===, containing exactly the one stepN() for that unit.

# 5c. assemble: writes <GEN>/<PatternName>.py (by-products stay in <GEN>/<ID>/) (Python)
python generate_pattern.py assemble <GEN>/<ID>/ <PatternName>

# 6. validate: syntax + IR structure + API reality (api_grounding vs Script) (Python)
#    --script-root defaults to GitNexusMCP/Script; the api-reality check flags calls
#    to api./ExecuteCMD./lib. symbols that don't exist or have bad kwargs/arity.
python generate_pattern.py validate \
    <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json [--script-root GitNexusMCP/Script]

# 6b. mypy the final pattern (see "Type-checking" below) — run where Script/ is top-level
```

## Type-checking the generated pattern (mypy)

The final `.py` lives under `GitNexusMCP/Script/pattern/generated/`, so it type-checks
against the real `Script/` library. **Run mypy from `GitNexusMCP/`** — there `Script/` is
the top-level package (so `from Script import api` resolves) and the
`mypy_skip_known_issue.ini` lives in that dir. The by-product subfolder
`Script/pattern/generated/<ID>/` is excluded by the ini (its `unit_*_methods.py` are
section-tagged fragments, not valid modules), while the top-level pattern `.py` is checked.

```bash
# only the modified pattern (fast, RECOMMENDED — clean output):
cd GitNexusMCP && python -m mypy --config-file mypy_skip_known_issue.ini \
    --follow-imports=silent Script/pattern/generated/<PatternName>.py
```

Passing the file path overrides the ini's `files = .` (checks just that file);
`--follow-imports=silent` resolves Script API types but reports only that file's errors.
(The bulk form `... ./` follows imports into the Script library and surfaces *pre-existing*
library type errors, not your pattern's — prefer the per-file form. `GitNexusMCP/Script`
has no `lib/`, so `from Script.lib import sdk_lib` is import-ignored/`Any`; the
bug-catching imports — `Script.api`, `Script.pattern.*`, `cmd_seq` — all resolve there.)
`validate`'s `api_grounding` check (step 6) is a fast pre-filter for unknown
symbols/bad kwargs; mypy is the authoritative gate (it also catches wrong attributes,
undefined `self.*`, and bad instance-method calls that `api_grounding` cannot see).

## Grounding rules (MANDATORY for the LLM generation step)

For **every** step, consult BOTH sources using their proper mechanism — never
ad-hoc text search:

- **Code** → call the **gitnexus** MCP `query` tool (**with `repo="GitNexusMCP"`**)
  using domain keywords to get the top-N candidate symbols, then `context` to confirm
  signatures. Do **not** assume a naming prefix. Pick the right `Script/` folder:
  `project_api/` for customer-specific behaviour, `api/` for Spec APIs, `pattern/`
  for the calling idiom (see `pattern/sample_code/`), `lib/` for low-level libs.
  Record the top-5 you used in `=== CODE REFS ===`.
- **Wiki** → use the injected RRF top-5 essence (the pipeline retrieves it for you);
  conflict overrides shown there WIN. Two independent rules: **CustomerReq > Spec**
  and **UserPrompt > ModelDefault**. Record pages used in `=== WIKI REFS ===`.
  (e.g. default LUN = MaxCapacity Enabled LUN, not 0; WriteBooster flag LUN must
  be Normal non-Boot index 0–7.)

Record provenance: tag each grounded element inline `# src[code]: <gitnexus path>:<sym>`
or `# src[wiki]: file`. If a source is missing, flag the unit in `=== REVIEW FLAGS ===`
(`TODO-REVIEW-NO-WIKI` / `-NO-CODE-REF` / `-BOTH-MISS`).

## Querying the llm-wiki (layered retrieval)

The wiki is queried by a deterministic **layered retriever** — you do not free-read it:

1. Build the index once: `python wiki_index.py build` (reference graph from
   `[[wikilinks]]` + optional dense embeddings).
2. Query: `python wiki_retrieve.py "<query>"` → Concept index → graph traversal →
   Entity index, fusing BM25 + dense via **RRF**, then an extractive **essence**
   ("concept → entity → reference → conflict override").
3. In the pipeline the per-unit RRF top-5 essence is **injected into the unit prompt**
   automatically; the agent grounds wiki facts from that block.
4. Conflicts are surfaced when a retrieved page is an "Affected Wiki Page" — the two
   independent rules (**CustomerReq > Spec**, **UserPrompt > ModelDefault**) WIN.

> Dense embeddings are optional (`pip install -r requirements-embed.txt`); without them
> retrieval uses BM25 + reference graph. `wiki_query.py` is deprecated.

## Generated pattern rules

- **First line MUST be `import package_root`** (path bootstrap), before the
  docstring and all other imports.
- Follow `pattern_template_wizard/pattern_template.py`: subclass `UFSTC`; implement
  `pre_process()` / `post_process()`; test steps are methods `step1`, `step2`, …
  (auto-run in order by `process()`).
- Carry phase data flow across steps as `self.<var>` attributes.
- A loop phase becomes one step method with an internal loop.
- Emit `# TODO human-confirm` for anything that cannot be grounded.

## Quick reference

```bash
# <dir> = <GEN>/<ID>/  where  <GEN> = GitNexusMCP/Script/pattern/generated
python generate_pattern.py prepare-ir TC/<tc>.md          # step 1
python generate_pattern.py finalize-ir <dir>/ir_skeleton.json <dir>/annotations.json  # step 3
python generate_pattern.py prepare <dir>/<id>-ir.json     # step 4
python generate_pattern.py prepare-unit <dir>/ <N>        # step 4b (per unit, N=2..)
python generate_pattern.py assemble <dir>/ <PatternName>  # step 5c → writes <GEN>/<PatternName>.py
python generate_pattern.py validate <GEN>/<PatternName>.py <dir>/<id>-ir.json  # step 6 (+api_grounding)
cd GitNexusMCP && python -m mypy --config-file mypy_skip_known_issue.ini \
    --follow-imports=silent Script/pattern/generated/<PatternName>.py  # step 6b (run from GitNexusMCP/)
python wiki_index.py build                     # build the wiki retrieval index
python wiki_retrieve.py "write booster flush"  # RRF retrieval + extractive essence
# code grounding: call the gitnexus MCP query/context tools (repo="GitNexusMCP"; no Python CLI)
python -m pytest -q                            # run the test suite
```

## For other agents / users

- **This README is the single entry point — it is enough to use the system.**
  At each step you read the prepared prompt file in `<GEN>/<ID>/`
  (`enrich_prompt.txt` for Step A, `unit_NN_<id>_prompt.txt` for each Step-B unit);
  those are **self-describing** — they embed the exact JSON schemas / output-section
  format and the grounding rules. So you do not need any other doc to operate.
- **Authoritative env/setup**: `CLAUDE.md` (Claude Code) and `AGENTS.md` (other agents)
  carry the same environment facts as this README (gitnexus location/embedding/`repo`
  param, dependency structure). They are kept in sync with this section.
- Optional deeper reference: **`docs/AGENT_WORKFLOW.md`** has a table of every
  output file (order, producer, meaning) — useful for debugging, not required.
- Visual overview: open **`docs/architecture-report.html`** in a browser — flow
  diagram, design rationale, a worked PF002_0098 example, and a debug guide.
- Self-contained and relative-path; copy the folder anywhere.
- After changing the pattern source under `Script/`, re-index it in gitnexus so the
  code-grounding graph stays current.
- After changing the wiki (`entities/`/`concepts/`/`conflicts.md`), rebuild the
  retrieval index: `python wiki_index.py build`.
