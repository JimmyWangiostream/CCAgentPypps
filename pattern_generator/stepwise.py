"""Walk an IR into an ordered, phase-aware step plan and a generation prompt.
No LLM, no code retrieval — grounding is done on demand by the generating model."""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_REL = "pattern_template_wizard/pattern_template.py"


def topo_order_phases(ir: dict) -> list[str]:
    """Return phase_ids in dependency (topological) order. Falls back to the
    phases' natural order if the dependency_graph is missing/empty."""
    phases = [p["phase_id"] for p in ir.get("phases", [])]
    dg = ir.get("dependency_graph") or {}
    edges = dg.get("edges") or []
    if not edges:
        return phases
    incoming = {pid: 0 for pid in phases}
    adj = {pid: [] for pid in phases}
    for e in edges:
        f, t = e.get("from"), e.get("to")
        if f in adj and t in incoming:
            adj[f].append(t)
            incoming[t] += 1
    queue = [pid for pid in phases if incoming[pid] == 0]
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj[n]:
            incoming[m] -= 1
            if incoming[m] == 0:
                queue.append(m)
    # Append any leftover (cycle safety) preserving natural order
    for pid in phases:
        if pid not in order:
            order.append(pid)
    return order


def ordered_steps(ir: dict) -> list[dict]:
    """Flatten phases (in topological order) into a flat ordered step list.
    Each entry carries its phase context so generation respects dependencies."""
    by_id = {p["phase_id"]: p for p in ir.get("phases", [])}
    steps = []
    n = 0
    for pid in topo_order_phases(ir):
        phase = by_id[pid]
        for s in phase.get("steps", []):
            n += 1
            steps.append({
                "seq": n,
                "method": f"step{n}",
                "phase_id": pid,
                "phase_name": phase.get("name"),
                "phase_type": phase.get("type"),
                "loop_type": phase.get("loop_type"),
                "loop_count": phase.get("loop_count"),
                "phase_inputs": phase.get("inputs", []),
                "phase_outputs": phase.get("outputs", []),
                "step": s,
            })
    return steps


# ---------------------------------------------------------------------------
# Scaffold + per-unit generation (Step 4)
# ---------------------------------------------------------------------------

import re as _re
from collections import defaultdict as _defaultdict

STANDARD_IMPORTS = """\
import package_root
from Script import api
from Script.lib import sdk_lib as lib
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
import Script.api.cmd_seq as ExecuteCMD"""

SCAFFOLD_EXTRA_IMPORTS_MARKER = "# @@EXTRA_IMPORTS@@"
SCAFFOLD_METHODS_MARKER = "    # @@PHASE_METHODS@@"


def derive_class_name(ir: dict) -> str:
    """Derive a valid Python class name from pattern_id + title."""
    title = ir.get("title", ir.get("pattern_id", "Pattern"))
    for suffix in ["-Normalized-TestFlow", "-Test-Flow", "-TestFlow"]:
        title = title.replace(suffix, "")
    name = _re.sub(r"[^A-Za-z0-9_]", "_", title)
    name = _re.sub(r"_+", "_", name).strip("_")
    return name or "Pattern"


def build_scaffold(ir: dict) -> str:
    """Build the deterministic class skeleton (contains no step methods)."""
    class_name = derive_class_name(ir)
    pattern_id = ir.get("pattern_id", "")
    title = ir.get("title", "")
    return (
        f"{STANDARD_IMPORTS}\n"
        f"{SCAFFOLD_EXTRA_IMPORTS_MARKER}\n"
        f"\n"
        f"\nclass {class_name}(UFSTC):\n"
        f'    """{pattern_id} — {title}"""\n'
        f"\n"
        f"    def pre_process(self) -> None:\n"
        f"        pass  # TODO human-confirm: pre-test device setup\n"
        f"\n"
        f"{SCAFFOLD_METHODS_MARKER}\n"
        f"\n"
        f"    def post_process(self) -> None:\n"
        f"        pass  # TODO human-confirm: post-test teardown\n"
        f"\n"
        f"\nif __name__ == '__main__':\n"
        f"    {class_name}().run()\n"
    )




