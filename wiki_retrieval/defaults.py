"""Build & load wiki/default.md — the single, always-injected "project defaults".

Deterministic merge (NO LLM) of three existing sources, with per-section provenance:
  - wiki/UserPrompt/*.md   — overrides (highest priority; Rule 2 beats ModelDefault)
  - wiki/conflicts.md      — the resolution authority (Rule 1 CustomerReq, Rule 2 UserPrompt)
  - wiki/ModelDefault/*.md — the LLM-generated base (used when TC & UserPrompt are silent)

This replaces the weak "conflict pointer" injection (essence.py) that told the model a
LUN override *existed* but not what it *was* — which let a generator hardcode lun=0.
The folders stay as regenerable sources; default.md becomes the one consumed file.
"""
from __future__ import annotations

import re
from pathlib import Path

DEFAULTS_FILENAME = "default.md"


def _read_dir(d: Path, skip=("README.md",)) -> list:
    out = []
    if d.is_dir():
        for f in sorted(d.glob("*.md")):
            if f.name in skip:
                continue
            out.append((f.stem, f.read_text(encoding="utf-8").strip()))
    return out


def _row(block: str, label: str) -> str:
    """Value cell of a markdown table row `| <label> | value |` (first match)."""
    m = re.search(r"\|\s*" + re.escape(label) + r"\s*\|\s*([^|]+?)\s*\|", block, re.I)
    return m.group(1).strip() if m else ""


def _parse_conflicts(text: str) -> list:
    """Per-conflict records: {title, rule, customerreq, kept, deleted, effect, note}."""
    out = []
    for block in re.split(r"\n##\s*Conflict\s*#", text)[1:]:
        title_m = re.match(r"\s*\d+\s*[—-]\s*(.+)", block)
        rule_m = re.search(r"\*\*Rule\*\*:\s*Rule\s*(\d)", block)
        out.append({
            "title": title_m.group(1).strip() if title_m else "?",
            "rule": int(rule_m.group(1)) if rule_m else 0,
            "customerreq": _row(block, "CustomerReq value"),
            "kept": _row(block, "UserPrompt value"),
            "deleted": _row(block, "ModelDefault value"),
            "effect": _row(block, "Effective behavior"),
            "note": _row(block, "Implementation note"),
        })
    return out


def build_defaults_md(wiki_root) -> str:
    """Deterministically merge the three sources into the default.md markdown."""
    wiki = Path(wiki_root)
    user = _read_dir(wiki / "UserPrompt")
    model = _read_dir(wiki / "ModelDefault")
    conflicts_path = wiki / "conflicts.md"
    conflicts = _parse_conflicts(conflicts_path.read_text(encoding="utf-8")) \
        if conflicts_path.is_file() else []

    out: list = [
        "# Project Defaults (default.md) — AUTO-GENERATED, do not hand-edit",
        "",
        "> Merge of ModelDefault (base) + UserPrompt (overrides) + CustomerReq constraints.",
        "> Priority: **UserPrompt > ModelDefault**. Apply these when the TC flow omits a detail.",
        "> Sources: wiki/UserPrompt/, wiki/ModelDefault/, wiki/conflicts.md (audit).",
        "> Regenerate: `python generate_pattern.py build-defaults`",
        "",
        "## (1) UserPrompt overrides — HIGHEST priority (use when TC is silent)",
    ]
    if user:
        for _stem, body in user:
            out.append(body + "\n\n_← UserPrompt (overrides ModelDefault)_")
    else:
        out.append("_(none)_")

    rule1 = [c for c in conflicts if c["rule"] == 1]
    rule2 = [c for c in conflicts if c["rule"] == 2]

    out += ["", "## (2) CustomerReq constraints (Rule 1 — CustomerReq > Spec)"]
    if rule1:
        for c in rule1:
            val = c["effect"] or c["customerreq"]
            out.append(f"- **{c['title']}**: {val}  _← CustomerReq_")
    else:
        out.append("_(none)_")

    out += ["", "## (3) Resolved overrides (audit — from conflicts.md)"]
    def _strip(v: str) -> str:
        return re.sub(r"^(DELETED|KEPT)\s*[—-]\s*", "", v).strip()

    if rule2:
        for c in rule2:
            line = (f"- **{c['title']}**: ModelDefault `{_strip(c['deleted'])}` "
                    f"SUPERSEDED → use `{_strip(c['kept'])}`.")
            if c["note"]:
                line += f" {c['note']}"
            out.append(line + "  _← UserPrompt wins_")
    else:
        out.append("_(none)_")

    out += ["", "## (4) ModelDefault base (used only when TC AND UserPrompt are silent)",
            "_Items resolved in (3) above are superseded._", ""]
    for stem, body in model:
        out += [f"### {stem}  _← ModelDefault_", body, ""]

    return "\n".join(out).rstrip() + "\n"


def write_defaults(wiki_root) -> Path:
    wiki = Path(wiki_root)
    path = wiki / DEFAULTS_FILENAME
    path.write_text(build_defaults_md(wiki), encoding="utf-8")
    return path


def load_defaults(wiki_root) -> str:
    """Return default.md content (building it on the fly if not yet written)."""
    path = Path(wiki_root) / DEFAULTS_FILENAME
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return build_defaults_md(wiki_root)
