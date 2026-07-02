"""Deterministic preparation for pattern generation. Walks the IR into ordered
generation units (one step = one unit; a loop phase = one unit) and builds the
class scaffold plus per-unit generation prompts. Prompts are built LAZILY: a
downstream unit's prompt embeds the already-generated upstream unit methods
(continuity), so it can only be built once those upstream methods exist.
No LLM, no code retrieval — grounding is done on demand by the generating model."""
import json
from pathlib import Path

from pattern_generator.config import PGConfig
from pattern_generator.run_logger import RunDir
from pattern_generator.assemble import _parse_unit_methods
from pattern_generator.stepwise import (
    generation_units,
    build_scaffold,
    build_one_unit_prompt,
    build_loop_wrapper_section,
    extract_helper_signatures,
)
from wiki_retrieval.retrieve import retrieve
from wiki_retrieval.essence import build_essence, format_top_refs
from wiki_retrieval.defaults import load_overrides, modeldefault_block, retrieve_modeldefault


def _unit_prompt_filename(unit: dict) -> str:
    return f"unit_{unit['index']:02d}_{unit['unit_id']}_prompt.txt"


def _unit_methods_filename(unit: dict) -> str:
    """Methods-file name for a unit. Loop wrappers carry a `_wrapper` token so they
    are visually distinct, but still match the assemble glob `unit_*_methods.py`."""
    if unit["kind"] == "loop_wrapper":
        return f"unit_{unit['index']:02d}_{unit['unit_id']}_wrapper_methods.py"
    return f"unit_{unit['index']:02d}_{unit['unit_id']}_methods.py"


def _unit_query(unit: dict) -> str:
    """Build the wiki retrieval query for a unit from its step cmd/idn/name."""
    terms: list = []
    for step in unit.get("steps", []):
        for key in ("scsi_cmd", "ufs_query", "name", "idn"):
            val = step.get(key)
            if val:
                terms.append(str(val))
    return " ".join(terms)


def _unit_code_query(unit: dict) -> str:
    """Query for CODE / api-fact retrieval — the base query PLUS the unit's data-flow
    variable names (produces/consumes/set_vars), underscore-split into intent words.

    Protocol tokens alone ('WRITE(10)', 'POR') retrieve the WRONG abstraction layer
    (low-level CDB classes / power_on), because they are not the framework's API
    vocabulary. The data-flow var names bridge the gap: 'write_record_p1' -> 'write
    record' surfaces get_empty_write_record/random_write; 'wb_support_info' -> 'wb
    support' surfaces get_extended_ufs_features_support (and triggers the WB-support
    canonical_facts idiom, whose English trigger the Chinese step name misses). This
    is the FEED-only fix; the wiki query (_unit_query) is intentionally left alone.
    """
    base = _unit_query(unit)
    var_tokens: list = []
    for key in ("produces", "consumes", "set_vars"):
        for v in unit.get(key, []) or []:
            var_tokens.append(str(v).replace("_", " "))
    extra = " ".join(dict.fromkeys(var_tokens))  # dedupe, preserve order
    return (base + (" " + extra if extra else "")).strip()


def _unit_wiki(unit: dict, wiki_path) -> dict:
    """Retrieve the wiki essence + top-5 for a unit (deterministic injection)."""
    query = _unit_query(unit).strip()
    if not query:
        return {"essence": "", "top": [], "has_match": False}
    # Generation is per-unit (×N, token-sensitive) -> top-3, not top-5 (few + exact
    # signatures beats many candidate names; see api_grounding's injected facts).
    result = retrieve(query, wiki_root=wiki_path, top_n=3, n_entity=3)
    return {
        "essence": build_essence(result, max_entities=3),
        "top": format_top_refs(result),
        "has_match": result.has_match,
    }


