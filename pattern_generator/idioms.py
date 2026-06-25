"""Operation -> canonical worked idiom (Stage 3 grounding).

Instead of injecting N bare candidate symbol names (which mislead — see plan), we
anchor each operation on ONE complete, correct call example pulled from the Script
library (preferring pattern/sample_code/, the canonical idioms). A whole worked
snippet carries the right symbol, the right argument order, and the surrounding
assign/enqueue/send + assertion idiom — far harder to misread than a name list.

Reuses code_retrieval to rank, then extracts the matching function's source via AST.
"""
from __future__ import annotations

import ast
from pathlib import Path

from code_retrieval.retrieve import retrieve_code

_MAX_IDIOM_LINES = 40


def _extract_source(doc, script_root) -> str | None:
    """Pull the def/class source for `doc` (a SymbolDoc) from its file."""
    f = Path(script_root) / doc.path
    try:
        src = f.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and getattr(node, "lineno", None) == doc.lineno):
            seg = ast.get_source_segment(src, node)
            if seg and len(seg.splitlines()) <= _MAX_IDIOM_LINES:
                return seg
            return None
    return None


def find_idiom(query: str, script_root, k: int = 8) -> dict | None:
    """Best worked idiom for an operation query, or None.

    Returns {path, symbol, code}. Prefers pattern/sample_code/ (canonical idioms),
    then any extractable candidate."""
    if not query or not query.strip():
        return None
    refs = retrieve_code(query, script_root, k=k)
    preferred = [r for r in refs if "sample_code" in r.doc.path] or refs
    for r in preferred:
        code = _extract_source(r.doc, script_root)
        if code:
            return {"path": r.doc.path, "symbol": r.doc.display, "code": code}
    return None


def format_idiom(idiom: dict | None) -> str:
    if not idiom:
        return "(no idiom found — grep GitNexusMCP/Script to confirm the call)"
    return (f"# from {idiom['path']}: {idiom['symbol']}\n"
            f"```python\n{idiom['code']}\n```")