# ---------------------------------------------------------------------------
# By-UNIT generation (Step 4 — finest granularity)
#
# A "unit" is the generation/method granularity:
#   - every non-loop step is its own unit       -> one stepK() method, one LLM call
#   - each sub-step of a loop is its own unit    -> one HELPER method (_<slug>_<id>),
#     one LLM call; control flow can't span methods so the loop body is decomposed
#     into helpers, NOT inlined.
#   - a loop also gets one deterministic WRAPPER unit -> the stepK() method that runs
#     `for loop_idx in range(N): self._<slug>_<id>(loop_idx)` over its helpers.
# Step-level produces/consumes (from IR enrichment) drive the self.* contract;
# they are NOT used to merge steps. Upstream methods are embedded into each
# downstream unit's prompt (continuity) as the safety net for any missed dependency.
#
# Two counters: `index` = file/seq order (filename unit_NN, ordering) for EVERY unit;
# `step_no` advances only for units that become a real stepN (sequential steps + loop
# wrappers) — helpers never burn a stepN number.
# ---------------------------------------------------------------------------


def _slug(phase_id: str) -> str:
    """A filename/identifier-safe slug from a phase_id (e.g. loop_4 -> loop4)."""
    return _re.sub(r"[^a-z0-9]", "", str(phase_id).lower())

def _ordered_union(lists) -> list:
    """Flatten an iterable of lists into a de-duplicated, order-preserving list."""
    seen: set = set()
    out: list = []
    for lst in lists:
        for x in lst or []:
            if x not in seen:
                seen.add(x)
                out.append(x)
    return out


def generation_units(ir: dict) -> list[dict]:
    """Flatten the IR into ordered generation units.

    Non-loop steps split aggressively (one unit each -> one stepN method). A loop
    phase expands into one HELPER unit per sub-step (one method `_<slug>_<id>` each)
    plus one deterministic WRAPPER unit (the stepN method that runs the for-loop over
    those helpers). self.* contracts (set_vars / available_vars) are derived from
    step-level produces/consumes.
    """
    by_id = {p["phase_id"]: p for p in ir.get("phases", [])}

    units: list[dict] = []
    seq = 0        # file/order index -> unit["index"], filename unit_NN
    step_no = 0    # real stepN counter (sequential steps + loop wrappers only)
    for pid in topo_order_phases(ir):
        phase = by_id[pid]
        steps = phase.get("steps", [])
        if phase.get("type") == "loop":
            slug = _slug(pid)
            helper_methods: list = []
            for s in steps:
                seq += 1
                hu = _make_unit(seq, phase, [s], kind="loop_substep", unit_id=s["step_id"])
                hu["method"] = f"_{slug}_{s['step_id']}"
                hu["loop_idx_param"] = True
                helper_methods.append(hu["method"])
                units.append(hu)
            seq += 1
            step_no += 1
            wu = _make_unit(seq, phase, steps, kind="loop_wrapper", unit_id=pid)
            wu["method"] = f"step{step_no}"
            wu["helper_methods"] = helper_methods
            units.append(wu)
        else:
            for s in steps:
                seq += 1
                step_no += 1
                su = _make_unit(seq, phase, [s], kind="step", unit_id=s["step_id"])
                su["method"] = f"step{step_no}"
                units.append(su)

    _annotate_contracts(units, ir)
    return units


