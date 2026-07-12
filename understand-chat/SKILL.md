---
name: understand-chat
description: Use when you need to ask questions about a codebase or understand code using a knowledge graph — including "how do I implement X" questions answered by fusing ALL knowledge graphs in the repo (wiki/knowledge + code graphs) with anchor-verified citations
argument-hint: "[query]"
---

# /understand-chat

Answer questions about this codebase using EVERY knowledge graph present in the
repository (`.ua/knowledge-graph.json`, or the legacy
`.understand-anything/knowledge-graph.json`) — a repo may hold several graphs
(e.g. a `kind: "knowledge"` wiki graph plus one or more `kind: "codebase"` code
graphs in subtrees). All of them participate in retrieval.

## Graph Structure Reference

The knowledge graph JSON has this structure:
- `kind` — `"codebase"` | `"knowledge"` | `"design"` — distinguishes a code graph
  from a wiki/domain-knowledge graph. Implementation questions use both kinds.
- `project` — {name, description, languages, frameworks, analyzedAt, gitCommitHash}
- `nodes[]` — each has {id, type, name, filePath?, lineRange?, summary, tags[], complexity, languageNotes?}
  - `lineRange` is `[startLine, endLine]` — the node's location inside `filePath`.
    Use it to READ AND VERIFY the actual source before citing a code node.
  - Code node types: file, function, class, module, concept
  - Non-code node types: config, document, service, table, endpoint, pipeline, schema, resource
  - Domain/knowledge node types: domain, flow, step, article, entity, topic, claim, source
  - IDs use the node type as prefix, e.g. `file:path`, `function:path:name`, `config:path`, `article:path`
- `edges[]` — each has {source, target, type, direction, weight}
  - Key types: imports, contains, calls, depends_on, configures, documents, deploys, triggers, contains_flow, flow_step, related, cites
- `layers[]` — each has {id, name, description, nodeIds[]}
- `tour[]` — each has {order, title, description, nodeIds[]}

## How to Read Efficiently

1. Use Grep to search within the JSON for relevant entries BEFORE reading the full file
2. Only read sections you need — don't dump the entire graph into context
3. Node names and summaries are the most useful fields for understanding
4. Edges tell you how components connect — follow imports and calls for dependency chains

## Instructions

1. **Discover ALL graphs** — search the whole repository for graph files, not
   just the current directory's:
   ```
   find . -path "*/node_modules" -prune -o -name knowledge-graph.json \( -path "*/.understand-anything/*" -o -path "*/.ua/*" \) -print
   ```
   (or Glob `**/.understand-anything/knowledge-graph.json` and
   `**/.ua/knowledge-graph.json`). For each hit, Grep its `"kind"` and
   `"project"` name and list what you found, e.g.:
   - `wiki/.understand-anything/knowledge-graph.json` — kind: knowledge (domain wiki)
   - `Script/pattern/.understand-anything/knowledge-graph.json` — kind: codebase (patterns)
   Steps 3–5 below run against EACH graph. If none exist, tell the user to run
   `/understand` (code) or `/understand-knowledge` (docs/wiki) first.
   NOTE: a code node's `filePath` is relative to THAT graph's own root (the
   directory containing its `.understand-anything/`), not the repo root.

2. **Read project metadata only** — use Grep or Read with a line limit to extract just the `"project"` section from the top of each graph file for context (name, description, languages, frameworks).

3. **Search for relevant nodes (in every graph)** — use Grep to search each knowledge graph file for the user's query keywords: "$ARGUMENTS"
   - Search `"name"` fields: `grep -i "query_keyword"` in the graph file
   - Search `"summary"` fields for semantic matches
   - Search `"tags"` arrays for topic matches
   - Note the `id` values of all matching nodes (and which graph each came from)

4. **Find connected edges** — for each matched node ID, Grep for that ID in the `edges` section of its own graph to find:
   - What it imports or depends on (downstream)
   - What calls or imports it (upstream)
   - This gives you the 1-hop subgraph around the query

5. **Read layer context** — Grep for `"layers"` to understand which architectural layers the matched nodes belong to.

6. **Answer the query** using only the relevant subgraph:
   - Reference specific files, functions, and relationships from the graph
   - Explain which layer(s) are relevant and why
   - Be concise but thorough — link concepts to actual code locations
   - If the query doesn't match any nodes, say so and suggest related terms from the graph
   - If the question is a HOW-DO-I-IMPLEMENT question, you MUST follow the
     stricter protocol below instead of answering from summaries alone.

## Implementation questions (how-do-I-implement protocol)

When the question asks HOW TO IMPLEMENT something ("怎麼實作", "用哪個 API",
"how do I implement/do X", "which function performs X"), the generic flow above
is NOT enough — graph summaries are LLM interpretation, not source truth, and a
name-similar node is often the WRONG API (an enum or parameter type instead of
the operation that performs the step). Follow this stricter protocol:

1. **Retrieve both halves.**
   - From `kind: "knowledge"` graphs: concept/claim/article/entity nodes — what
     the thing IS and its constraints (e.g. "this flag is volatile, resets to 0
     after any reset").
   - From `kind: "codebase"` graphs: function/class/method nodes — how it is
     DONE. Prefer nodes whose `filePath` lies under a `sample_code/` directory
     or a real pattern/caller over bare library type definitions (enums/structs
     are parameters, not operations).

2. **Anchor-verify every code node before citing it (MANDATORY).**
   Resolve `filePath` against that graph's own root, Read a window of
   `lineRange[0] ± 5` lines, and confirm the node's `name` symbol actually
   appears there. A node that fails this check is DROPPED from the
   implementation answer (list it under "Dropped" for transparency).
   Confidence rides the verified anchor — never the graph summary's assertion.

3. **Show real usage.** For each surviving top exemplar, follow its `calls`
   edges BACKWARD (who calls it) and Read one real call site; include it in the
   answer. An operation's true idiom lives at its call sites, not in its
   signature.

4. **Answer in this exact shape** (mandate the citation, never a ready-to-paste
   command):

   ```
   ## Concept (knowledge graph)
   - <name> — <one-line summary> (<source page path>)

   ## Implementation exemplars (code graph, anchor-verified)
   - <symbol> — <filePath>:<startLine> — <one-line summary> [VERIFIED]
     real call site: <path>:<line>

   ## Dropped (anchor verification failed)
   - <symbol> — <reason, e.g. anchor mismatch / file missing>

   ## Caveat
   These are navigation, not evidence — confirm every API against the real
   source (e.g. `python code_retrieve.py def/callers "<symbol>"` where that
   tool exists, or read the defining file) before writing it into code.
   ```

5. **If NO code node survives anchor verification**, say plainly that there is
   no trustworthy implementation source in the graphs, present only the
   knowledge-graph concept half, and DO NOT guess an API name. A wrong-but-
   plausible suggestion is worse than none.
