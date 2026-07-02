"""Assemble scaffold.py + per-unit method files into a final pattern .py.

Per-unit method files follow this output format (sections in order):
    === WIKI REFS ===
    <wiki pages used, one per line; or "NO MATCH">
    === CODE REFS ===
    <gitnexus query top-5 used, one per line; or "NO MATCH">
    === REVIEW FLAGS ===
    <TODO-REVIEW-NO-WIKI | -NO-CODE-REF | -BOTH-MISS, or empty>
    === EXTRA IMPORTS ===
    from x import y          # optional; omit section if none needed
    === METHODS ===
        def stepN(self) -> None:
            ...
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pattern_generator.api_grounding import build_script_index
from pattern_generator.unit_gate import check_unit

EXTRA_IMPORTS_MARKER = "# @@EXTRA_IMPORTS@@"
METHODS_MARKER = "    # @@PHASE_METHODS@@"

# The scaffold's deterministic pre/post_process stubs (see stepwise.build_scaffold).
# When a unit PROVIDES one of these methods, the stub is stripped so the unit's
# version REPLACES it instead of duplicating the def (Python keeps the last def
# silently; the validator's duplicate check backstops any other collision).
_SCAFFOLD_STUB_RE = {
    "pre_process": re.compile(
        r"    def pre_process\(self\) -> None:\n"
        r"        pass  # TODO human-confirm[^\n]*\n\n?"),
    "post_process": re.compile(
        r"    def post_process\(self\) -> None:\n"
        r"        pass  # TODO human-confirm[^\n]*\n\n?"),
}

REVIEW_FLAGS = ("TODO-REVIEW-NO-WIKI", "TODO-REVIEW-NO-CODE-REF", "TODO-REVIEW-BOTH-MISS")

# Detects a real namespace call (api./ExecuteCMD./lib.<name>( ) in a methods block.
_API_CALL_RE = re.compile(r"\b(?:api|ExecuteCMD|lib)\.\w+\s*\(")


def _derive_review_flags(u: "UnitMethods") -> list:
    """Derive review flags from CONTENT (not the agent's self-report).

    A NO-CODE-REF / BOTH-MISS flag is only meaningful when the unit actually
    issues an API call — pure-Python steps (e.g. a delay) are not flagged."""
    has_api = bool(_API_CALL_RE.search(u.methods or ""))
    wiki_missing = u.is_no_match(u.wiki_refs)
    code_missing = u.is_no_match(u.code_refs)
    if has_api and code_missing and wiki_missing:
        return ["TODO-REVIEW-BOTH-MISS"]
    if has_api and code_missing:
        return ["TODO-REVIEW-NO-CODE-REF"]
    if wiki_missing and not code_missing:
        return ["TODO-REVIEW-NO-WIKI"]
    return []

_SECTION_HEADERS = {
    "=== WIKI REFS ===": "wiki",
    "=== CODE REFS ===": "code",
    "=== REVIEW FLAGS ===": "flags",
    "=== EXTRA IMPORTS ===": "imports",
    "=== METHODS ===": "methods",
    # legacy header still tolerated (treated as code refs)
    "=== GROUNDING LOG ===": "code",
}


@dataclass
class UnitMethods:
    wiki_refs: list = field(default_factory=list)
    code_refs: list = field(default_factory=list)
    review_flags: list = field(default_factory=list)
    extra_imports: list = field(default_factory=list)
    methods: str = ""

    def is_no_match(self, refs: list) -> bool:
        return (not refs) or all("NO MATCH" in r.upper() for r in refs)


def _parse_unit_methods(text: str) -> UnitMethods:
    """Parse a unit methods file into its structured sections."""
    buckets: dict = {"wiki": [], "code": [], "flags": [], "imports": [], "methods": []}
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in _SECTION_HEADERS:
            section = _SECTION_HEADERS[stripped]
            continue
        if section is None:
            continue
        if section == "methods":
            buckets["methods"].append(line.rstrip())
        elif section == "imports":
            if stripped and not stripped.startswith("#"):
                buckets["imports"].append(line.rstrip())
        elif section == "flags":
            for flag in REVIEW_FLAGS:
                if flag in stripped:
                    buckets["flags"].append(flag)
        else:  # wiki / code
            if not stripped:
                continue
            # Tolerate the legacy "=== GROUNDING LOG ===" style where every ref
            # line is a "# ..." comment — strip the comment marker and keep the
            # content. (Dropping "#" lines is what silently blanked units 3-7.)
            content = stripped.lstrip("#").strip() if stripped.startswith("#") else stripped
            if content:
                buckets[section].append(content.lstrip("- ").rstrip())

    m = buckets["methods"]
    while m and not m[0].strip():
        m.pop(0)
    while m and not m[-1].strip():
        m.pop()
    return UnitMethods(
        wiki_refs=buckets["wiki"], code_refs=buckets["code"],
        review_flags=buckets["flags"], extra_imports=buckets["imports"],
        methods="\n".join(m),
    )


# Backward-compatible tuple shim used by prepare._gather_upstream.
def _parse_phase_methods(text: str) -> tuple:
    """(legacy shape) Returns (code_ref_lines, extra_import_lines, methods_text)."""
    u = _parse_unit_methods(text)
    return u.code_refs, u.extra_imports, u.methods


def assemble_pattern(run_dir, pattern_name: str, script_root=None, output_dir=None) -> str:
    """Combine scaffold.py + unit_*_methods.py into {pattern_name}.py.

    Reads  : scaffold.py, unit_*_methods.py (from run_dir; lexicographic NN = order)
    Writes : {pattern_name}.py  -> `output_dir` (default: run_dir.parent, i.e. the
                                    generated/ base, so the .py sits next to real
                                    patterns for mypy/indexing)
             retrieval_debug.md -> run_dir (a by-product, stays in the subfolder)
    Returns: assembled source string

    If `script_root` is given and resolves to a Script library, each unit's
    methods are run through the api-grounding reality check and any unknown
    symbols / bad signatures are surfaced per unit in retrieval_debug.md.
    """
    run_dir = Path(run_dir)
    main_dir = Path(output_dir) if output_dir is not None else run_dir.parent
    main_dir.mkdir(parents=True, exist_ok=True)
    scaffold = (run_dir / "scaffold.py").read_text(encoding="utf-8")

    method_files = sorted(run_dir.glob("unit_*_methods.py"))
    if not method_files:
        raise FileNotFoundError(
            f"No unit_*_methods.py files found in {run_dir}. "
            "Complete the per-unit LLM steps first."
        )

    parsed: list = []           # (filename, UnitMethods)
    all_extra_imports: list = []
    all_methods: list = []
    for f in method_files:
        u = _parse_unit_methods(f.read_text(encoding="utf-8"))
        parsed.append((f.name, u))
        all_extra_imports.extend(u.extra_imports)
        if u.methods:
            all_methods.append(u.methods)

    seen: set = set()
    deduped_imports: list = []
    for line in all_extra_imports:
        if line not in seen:
            seen.add(line)
            deduped_imports.append(line)

    merged_methods = "\n\n".join(all_methods)
    # A unit that provides pre_process/post_process REPLACES the scaffold stub.
    for name, stub_re in _SCAFFOLD_STUB_RE.items():
        if re.search(rf"(?m)^    def {name}\b", merged_methods):
            scaffold = stub_re.sub("", scaffold, count=1)

    result = scaffold.replace(EXTRA_IMPORTS_MARKER, "\n".join(deduped_imports), 1)
    result = result.replace(METHODS_MARKER, merged_methods, 1)

    (main_dir / f"{pattern_name}.py").write_text(result, encoding="utf-8")

    # The unit plan (when present) pins each file's expected method + loop arity.
    plan_by_fname: dict = {}
    plan_file = run_dir / "1_units.json"
    if plan_file.is_file():
        try:
            from pattern_generator.prepare import _unit_methods_filename
            for pu in json.loads(plan_file.read_text(encoding="utf-8")):
                plan_by_fname[_unit_methods_filename(pu)] = pu
        except Exception:
            plan_by_fname = {}

    # Per-unit deterministic findings (same checks as the gate, run per unit). Best-effort:
    # api/citation need the Script library; semantic is pure AST. See unit_gate.check_unit.
    api_issues: dict = {}
    sem_issues: dict = {}
    cite_issues: dict = {}
    index = build_script_index(script_root) if script_root else None
    for fname, u in parsed:
        if not u.methods:
            continue
        pu = plan_by_fname.get(fname) or {}
        res = check_unit(u.methods, code_refs=u.code_refs, script_root=script_root, index=index,
                         expected_methods=[pu["method"]] if pu.get("method") else None,
                         extra_imports=deduped_imports,   # assembly scope = union of imports
                         loop_idx_required=bool(pu.get("loop_idx_param")))
        if res["api"]:
            api_issues[fname] = res["api"]
        if res["citation"]:
            cite_issues[fname] = res["citation"]
        if res["semantic"]:
            sem_issues[fname] = res["semantic"]

    _write_retrieval_debug(run_dir, parsed, api_issues, sem_issues, cite_issues)
    return result


def _write_retrieval_debug(run_dir: Path, parsed: list, api_issues: dict | None = None,
                           sem_issues: dict | None = None,
                           cite_issues: dict | None = None) -> None:
    """Write retrieval_debug.md: per-unit wiki top-5 + code top-5 + review flag,
    with a flag-count summary at the top.

    Review flags shown are the union of the agent's self-reported flags and the
    flags DERIVED from content (so a unit that calls APIs without any code ref is
    flagged even if the agent forgot to). `api_issues` maps filename -> list of
    api-grounding problem strings (unknown symbol / bad signature)."""
    api_issues = api_issues or {}
    sem_issues = sem_issues or {}
    cite_issues = cite_issues or {}
    counts = {flag: 0 for flag in REVIEW_FLAGS}
    api_issue_count = 0
    sem_issue_count = 0
    cite_issue_count = 0
    body: list = []
    for fname, u in parsed:
        body.append(f"## {fname}")
        body.append("**wiki refs:**")
        if u.is_no_match(u.wiki_refs):
            body.append("- _NO MATCH_")
        else:
            body.extend(f"- {r}" for r in u.wiki_refs)
        body.append("**code refs (gitnexus):**")
        if u.is_no_match(u.code_refs):
            body.append("- _NO MATCH_")
        else:
            body.extend(f"- {r}" for r in u.code_refs)

        # Union of self-reported + content-derived flags (order-preserving, unique).
        effective_flags: list = []
        for flag in list(u.review_flags) + _derive_review_flags(u):
            if flag not in effective_flags:
                effective_flags.append(flag)
        if effective_flags:
            for flag in effective_flags:
                counts[flag] = counts.get(flag, 0) + 1
            body.append("**review flags:** " + ", ".join(f"`{f}`" for f in effective_flags))

        if fname in api_issues:
            api_issue_count += len(api_issues[fname])
            body.append("**⚠️ api-grounding issues (validator):**")
            body.extend(f"- {msg}" for msg in api_issues[fname])
        if fname in sem_issues:
            sem_issue_count += len(sem_issues[fname])
            body.append("**⚠️ semantic issues (validator):**")
            body.extend(f"- {msg}" for msg in sem_issues[fname])
        if fname in cite_issues:
            cite_issue_count += len(cite_issues[fname])
            body.append("**⚠️ fabricated citation(s):**")
            body.extend(f"- {msg}" for msg in cite_issues[fname])
        body.append("")

    header = ["# Retrieval Debug", ""]
    total_flagged = sum(counts.values())
    if total_flagged or api_issue_count or sem_issue_count or cite_issue_count:
        if total_flagged:
            header.append("> ⚠️ review flags raised:")
            for flag, n in counts.items():
                if n:
                    header.append(f">  - `{flag}`: {n}")
        if api_issue_count:
            header.append(f"> ⚠️ api-grounding issues: {api_issue_count} "
                          "(unknown symbol / bad signature — see units below)")
        if sem_issue_count:
            header.append(f"> ⚠️ semantic issues: {sem_issue_count} "
                          "(wrong field/polarity — see units below)")
        if cite_issue_count:
            header.append(f"> ⚠️ fabricated citations: {cite_issue_count} "
                          "(code-ref cites a symbol not in Script — see units below)")
        header.append("")
    else:
        header.append("_(no review flags — every unit grounded in both wiki and code)_")
        header.append("")

    # Embed the deterministic "defaults offered per unit" record (written by prepare)
    # so one file shows both what was OFFERED (deterministic) and what the model
    # SELF-REPORTED using (wiki/code refs above).
    defaults_dbg = run_dir / "defaults_debug.md"
    tail: list = []
    if defaults_dbg.is_file():
        tail = ["", "---", "", "## Defaults offered (deterministic — what was injected)",
                "", defaults_dbg.read_text(encoding="utf-8").strip()]

    (run_dir / "retrieval_debug.md").write_text(
        "\n".join(header + body + tail), encoding="utf-8")