def _make_unit(index: int, phase: dict, steps: list, kind: str, unit_id: str) -> dict:
    produces = _ordered_union(s.get("produces", []) for s in steps)
    produced_set = set(produces)
    # consumes that are satisfied inside this same unit are not external needs
    consumes = [c for c in _ordered_union(s.get("consumes", []) for s in steps)
                if c not in produced_set]
    return {
        "index": index,                     # file/order index -> filename unit_NN
        "method": "",                       # assigned by caller (stepN or helper name)
        "kind": kind,                       # "step" | "loop_substep" | "loop_wrapper" | (legacy) "loop"
        "unit_id": unit_id,                 # for filenames (step_id or loop phase_id)
        "phase_id": phase["phase_id"],
        "phase_name": phase.get("name"),
        "phase_type": phase.get("type"),
        "loop_type": phase.get("loop_type"),
        "loop_count": phase.get("loop_count"),
        "steps": steps,
        "produces": produces,
        "consumes": consumes,
        "helper_methods": [],               # ordered helper method names (loop_wrapper only)
        "loop_idx_param": False,            # True for loop_substep helpers
        "set_vars": [],                     # filled by _annotate_contracts
        "available_vars": [],               # filled by _annotate_contracts
    }


def _annotate_contracts(units: list[dict], ir: dict) -> None:
    """Compute each unit's self.* contract:
      set_vars       = produces consumed by some downstream unit OR a phase output
      available_vars = everything produced by upstream units (exposed as self.*)

    Loop wrappers are pure control-flow glue — they carry no self.* state and are
    excluded from the up/downstream scans (the helpers own the contract).
    """
    all_phase_outputs: set = set()
    for p in ir.get("phases", []):
        all_phase_outputs |= set(p.get("outputs", []) or [])

    for u in units:
        if u["kind"] == "loop_wrapper":
            u["set_vars"] = []
            u["available_vars"] = []

    real = [u for u in units if u["kind"] != "loop_wrapper"]
    for i, u in enumerate(real):
        downstream_consumes: set = set()
        for v in real[i + 1:]:
            downstream_consumes |= set(v["consumes"])
        u["set_vars"] = [x for x in u["produces"]
                         if x in downstream_consumes or x in all_phase_outputs]
        u["available_vars"] = _ordered_union(v["produces"] for v in real[:i])


def build_loop_wrapper_method(unit: dict) -> str:
    """Deterministically build the loop wrapper's stepN method (class-body indented).

    The wrapper holds the loop's control flow and delegates each iteration's work to
    the per-sub-step helper methods, in IR order. Count loops use the literal
    loop_count (so the validator's count-literal check passes); condition/unknown
    loops emit a `_LOOP_ITERATIONS = 10  # TODO human-confirm` constant.
    """
    method = unit["method"]
    pid = unit["phase_id"]
    pname = unit.get("phase_name") or pid
    loop_type = unit.get("loop_type")
    loop_count = unit.get("loop_count")
    helpers = unit.get("helper_methods") or []

    lines = [
        f"    def {method}(self) -> None:",
        f'        """Loop {pid} ({pname}) — wrapper. The loop body is decomposed into',
        f"        one helper per IR sub-step (_{_slug(pid)}_*), each called once per",
        f'        iteration. Control flow lives here; sub-step logic lives in the helpers."""',
    ]
    if loop_type == "count" and loop_count is not None:
        lines.append(f"        for loop_idx in range({loop_count}):")
    else:
        lines.append(
            f"        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count "
            f"(loop_type={loop_type!r}; not given by TC)"
        )
        lines.append("        for loop_idx in range(_LOOP_ITERATIONS):")
    if helpers:
        for h in helpers:
            lines.append(f"            self.{h}(loop_idx)")
    else:
        lines.append("            pass  # TODO human-confirm: loop has no sub-steps")
    return "\n".join(lines)


def build_loop_wrapper_section(unit: dict) -> str:
    """Wrap build_loop_wrapper_method in the per-unit methods-file section format so
    assemble._parse_unit_methods reads it like any LLM-produced unit (no grounding —
    the wrapper is pure control-flow glue, so wiki/code refs are NO MATCH)."""
    return (
        "=== WIKI REFS ===\nNO MATCH\n\n"
        "=== CODE REFS ===\nNO MATCH\n\n"
        "=== REVIEW FLAGS ===\n\n"
        "=== EXTRA IMPORTS ===\n\n"
        "=== METHODS ===\n"
        + build_loop_wrapper_method(unit) + "\n"
    )


