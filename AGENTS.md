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
prepare-unit ×N → (Step B: unit_NN_*_methods.py) → assemble → validate`.
Steps prepare-ir / finalize-ir / prepare / prepare-unit / assemble / validate are
deterministic Python CLI commands; Step A and Step B are performed by the agent.
No external LLM API keys are used. See `CLAUDE.md` for command syntax and Step rules.
