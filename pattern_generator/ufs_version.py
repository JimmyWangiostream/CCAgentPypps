"""Target UFS spec version — a first-class, deterministic input.

Why: several Script APIs / struct fields exist only on some UFS versions
(e.g. `get_extended_write_booster_support` reads `w77_extended_write_booster_support`,
which is on `DeviceDescriptor410` only — UFS 4.1). Without knowing the target version the
pipeline cannot deterministically exclude a version-unavailable symbol, so a 4.1-only API
can leak into a 3.1 pattern (the Hermes WriteBooster bug). This module makes the target
version an explicit input and maps it to the versioned struct suffix (310/400/410) the
`api_grounding` index uses.

Resolution priority (see `resolve`): the TC frontmatter `ufs_version:` (per-TC) wins, else
the project default in `wiki/target.md` (`ufs_version: X.Y`, editable per project), else None
(no version gating — behave as today).
"""
from __future__ import annotations

import re
from pathlib import Path

# Canonical version -> versioned struct/class suffix used across the Script index.
VERSION_SUFFIX = {"3.1": "310", "4.0": "400", "4.1": "410"}
_SUFFIX_TO_VERSION = {v: k for k, v in VERSION_SUFFIX.items()}


def normalize(raw) -> str | None:
    """Canonical `"3.1"/"4.0"/"4.1"` from many spellings, else None.

    Accepts dotted (`3.1`, `UFS 3.1`), struct suffix (`310`), and spec-version hex
    (`0x0410`, `0410`). Unknown/blank -> None (treated as "no target version")."""
    if raw is None:
        return None
    s = str(raw).strip().lower().replace("ufs", "").strip(" _-v")
    m = re.search(r"([34])\.(\d)", s)                 # dotted: 3.1 / 4.0 / 4.1
    if m:
        cand = f"{m.group(1)}.{m.group(2)}"
        return cand if cand in VERSION_SUFFIX else None
    digits = re.sub(r"[^0-9a-f]", "", s)              # 310 / 0410 / 0x0410
    if digits.startswith("0x"):
        digits = digits[2:]
    digits = digits.lstrip("0") or "0"
    return _SUFFIX_TO_VERSION.get(digits)


def struct_suffix(version) -> str | None:
    """`"3.1"` -> `"310"` (the DeviceDescriptor310/... suffix); None if unknown."""
    return VERSION_SUFFIX.get(normalize(version) or "")


def project_default(wiki_root=None) -> str | None:
    """Read the project-wide target version from `wiki/target.md` (`ufs_version: X.Y`)."""
    root = Path(wiki_root) if wiki_root else Path(__file__).resolve().parent.parent / "wiki"
    f = root / "target.md"
    if not f.is_file():
        return None
    m = re.search(r"^\s*ufs_version\s*:\s*(.+)$",
                  f.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    return normalize(m.group(1)) if m else None


def resolve(ir: dict | None = None, wiki_root=None, override=None) -> str | None:
    """Canonical target version: `override` (or IR `ufs_version`) > project default > None."""
    tc = normalize(override) or normalize((ir or {}).get("ufs_version"))
    return tc or project_default(wiki_root)
