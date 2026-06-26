"""Append-only gate history — every validate/finish run records its fail points.

All history for a pattern accumulates in ONE folder (PGConfig.gate_log_dir),
one markdown file per pattern: `<pattern_id>.gate_log.md`. Each run appends a
timestamped entry listing that run's findings per dimension, so you can see the
whole history (which fail points recur, which round fixed them) in one place.

Never overwrites; pure stdlib.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pattern_generator.driver import gate_failures


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_record(pattern_id: str, py_path, command: str, round_,
                  report: dict, timestamp: str | None = None) -> str:
    """Render one history entry (the block appended per run). round_ may be None
    (standalone validate) -> omitted from the header."""
    fails = gate_failures(report)
    outcome = "FAIL" if fails else "PASS"
    ts = timestamp or _now()
    rnd = f" round {round_}" if round_ else ""
    lines = [f"## {ts} — {command}{rnd} — {outcome}  ({py_path})"]
    if fails:
        for dim, val in fails.items():
            if isinstance(val, list):
                for m in val:
                    lines.append(f"- [{dim}] {m}")
            else:
                lines.append(f"- [{dim}] {val}")
    else:
        lines.append("- (no findings)")
    return "\n".join(lines) + "\n"


def log_path(log_dir, pattern_id: str) -> Path:
    return Path(log_dir) / f"{pattern_id}.gate_log.md"


def append_record(log_dir, pattern_id: str, py_path, command: str, round_: int,
                  report: dict, timestamp: str | None = None) -> Path:
    """Append one run's findings to <log_dir>/<pattern_id>.gate_log.md (created on
    first use, with a title). Returns the log path."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_path(log_dir, pattern_id)
    block = format_record(pattern_id, py_path, command, round_, report, timestamp)
    if not path.exists():
        path.write_text(f"# Gate log — {pattern_id}\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(block + "\n")
    return path