def _unit_defaults(unit: dict, wiki_path):
    """Per-unit defaults block: §1-§3 overrides (always) + the single most relevant
    ModelDefault topic (retrieved). Keeps unit prompts small (~4KB vs ~30KB) while
    the absence-triggered overrides (LUN etc.) are never missed.

    Returns (text, modeldefault_stem | None) so the caller can record deterministically
    WHAT was offered to this unit (see _record_defaults)."""
    query = _unit_query(unit)
    overrides = load_overrides(wiki_path)
    hits = retrieve_modeldefault(query, wiki_path, k=1)
    stem = hits[0][0] if hits else None
    md = modeldefault_block(query, wiki_path, k=1)  # cached retrieve
    return overrides + ("\n\n" + md if md else ""), stem


def _record_defaults(run_dir, unit: dict, stem, init: bool = False) -> None:
    """Append one deterministic 'defaults OFFERED to this unit' line to
    <run_dir>/defaults_debug.md. (What the model actually USED is its own
    `# src[wiki]` self-report, aggregated into retrieval_debug.md.)"""
    path = Path(run_dir) / "defaults_debug.md"
    if init or not path.exists():
        path.write_text(
            "# Defaults offered per unit — DETERMINISTIC (what was INJECTED)\n\n"
            "> §1-§3 overrides (UserPrompt/CustomerReq) are ALWAYS injected.\n"
            "> §4 ModelDefault base is retrieved per step (top-1 topic).\n"
            "> What the model actually USED = its `# src[wiki]` tags (see retrieval_debug.md).\n\n",
            encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- unit {unit['index']:02d} ({unit.get('unit_id')}): "
                 f"overrides=always; modeldefault={stem or 'NONE'}\n")


def _unit_code(unit: dict, script_root, k: int = 3) -> list:
    """Top-k candidate Script symbols for a unit (direct-grounding injection).

    Mirrors _unit_wiki: builds the same cmd/idn/name query and asks the
    code_retrieval index (no gitnexus) for real symbols to inject as candidates.
    """
    from code_retrieval.retrieve import retrieve_code
    query = _unit_code_query(unit).strip()
    if not query:
        return []
    return [r.render() for r in retrieve_code(query, script_root, k=k)]


def _unit_api_facts(unit: dict, script_root, version=None, k: int = 5) -> list:
    """Phase B: deterministic exact-signature + enum facts for this unit (both modes).

    Resolve the unit's likely symbols (same code index as _unit_code) and look up
    their EXACT signatures + relevant enum members from the api_grounding AST index
    — the same index the validator checks against. Injected so the model copies the
    real form instead of guessing. Empty if script_root isn't a Script library.

    The candidate list is deterministically refined by capability_resolver:
      * version_gate DROPS a candidate whose return struct is unavailable on the target
        UFS `version` (e.g. get_extended_write_booster_support = 4.1-only on a 3.1 run) —
        so the wrong sibling can't be copied;
      * the accessors a canonical idiom names are FORCE-FED (prepended) so the CORRECT
        accessor's real signature + struct fields (incl u8_write_booster) are injected as
        a concrete anchor, not just idiom prose. This is the fix for the Hermes WB bug.
    The remaining symbols stay HEURISTIC (ride the mode-aware authority block)."""
    from pattern_generator.api_grounding import api_facts, _cached_index
    from pattern_generator.capability_resolver import canonical_symbols, version_gate
    from code_retrieval.retrieve import retrieve_code
    query = _unit_code_query(unit).strip()
    if not query:
        return []
    try:
        names = [r.doc.name for r in retrieve_code(query, script_root, k=k)]
    except Exception:
        names = []
    index = _cached_index(str(script_root))
    if index and version:
        names, _dropped = version_gate(index, names, version)
    # Force-feed the canonical idiom's accessor(s) so their real fields anchor the model.
    canon = canonical_symbols(_unit_canonical(unit))
    names = list(dict.fromkeys(canon + names))
    return api_facts(script_root, names, query)


def _unit_canonical(unit: dict) -> list:
    """Canonical-idiom imperative facts for this unit (semantic_checks.canonical_facts).

    The PREVENT half of ENFORCED gate rules → AUTHORITATIVE, kept separate from the
    heuristic api_facts so the mode-aware demotion (gitnexus cross-check) never weakens
    an enforced idiom. Triggered off the enriched code query (so the var-name vocabulary,
    e.g. 'wb support', fires the rule even when the step name is Chinese)."""
    from pattern_generator.semantic_checks import canonical_facts
    return canonical_facts(_unit_code_query(unit))


