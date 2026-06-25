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
import re
from dataclasses import dataclass, field
from pathlib import Path

from pattern_generator.api_grounding import (
    build_script_index, check_api_calls, format_issues,
)

EXTRA_IMPORTS_MARKER = "# @@EXTRA_IMPORTS@@"
METHODS_MARKER = "    # @@PHASE_METHODS@@"

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

    result = scaffold.replace(EXTRA_IMPORTS_MARKER, "\n".join(deduped_imports), 1)
    result = result.replace(METHODS_MARKER, "\n\n".join(all_methods), 1)

    (main_dir / f"{pattern_name}.py").write_text(result, encoding="utf-8")

    # API-reality findings per unit (best-effort; needs the Script library).
    api_issues: dict = {}
    index = build_script_index(script_root) if script_root else None
    if index:
        for fname, u in parsed:
            if not u.methods:
                continue
            # Wrap in a dummy class so the 4-space-indented methods parse.
            issues = check_api_calls("class _W:\n" + u.methods, index)
            if issues:
                api_issues[fname] = format_issues(issues)

    _write_retrieval_debug(run_dir, parsed, api_issues)
    return result


def _write_retrieval_debug(run_dir: Path, parsed: list, api_issues: dict | None = None) -> None:
    """Write retrieval_debug.md: per-unit wiki top-5 + code top-5 + review flag,
    with a flag-count summary at the top.

    Review flags shown are the union of the agent's self-reported flags and the
    flags DERIVED from content (so a unit that calls APIs without any code ref is
    flagged even if the agent forgot to). `api_issues` maps filename -> list of
    api-grounding problem strings (unknown symbol / bad signature)."""
    api_issues = api_issues or {}
    counts = {flag: 0 for flag in REVIEW_FLAGS}
    api_issue_count = 0
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
        body.append("")

    header = ["# Retrieval Debug", ""]
    total_flagged = sum(counts.values())
    if total_flagged or api_issue_count:
        if total_flagged:
            header.append("> ⚠️ review flags raised:")
            for flag, n in counts.items():
                if n:
                    header.append(f">  - `{flag}`: {n}")
        if api_issue_count:
            header.append(f"> ⚠️ api-grounding issues: {api_issue_count} "
                          "(unknown symbol / bad signature — see units below)")
        header.append("")
    else:
        header.append("_(no review flags — every unit grounded in both wiki and code)_")
        header.append("")

    (run_dir / "retrieval_debug.md").write_text("\n".join(header + body), encoding="utf-8")