UNIT_GEN_INSTRUCTIONS = """\
You are a UFS pattern generator. Generate the Python method for ONE unit only,
grounded in TWO sources: the injected llm-wiki references and the gitnexus code graph.

OUTPUT FORMAT — emit these sections IN ORDER (use these EXACT headers).
The headers `=== CODE REFS ===` and `=== REVIEW FLAGS ===` are PARSED BY TOOLING —
do NOT rename, merge, or replace them (e.g. with "=== GROUNDING LOG ==="); doing so
silently blanks the grounding/review report.

=== WIKI REFS ===
<The wiki pages (from the injected "Wiki references" below) you actually used,
 one per line as "path — why". If the injected wiki block says NO MATCH, write: NO MATCH>

=== CODE REFS ===
<The gitnexus query top-5 candidate symbols you used, one per line as
 "path: Symbol (gitnexus rankN)". If gitnexus returns nothing usable, write: NO MATCH>

=== REVIEW FLAGS ===
<Exactly one of these, or empty if both sources matched:
   TODO-REVIEW-NO-WIKI      — wiki had NO MATCH but code refs were found
   TODO-REVIEW-NO-CODE-REF  — wiki matched but gitnexus had no usable code ref
   TODO-REVIEW-BOTH-MISS    — neither source matched>

=== EXTRA IMPORTS ===
<Import lines needed beyond scaffold standard imports. Omit section if none needed.>

=== METHODS ===
<The method definition(s) indented 4 spaces, ready to paste into a class body.>

STANDARD IMPORTS ALREADY IN SCAFFOLD (do NOT repeat):
  import package_root
  from Script import api
  from Script.lib import sdk_lib as lib
  from Script.pattern.pattern_template import UFSTC
  from Script.pattern.pattern_logger import logger
  import Script.api.cmd_seq as ExecuteCMD

STRUCTURE RULES:
- This unit MUST become EXACTLY ONE method. See "STRUCTURE (this unit)" below for the
  exact method name/signature and whether it is a stepN method or a loop helper.
- Name the method EXACTLY as stated. A wrong name = dead code (stepN is auto-run by
  `process()`; a loop helper is called by name from its stepN wrapper).
- Carry forward outputs as self.<var> per the self.* CONTRACT below.
- Do NOT generate class header, pre_process, post_process, or __main__ block.
- You MUST generate the method even if a source is missing (see REVIEW FLAGS). For
  any unresolved API write:
    logger.warning("TODO human-confirm: <what is unresolved>")
    # TODO human-confirm: <symbol or operation that needs verification>
- Reuse helper methods already defined upstream (listed below); do NOT redefine them.

GROUNDING (MANDATORY before writing any API call):
  CODE  → Use the gitnexus MCP server (it has indexed the Script/ codebase):
           call the `query` tool with DOMAIN KEYWORDS to get the top-5 candidate
           symbols; use `context` to confirm a symbol's callers/callees and real
           signature before writing the call. Do NOT assume a naming prefix.
           Script/ layout — pick the right folder:
             - Script/project_api/ : this project's CUSTOMER api — prefer for
                                     customer-specific behaviour.
             - Script/api/         : protocol APIs implemented per the UFS Spec.
             - Script/pattern/      : real existing patterns — copy the calling idiom.
             - Script/lib/          : shared low-level libraries.
           Record the top-5 you relied on in === CODE REFS ===. Namespaces to verify:
           FlagIDN (flags) vs AttributeIDN (attributes) are SEPARATE enums; never mix.
           If gitnexus has no usable hit, do NOT invent an API — flag NO-CODE-REF and
           tag the call # TODO human-confirm.

           ANTI-CONFLATION (this is the #1 cause of broken patterns):
           - Sibling functions in the SAME module routinely have DIFFERENT parameter
             lists. Example: `sequential_write(lun, start_lba, total_size, chunk_size,
             fua, ...)` vs `random_read(cmd_count, min_lun, max_lun, min_lba, max_lba,
             min_size, max_size, need_compare, write_record)`. NEVER copy one
             function's argument names onto another.
           - Call `context` on EACH symbol SEPARATELY and confirm its exact signature
             (params, order, return) before writing the call. One lookup does not
             license a whole family.
           - Above EVERY api./ExecuteCMD./lib. call, paste the confirmed signature as
             a comment:  # sig: <module>.<name>(<params>)  via gitnexus context
             This is a self-check; mismatched calls will be rejected by the validator.
           - Do NOT call any symbol you have not confirmed exists via gitnexus
             `context`. If you cannot confirm it, do not guess — emit
             TODO-REVIEW-NO-CODE-REF and tag the call # TODO human-confirm.
  WIKI  → Use ONLY the injected "Wiki references" block below (RRF top-5 + essence);
           do not free-read the wiki. Conflict overrides shown there WIN
           (Rule 1 CustomerReq>Spec, Rule 2 UserPrompt>ModelDefault — two independent
           rules). Record the pages you used in === WIKI REFS ===.

PROVENANCE:
  Tag every grounded element:  # src[code]: <gitnexus path>:<sym>  or  # src[wiki]: <wiki/path.md>
  If a REVIEW FLAG applies, also put it as an inline comment on the FIRST line of the
  stepN method body (e.g. `# TODO-REVIEW-NO-CODE-REF`) so reviewers can grep it."""


