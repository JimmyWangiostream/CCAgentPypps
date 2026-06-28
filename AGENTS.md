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

**Key design for agents: every LLM step's instructions are in a self-contained
`.txt` prompt the CLI writes.** You don't need a meta-prompt — run the command,
read the emitted prompt file, write the named output. The prompt files are:
`enrich_prompt.txt` (Step A), `unit_NN_*_prompt.txt` (Step B per unit),
`<id>_repair_prompt.txt` / `<id>_review_prompt.txt` (the `finish` gate loop),
`wholefile_prompt.txt` (the Stage-3 whole-file alternative).

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
fixing every finding in its repair prompt, until GATE PASS. Fail points accumulate in
gate_logs/<id>.gate_log.md; the pitfall checklist is `python generate_pattern.py rules`.
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
6. python generate_pattern.py assemble <run> <PatternName>
7. python generate_pattern.py finish <gen>/<PatternName>.py <run>/<id>-ir.json
      GATE FAIL -> read the printed <id>_repair_prompt.txt, rewrite the WHOLE .py
                   fixing every finding, re-run finish (until GATE PASS or max-rounds).
      GATE PASS -> read <id>_review_prompt.txt, do one rule-level review pass.
```

### New commands (since the original pipeline)
- `prepare --grounding {gitnexus,direct}` — `direct` injects candidate symbols from
  `Script` via `code_retrieval` (no MCP server); default `gitnexus` is unchanged.
- `validate` — now also reports **structure** (every stepN/helper is a class member;
  no method outside the class / after `if __name__`) and **dataflow** (a consumer must
  not re-derive a var it should inherit), plus api `missing_required_arg`.
- `finish` — gate driver: validate; on FAIL emit a repair prompt (validator findings +
  review) and loop (`--max-rounds`, default 3); on PASS emit the review prompt.
- `review` — build the review→repair prompt (IR checkpoints + rule pack + code).
- `rules` — print the prescriptive rule pack (the pitfall checklist).
- `prepare-wholefile` — Stage-3 alternative: one whole-file authoring prompt
  (idiom anchors + rule pack + data-flow contract) instead of per-unit fragments.
- `build-defaults` — merge `wiki/UserPrompt` + `wiki/ModelDefault` (+ `conflicts.md`) →
  `wiki/default.md`: the resolved "what to do when the TC is silent" policy
  (UserPrompt > ModelDefault + CustomerReq constraints). Regenerate after editing those.

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
- **Pitfall checklist (the rules):** `python generate_pattern.py rules`, source in
  `pattern_generator/rules.py`.
- **Defaults provenance:** `<run>/defaults_debug.md` (deterministic — which default
  overrides + ModelDefault topic were OFFERED to each unit) + `retrieval_debug.md` (which
  embeds it, alongside the model's self-reported `# src[wiki]` usage).

See `CLAUDE.md` for command syntax and Step rules.