def _unit_procedures(unit: dict) -> list:
    """Procedure-idiom guards for this unit (procedure_idioms.match_procedures) — fired off
    the data-flow-enriched query so var names like 'test_lun'/'max_capacity' trigger them."""
    from pattern_generator.procedure_idioms import match_procedures
    return match_procedures(_unit_code_query(unit))


def _target_version(ir: dict, config: PGConfig) -> str | None:
    """Resolved target UFS version for this run: TC frontmatter `ufs_version` > wiki/target.md.

    Threaded into every unit prompt (and, later, the resolver/validator version gate) so a
    version-unavailable API (e.g. 4.1-only get_extended_write_booster_support) is excludable
    deterministically instead of guessed."""
    from pattern_generator.ufs_version import resolve
    return resolve(ir, config.wiki_path)


def _resolve_grounding_mode(run_dir: Path, config: PGConfig) -> str:
    """Grounding mode for a downstream unit: the run's persisted mode (written by
    prepare_pattern) wins, since prepare-unit is a separate CLI call. A non-default
    config value still overrides (explicit --grounding on prepare-unit)."""
    if config.grounding_mode != "gitnexus":
        return config.grounding_mode
    meta = run_dir / "_run_meta.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text(encoding="utf-8")).get("grounding_mode", "gitnexus")
        except (OSError, ValueError):
            pass
    return "gitnexus"


def _gather_upstream(run_dir: Path, target_index: int) -> tuple[str, list, list]:
    """Collect already-generated upstream unit methods for continuity.

    Returns (methods_text, code_ref_lines, helper_signatures) aggregated over all
    unit_*_methods.py whose NN prefix is < target_index (lexicographic NN = order).
    """
    methods_blocks: list = []
    code_refs: list = []
    helpers: list = []
    for f in sorted(run_dir.glob("unit_*_methods.py")):
        try:
            nn = int(f.name.split("_", 2)[1])
        except (IndexError, ValueError):
            continue
        if nn >= target_index:
            continue
        u = _parse_unit_methods(f.read_text(encoding="utf-8"))
        if u.methods:
            methods_blocks.append(u.methods)
            helpers.extend(extract_helper_signatures(u.methods))
        code_refs.extend(r for r in u.code_refs if "NO MATCH" not in r.upper())
    code_refs = list(dict.fromkeys(code_refs))
    helpers = list(dict.fromkeys(helpers))
    return "\n\n".join(methods_blocks), code_refs, helpers


def _write_ir_lint(run, ir: dict) -> list:
    """Lever #4: deterministically flag IR steps whose protocol path contradicts a
    canonical idiom (report-only) -> <run>/ir_lint.md. Generation-prompt canonical
    blocks then OVERRIDE the contradiction; this surfaces the root cause to a human."""
    from pattern_generator.semantic_checks import check_ir_protocol_paths
    findings = check_ir_protocol_paths(ir)
    lines = ["# IR protocol-path lint (canonical-idiom contradictions — report-only)\n"]
    if findings:
        lines.append("> The generation prompt's canonical-idiom block OVERRIDES these; "
                     "fix the IR/TC upstream to remove the contradiction.\n")
        for f in findings:
            lines.append(f"- [{f['kind']}] {f['detail']}  (suggest: {f.get('suggestion','')})")
    else:
        lines.append("- (no contradictions)")
    run.write_text("ir_lint.md", "\n".join(lines) + "\n")
    return findings