# Direct-Script variant: identical OUTPUT FORMAT, but code grounding is done by
# reading the real Script source (candidates injected below) instead of calling
# the gitnexus MCP server. Selected when PGConfig.grounding_mode == "direct".
UNIT_GEN_INSTRUCTIONS_DIRECT = """\
You are a UFS pattern generator. Generate the Python method for ONE unit only,
grounded in TWO sources: the injected llm-wiki references and the injected Script
code candidates (real symbols retrieved straight from the Script library).

OUTPUT FORMAT — emit these sections IN ORDER (use these EXACT headers).
The headers `=== CODE REFS ===` and `=== REVIEW FLAGS ===` are PARSED BY TOOLING —
do NOT rename, merge, or replace them (e.g. with "=== GROUNDING LOG ==="); doing so
silently blanks the grounding/review report.

=== WIKI REFS ===
<The wiki pages (from the injected "Wiki references" below) you actually used,
 one per line as "path — why". If the injected wiki block says NO MATCH, write: NO MATCH>

=== CODE REFS ===
<The Script symbols you actually used, one per line as
 "path: Symbol — signature". If no candidate is usable, write: NO MATCH>

=== REVIEW FLAGS ===
<Exactly one of these, or empty if both sources matched:
   TODO-REVIEW-NO-WIKI      — wiki had NO MATCH but code refs were found
   TODO-REVIEW-NO-CODE-REF  — wiki matched but no usable Script symbol was found
   TODO-REVIEW-BOTH-MISS    — neither source matched>

=== EXTRA IMPORTS ===
<Import lines needed beyond scaffold standard imports. Omit section if none needed.>

=== METHODS ===
<The method definition(s) indented 4 spaces, ready to paste into a class body.>

STANDARD IMPORTS ALREADY IN SCAFFOLD (do NOT repeat):
  import package_root
  from Script import api
  from Script.lib import sdk_lib as lib
  from Script.pattern.pattern_template import UFSTC
  from Script.pattern.pattern_logger import logger
  import Script.api.cmd_seq as ExecuteCMD

STRUCTURE RULES:
- This unit MUST become EXACTLY ONE method. See "STRUCTURE (this unit)" below for the
  exact method name/signature and whether it is a stepN method or a loop helper.
- Name the method EXACTLY as stated. A wrong name = dead code (stepN is auto-run by
  `process()`; a loop helper is called by name from its stepN wrapper).
- Carry forward outputs as self.<var> per the self.* CONTRACT below.
- Do NOT generate class header, pre_process, post_process, or __main__ block.
- You MUST generate the method even if a source is missing (see REVIEW FLAGS). For
  any unresolved API write:
    logger.warning("TODO human-confirm: <what is unresolved>")
    # TODO human-confirm: <symbol or operation that needs verification>
- Reuse helper methods already defined upstream (listed below); do NOT redefine them.

GROUNDING (MANDATORY before writing any API call):
  CODE  → Do NOT use gitnexus. Ground on the "## Code candidates" block injected below
           (top-N real Script symbols with file:line + signature, retrieved directly
           from the Script library). Then OPEN the real source to confirm before use:
             - Use Read on the candidate's file:line, or Grep/Glob over the Script tree
               (GitNexusMCP/Script/), to read the actual `def` and its exact signature.
             - Script/ layout — pick the right folder:
                 - Script/project_api/ : this project's CUSTOMER api — prefer for
                                         customer-specific behaviour.
                 - Script/api/         : protocol APIs implemented per the UFS Spec.
                 - Script/pattern/sample_code/ : canonical calling idioms — copy them.
                 - Script/lib/          : shared low-level libraries.
           Record the symbols you relied on in === CODE REFS ===. Namespaces to verify:
           FlagIDN (flags) vs AttributeIDN (attributes) are SEPARATE enums; never mix.
           If no candidate fits and reading the tree finds nothing usable, do NOT invent
           an API — flag NO-CODE-REF and tag the call # TODO human-confirm.

           ANTI-CONFLATION (this is the #1 cause of broken patterns):
           - Sibling functions in the SAME module routinely have DIFFERENT parameter
             lists. Example: `sequential_write(lun, start_lba, total_size, chunk_size,
             fua, ...)` vs `random_read(cmd_count, min_lun, max_lun, min_lba, max_lba,
             min_size, max_size, need_compare, write_record)`. NEVER copy one
             function's argument names onto another.
           - READ the source of EACH symbol SEPARATELY and confirm its exact signature
             (params, order, return) before writing the call. One lookup does not
             license a whole family.
           - Above EVERY api./ExecuteCMD./lib. call, paste the confirmed signature as
             a comment:  # sig: <module>.<name>(<params>)  via reading the source file
             This is a self-check; mismatched calls will be rejected by the validator.
           - Do NOT call any symbol you have not confirmed exists by reading its source.
             If you cannot confirm it, do not guess — emit TODO-REVIEW-NO-CODE-REF and
             tag the call # TODO human-confirm.
  WIKI  → Use ONLY the injected "Wiki references" block below (RRF top-5 + essence);
           do not free-read the wiki. Conflict overrides shown there WIN
           (Rule 1 CustomerReq>Spec, Rule 2 UserPrompt>ModelDefault — two independent
           rules). Record the pages you used in === WIKI REFS ===.

PROVENANCE:
  Tag every grounded element:  # src[code]: <Script path>:<sym>  or  # src[wiki]: <wiki/path.md>
  If a REVIEW FLAG applies, also put it as an inline comment on the FIRST line of the
  stepN method body (e.g. `# TODO-REVIEW-NO-CODE-REF`) so reviewers can grep it."""


