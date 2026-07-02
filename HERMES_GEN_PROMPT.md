# Pattern Generation Runbook (agent prompt)

**ROLE**: You are a UFS pattern-generation agent for this repo (TC → Pattern pipeline).
After reading this file, **WAIT for the user to name a target** — do not start generating.
The target may be given as:

- a TC markdown path: `TC/<file>.md`, or
- a pattern ID (e.g. `PF010_0310`) — resolve it yourself: look for a matching
  `TC/*.md` (case-insensitive, `_`/`-` interchangeable) or an existing IR at
  `<GEN>/<ID>/<id>-ir.json`. If both are ambiguous or neither exists, ask the user.

**GOAL**: first generation correct — `finish` must reach GATE PASS with **at most 1
repair round**. The per-unit gate exists so bugs die at the unit, not at the end.

## Environment facts

- `<GEN>` = `GitNexusMCP/Script/pattern/generated` (run by-products in `<GEN>/<ID>/`,
  the final `.py` one level up in `<GEN>/`).
- **Code grounding**: gitnexus MCP indexes `GitNexusMCP/Script`. Every gitnexus tool
  call **must pass `repo="GitNexusMCP"`**. If you have NO gitnexus MCP, add
  `--grounding direct` to `prepare` and ground by reading `GitNexusMCP/Script` source.
- Core pipeline is pure-stdlib Python; run commands from the repo root.
- Detailed rules live in `AGENTS.md` + `CLAUDE.md` — read them if anything here is
  unclear. Every LLM step's full instructions are in the `.txt` prompt the CLI emits;
  those emitted prompts are AUTHORITATIVE (this file only orchestrates).

## Procedure

### 0. Resolve mode + clean stale artifacts (ALWAYS)

- IR already exists (`<GEN>/<ID>/<id>-ir.json`) → skip to step 4 (reuse the IR).
- Otherwise start at step 1 with the TC file.
- **Before step 4, delete stale generation artifacts from a previous run**:
  every `unit_*_methods.py` and `unit_*_prompt.txt` under `<GEN>/<ID>/`
  (keep `*-ir.json`, `ir_skeleton.json`, `annotations.json`). Stale unit files WILL
  be globbed into `assemble` and poison the result. An old `<GEN>/<PatternName>.py`
  will simply be overwritten.

### 1–3. TC → IR (skip if IR exists)

```bash
python generate_pattern.py prepare-ir TC/<file>.md
# read <GEN>/<ID>/enrich_prompt.txt  -> write <GEN>/<ID>/annotations.json  (LLM Step A)
python generate_pattern.py finalize-ir <GEN>/<ID>/ir_skeleton.json <GEN>/<ID>/annotations.json
```

### 4. IR → scaffold + unit plan

```bash
python generate_pattern.py prepare <GEN>/<ID>/<id>-ir.json     # [--grounding direct]
```

### 5. Per-unit generation loop (k = 1..N, order per `1_units.json`)

```bash
python generate_pattern.py prepare-unit <GEN>/<ID>/ <k>
# "loop wrapper — skip" -> deterministic, do NOT hand-write; go to k+1.
# else: read <GEN>/<ID>/unit_kk_*_prompt.txt -> write unit_kk_*_methods.py
python generate_pattern.py validate-unit <GEN>/<ID>/ <k>
# FAIL -> every finding contains its FIX (e.g. "write api.init_tester_to_unit_ready(...)").
#         Rewrite ONLY that unit file accordingly, re-run validate-unit until PASS.
#         Only then move to k+1.
```

Hard rules for writing a unit (the emitted prompt repeats these — obey it):

- **Namespace rule (AUTHORITATIVE, gate-enforced)**: prefix every Script symbol by
  its defining file path — `Script/api/cmd_seq/**` → `ExecuteCMD.<name>`, other
  `Script/api/**` → `api.<name>` (enums too: `api.Dcmd5ResetType`), `Script/lib/**`
  → `lib.<name>`. Reference patterns show BARE names (they star-import ufs_api);
  you MUST re-prefix them. Never guess a prefix; never write a bare Script symbol.
- Logging uses the scaffold's `logger` (`_log` does not exist). Any stdlib module
  you use (`time`, `copy`, …) must be declared in `=== EXTRA IMPORTS ===`.
- Exactly ONE method, named exactly as the prompt states; loop sub-step helpers
  take `(self, loop_idx)`.
- Ground every API call: gitnexus `query` (top-5) + `context` to confirm the exact
  signature (always `repo="GitNexusMCP"`); record them in `=== CODE REFS ===`.
  When the TC is silent (e.g. which LUN), follow the injected project defaults —
  do NOT hardcode `lun=0`; tag defaults used with `# src[wiki]: default.md`.

### 6. Assemble

```bash
python generate_pattern.py assemble <GEN>/<ID>/ <PatternName>
```

`<PatternName>` = the scaffold's class name (see `class <Name>(UFSTC)` in
`<GEN>/<ID>/scaffold.py`). Check `<GEN>/<ID>/retrieval_debug.md` afterwards: any
per-unit api-grounding issue listed there must be fixed in the unit file(s) and
re-assembled BEFORE running `finish`.

### 7. Gate loop

```bash
python generate_pattern.py finish <GEN>/<PatternName>.py <GEN>/<ID>/<id>-ir.json
# FAIL -> read gate_logs/<id>_repair_prompt.txt, rewrite the WHOLE .py fixing EVERY
#         finding (each carries its resolution), re-run finish.
# PASS -> read gate_logs/<id>_review_prompt.txt, do one rule-level review pass.
```

## Final report (always give the user)

1. Path of the assembled pattern + PASS/FAIL.
2. Number of `finish` repair rounds used (target ≤ 1).
3. Whether the latest round of `gate_logs/<id>.gate_log.md` still contains any of
   these mechanical classes: `name is not defined` / `wrong_namespace` / `bare name`
   / `defined more than once` / `must have signature (self, loop_idx)`.
   These should be ZERO by assemble time — if any survived to `finish`, say which
   unit produced it.
4. Count of `TODO human-confirm` / `TODO-REVIEW-*` flags left in the file (from
   `retrieval_debug.md`).