def prepare_pattern(ir_path, config: PGConfig | None = None) -> dict:
    """Step 4: write scaffold.py + 1_units.json + the FIRST unit prompt.

    Downstream unit prompts are produced one at a time by prepare_unit() after
    each upstream unit's methods file is generated.
    """
    config = config or PGConfig()
    ir = json.loads(Path(ir_path).read_text(encoding="utf-8"))
    pattern_id = ir["pattern_id"]

    units = generation_units(ir)
    scaffold = build_scaffold(ir)

    run = RunDir(config.generated_dir, pattern_id)
    run.write_json("1_units.json", units)
    run.write_text("scaffold.py", scaffold)
    _write_ir_lint(run, ir)

    # Persist the grounding mode so downstream prepare-unit calls (separate CLI
    # invocations) reuse it without re-passing --grounding. Gitnexus runs (default)
    # also record it for transparency.
    run.write_json("_run_meta.json", {
        "grounding_mode": config.grounding_mode,
        "script_root": str(config.script_root),
    })

    # Make the run dir self-contained so prepare_unit can find the IR later,
    # regardless of where the source IR file lived. Keep the *-ir.json suffix
    # so prepare_unit's glob matches.
    ir_name = Path(ir_path).name
    if not ir_name.endswith("-ir.json"):
        ir_name = f"{pattern_id.lower()}-ir.json"
    run.write_json(ir_name, ir)

    # Loop wrappers are deterministic control-flow glue: write their methods files
    # up front so the assemble glob picks them up and they never need an LLM prompt.
    for u in units:
        if u["kind"] == "loop_wrapper":
            run.write_text(_unit_methods_filename(u), build_loop_wrapper_section(u))

    # Only the first PROMPTABLE unit can be built up-front (no upstream context).
    # Skip any leading deterministic wrapper.
    first_prompt_file = None
    first_unit = next((u for u in units if u["kind"] != "loop_wrapper"), None)
    if first_unit is not None:
        wiki = _unit_wiki(first_unit, config.wiki_path)
        code_candidates = (_unit_code(first_unit, config.script_root)
                           if config.grounding_mode == "direct" else None)
        facts = _unit_api_facts(first_unit, config.script_root, version=_target_version(ir, config))
        canonical = _unit_canonical(first_unit)
        defaults_text, md_stem = _unit_defaults(first_unit, config.wiki_path)
        prompt = build_one_unit_prompt(
            ir, first_unit,
            wiki_essence=wiki["essence"], wiki_top=wiki["top"],
            wiki_has_match=wiki["has_match"],
            grounding_mode=config.grounding_mode,
            code_candidates=code_candidates,
            api_facts=facts,
            canonical_facts=canonical,
            defaults=defaults_text,
            ufs_version=_target_version(ir, config),
            procedures=_unit_procedures(first_unit),
        )
        first_prompt_file = _unit_prompt_filename(first_unit)
        run.write_text(first_prompt_file, prompt)
        _record_defaults(run.path, first_unit, md_stem, init=True)

    return {
        "run_dir": str(run.path),
        "units": units,
        "unit_count": len(units),
        "scaffold": scaffold,
        "first_prompt_file": first_prompt_file,
    }