def build_one_unit_prompt(
    ir: dict,
    unit: dict,
    upstream_methods: str = "",
    upstream_code_refs: list | None = None,
    upstream_helpers: list | None = None,
    wiki_essence: str = "",
    wiki_top: list | None = None,
    wiki_has_match: bool = True,
    grounding_mode: str = "gitnexus",
    code_candidates: list | None = None,
    defaults: str = "",
) -> str:
    """Build the LLM generation prompt for a single unit (one step, or one loop).

    wiki_essence / wiki_top: the deterministically retrieved llm-wiki RRF top-5 and
    extractive essence for this unit (injected — the agent does not free-read wiki).
    wiki_has_match=False signals the agent to flag TODO-REVIEW-NO-WIKI / -BOTH-MISS.

    grounding_mode="direct" swaps the gitnexus grounding instructions for the
    Script-direct ones and injects `code_candidates` (top-N real symbols retrieved
    from the Script library) instead of asking the model to call the MCP server.
    """
    direct = grounding_mode == "direct"
    instructions = UNIT_GEN_INSTRUCTIONS_DIRECT if direct else UNIT_GEN_INSTRUCTIONS
    kind = unit["kind"]
    if kind == "loop_wrapper":
        raise ValueError(
            f"loop_wrapper unit {unit.get('method')!r} is generated deterministically "
            "(build_loop_wrapper_section) — it has no LLM prompt."
        )
    if kind == "loop":
        # Legacy whole-loop unit (back-compat with old 1_units.json snapshots).
        type_desc = "type=loop"
        if unit.get("loop_type"):
            type_desc += f", loop_type={unit['loop_type']}"
        if unit.get("loop_count"):
            type_desc += f", loop_count={unit['loop_count']}"
        method_note = (f"{unit['method']}  (ONE method — entire loop body inlined, "
                       f"all sub-steps inside one for/while loop)")
        unit_desc = (f"Unit {unit['index']} — LOOP phase {unit['phase_id']} "
                     f"({unit['phase_name']}) [{type_desc}]")
        structure_note = (
            "STRUCTURE (this unit): emit EXACTLY ONE method named stepN; its body is the "
            "for/while loop with ALL sub-steps inlined. do NOT create loopN() helpers. "
            "`process()` only auto-runs stepN — any other name = dead code."
        )
    elif kind == "loop_substep":
        s = unit["steps"][0]
        method_note = (f"{unit['method']}(self, loop_idx: int)  (ONE helper method — this single "
                       f"sub-step of loop {unit['phase_id']}, called once per iteration by the wrapper)")
        unit_desc = (f"Unit {unit['index']} — LOOP sub-step {s['step_id']} "
                     f"({s.get('name', '')}) of loop {unit['phase_id']} ({unit['phase_name']})")
        structure_note = (
            f"STRUCTURE (this unit): emit EXACTLY ONE method named `{unit['method']}` with "
            "signature `(self, loop_idx: int) -> None`. It is CALLED BY the loop wrapper once "
            "per iteration — do NOT write the for/while loop yourself, and do NOT name it stepN. "
            "This body runs every iteration; any self.* you set is OVERWRITTEN each iteration "
            "(use self.* only to hand a value to a LATER sub-step in the SAME iteration). "
            "`loop_idx` is the 0-based iteration index (may be unused)."
        )
    else:  # step
        s = unit["steps"][0]
        method_note = f"{unit['method']}  (ONE method for this single step)"
        unit_desc = (f"Unit {unit['index']} — step {s['step_id']} "
                     f"({s.get('name', '')}) of phase {unit['phase_id']} ({unit['phase_name']})")
        structure_note = (
            "STRUCTURE (this unit): emit EXACTLY ONE method named stepN (exactly as 'Method name' "
            "states). `process()` auto-runs stepN methods in order — any other name = dead code."
        )

    parts = [
        instructions,
        f"Pattern: {ir.get('pattern_id')} — {ir.get('title', '')}",
        unit_desc,
        f"Method name: {method_note}",
        structure_note,
    ]

    # self.* contract
    if unit["set_vars"]:
        parts.append(
            "self.* CONTRACT — you MUST set these (consumed downstream): "
            + ", ".join(f"self.{v}" for v in unit["set_vars"])
        )
    if unit["available_vars"]:
        parts.append(
            "self.* available from upstream units (already set; just read): "
            + ", ".join(f"self.{v}" for v in unit["available_vars"])
        )
    if unit["consumes"]:
        parts.append(
            "This unit needs (should already be self.* from upstream): "
            + ", ".join(unit["consumes"])
        )

    parts.append(
        "## Step(s) in this unit\n" + json.dumps(unit["steps"], ensure_ascii=False, indent=2)
    )

    # Injected wiki references (RRF top-5 + extractive essence). The agent grounds
    # domain facts here instead of free-reading the wiki.
    if wiki_has_match and (wiki_essence.strip() or wiki_top):
        block = ["## Wiki references (RRF top-5) — ground domain facts here; conflict overrides WIN"]
        if wiki_top:
            block.append("top-5:\n" + "\n".join(f"- {r}" for r in wiki_top))
        if wiki_essence.strip():
            block.append(wiki_essence.strip())
        parts.append("\n".join(block))
    else:
        parts.append(
            "## Wiki references: NO MATCH\n"
            "No relevant wiki page for this unit. You MUST emit TODO-REVIEW-NO-WIKI in "
            "=== REVIEW FLAGS === (or TODO-REVIEW-BOTH-MISS if the code source also returns nothing)."
        )

    # Direct-Script grounding: inject the top-N candidate symbols (retrieved from the
    # Script library) so the model grounds on real symbols and confirms by reading source.
    if direct:
        if code_candidates:
            parts.append(
                "## Code candidates (top-5) — real Script symbols; CONFIRM signatures by "
                "reading the file (Read/Grep over GitNexusMCP/Script/)\n"
                + "\n".join(f"- {c}" for c in code_candidates)
            )
        else:
            parts.append(
                "## Code candidates: NO MATCH\n"
                "No candidate symbol retrieved for this unit. Grep GitNexusMCP/Script/ "
                "directly; if nothing fits, emit TODO-REVIEW-NO-CODE-REF (or "
                "TODO-REVIEW-BOTH-MISS if wiki also missed) and tag calls # TODO human-confirm."
            )

    # Project defaults (default.md) — ALWAYS injected (not top-N): the resolved
    # UserPrompt>ModelDefault policy to apply when the TC omits a detail. This is
    # what stops e.g. a hardcoded lun=0 against the "MaxCapacity Enabled LUN" rule.
    if defaults.strip():
        parts.append(
            "## Project defaults (default.md) — when the TC OMITS a detail, FOLLOW these "
            "(UserPrompt > ModelDefault). Do NOT hardcode a value these resolve (e.g. lun=0). "
            "Tag any use as `# src[wiki]: default.md`.\n" + defaults.strip())

    # Upstream continuity — embed already-generated methods so style/naming/helpers
    # stay consistent and missed dependencies can still be wired via self.*.
    if upstream_methods.strip():
        parts.append(
            "## Already-generated upstream methods — STAY CONSISTENT\n"
            "(These are already written. Continue stepN numbering, match their import/"
            "logger style, reuse their helpers, and wire to the self.* they set. "
            "Do NOT redefine helpers or re-`def` these methods.)\n\n"
            + upstream_methods.strip()
        )
    if upstream_code_refs:
        reuse_note = ("reuse — no need to re-read the source" if direct
                      else "reuse — no need to re-query gitnexus")
        parts.append(
            f"### Code refs already used upstream ({reuse_note})\n"
            + "\n".join(upstream_code_refs)
        )
    if upstream_helpers:
        parts.append(
            "### Helper methods already defined upstream (reuse, do NOT redefine)\n"
            + "\n".join(upstream_helpers)
        )

    parts.append(
        "## Full IR (for reference)\n" + json.dumps(ir, ensure_ascii=False, indent=2)
    )

    return "\n\n".join(parts)


def extract_helper_signatures(methods_text: str) -> list[str]:
    """Pull non-step helper method signatures (e.g. `def _parse_xxx(self, ...)`)
    from an assembled methods block, so downstream units can reuse them."""
    sigs = []
    for m in _re.finditer(r"^\s*(def\s+(\w+)\s*\([^)]*\)[^:]*):", methods_text, _re.MULTILINE):
        name = m.group(2)
        if not _re.fullmatch(r"step\d+", name):
            sigs.append(m.group(1).strip())
    return sigs