def prepare_unit(run_dir, unit_index: int, config: PGConfig | None = None) -> dict:
    """Step 4b: build the prompt for unit N, embedding upstream unit methods.

    Requires every upstream unit (1..N-1) to already have its *_methods.py file.
    """
    run_dir = Path(run_dir)
    units = json.loads((run_dir / "1_units.json").read_text(encoding="utf-8"))
    if unit_index < 1 or unit_index > len(units):
        raise ValueError(f"unit_index {unit_index} out of range 1..{len(units)}")

    unit = units[unit_index - 1]

    # Loop wrappers are deterministic — (idempotently) (re)write the methods file and
    # skip; there is no LLM prompt for a wrapper.
    if unit["kind"] == "loop_wrapper":
        (run_dir / _unit_methods_filename(unit)).write_text(
            build_loop_wrapper_section(unit), encoding="utf-8")
        return {
            "run_dir": str(run_dir),
            "unit_index": unit_index,
            "prompt_file": None,
            "skipped": True,
            "unit_count": len(units),
        }

    ir_files = list(run_dir.glob("*-ir.json"))
    if not ir_files:
        raise FileNotFoundError(f"No *-ir.json found in {run_dir}")
    ir = json.loads(ir_files[0].read_text(encoding="utf-8"))

    # Verify all upstream method files exist (fail fast on a gap).
    existing = {int(f.name.split("_", 2)[1]) for f in run_dir.glob("unit_*_methods.py")}
    missing = [u["index"] for u in units[: unit_index - 1] if u["index"] not in existing]
    if missing:
        raise FileNotFoundError(
            f"Cannot prepare unit {unit_index}: upstream unit methods missing for "
            f"{missing}. Generate them first (read their prompt → write "
            f"unit_NN_<id>_methods.py)."
        )

    methods_text, code_refs, helpers = _gather_upstream(run_dir, unit_index)
    cfg = config or PGConfig()

    # Per-unit micro-gate: run the SAME deterministic checks the final gate runs, but on
    # the immediately-upstream unit, and surface any failures at the top of THIS prompt —
    # so a unit's bug is fixed where it was made (self-heals even if the workflow forgot
    # to run `validate-unit`). See pattern_generator.unit_gate.
    upstream_gate = ""
    if unit_index > 1:
        prev = units[unit_index - 2]
        prev_mf = run_dir / _unit_methods_filename(prev)
        if prev.get("kind") != "loop_wrapper" and prev_mf.is_file():
            from pattern_generator.assemble import _parse_unit_methods
            from pattern_generator.unit_gate import check_unit, unit_findings
            pu = _parse_unit_methods(prev_mf.read_text(encoding="utf-8", errors="ignore"))
            # A unit may legitimately use a name imported by an EARLIER unit (assemble
            # merges all EXTRA IMPORTS) — give the bare-name check the upstream union.
            upstream_imports: list = list(pu.extra_imports)
            for f in sorted(run_dir.glob("unit_*_methods.py")):
                try:
                    nn = int(f.name.split("_", 2)[1])
                except (IndexError, ValueError):
                    continue
                if nn < unit_index and f != prev_mf:
                    upstream_imports.extend(_parse_unit_methods(
                        f.read_text(encoding="utf-8", errors="ignore")).extra_imports)
            findings = unit_findings(check_unit(
                pu.methods, code_refs=pu.code_refs, script_root=cfg.script_root,
                expected_methods=[prev["method"]] if prev.get("method") else None,
                extra_imports=upstream_imports,
                loop_idx_required=bool(prev.get("loop_idx_param"))))
            if findings:
                upstream_gate = (
                    f"## FIX UPSTREAM UNIT FIRST — {prev_mf.name} failed the per-unit gate\n"
                    "Correct that file (deterministic errors below) before generating this "
                    "unit, which builds on it:\n"
                    + "\n".join(f"- {f}" for f in findings) + "\n\n"
                )

    mode = _resolve_grounding_mode(run_dir, cfg)
    wiki = _unit_wiki(unit, cfg.wiki_path)
    code_candidates = (_unit_code(unit, cfg.script_root) if mode == "direct" else None)
    facts = _unit_api_facts(unit, cfg.script_root, version=_target_version(ir, cfg))
    canonical = _unit_canonical(unit)
    defaults_text, md_stem = _unit_defaults(unit, cfg.wiki_path)
    prompt = build_one_unit_prompt(
        ir, unit,
        upstream_methods=methods_text,
        upstream_code_refs=code_refs,
        upstream_helpers=helpers,
        wiki_essence=wiki["essence"], wiki_top=wiki["top"],
        wiki_has_match=wiki["has_match"],
        grounding_mode=mode,
        code_candidates=code_candidates,
        api_facts=facts,
        canonical_facts=canonical,
        defaults=defaults_text,
        ufs_version=_target_version(ir, cfg),
        procedures=_unit_procedures(unit),
    )
    fname = _unit_prompt_filename(unit)
    (run_dir / fname).write_text(upstream_gate + prompt, encoding="utf-8")
    _record_defaults(run_dir, unit, md_stem)

    return {
        "run_dir": str(run_dir),
        "unit_index": unit_index,
        "prompt_file": fname,
        "unit_count": len(units),
    }
