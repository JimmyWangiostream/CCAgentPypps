"""Build a flat, searchable index of real symbols from a Script library tree.

Pure stdlib (`ast`). No imports are executed — the library is read statically,
the same way `pattern_generator.api_grounding` indexes it for the validator. We
scan a focused set of folders (sample_code idioms first, then the api / project
api surfaces) so candidates stay high-signal rather than drowning in the full
414-file pattern tree.

Each indexed symbol becomes a `SymbolDoc` carrying its file:line, an ordered
rendered signature, and its docstring — enough to inject as a candidate and for
the model to locate-and-confirm by reading the source.
"""
from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass
from pathlib import Path

# Split a CamelCase / snake_case / digit-joined identifier into its word parts so
# a natural-language query ("TEST UNIT READY") matches a compound symbol name
# ("TestUnitReady") under the word-level BM25 tokenizer.
_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _split_identifier(name: str) -> str:
    words: list[str] = []
    for chunk in name.replace(".", "_").split("_"):
        words.extend(_WORD_RE.findall(chunk))
    return " ".join(words)

# Folders worth surfacing as code candidates, in rough priority order:
#   pattern/sample_code/ — canonical call idioms (highest value)
#   api/                 — protocol APIs implemented per the UFS Spec
#   project_api/         — this project's customer APIs
# The bulk pattern/ tree is intentionally skipped (noise); upstream patterns are
# still reachable because the model may grep the tree to confirm an idiom.
SCAN_DIRS = ("pattern/sample_code", "api", "project_api")


@dataclass
class SymbolDoc:
    name: str
    kind: str           # "func" | "class" | "method"
    path: str           # script_root-relative posix path, e.g. "api/ufs_api/rw_functions.py"
    lineno: int
    signature: str      # rendered "name(params)" with defaults marked '=...'
    docstring: str = ""
    qualname: str = ""  # "Class.method" for methods; else == name

    @property
    def uid(self) -> str:
        return f"{self.path}::{self.qualname or self.name}::{self.lineno}"

    @property
    def display(self) -> str:
        return self.qualname or self.name

    def search_text(self) -> str:
        """BM25 corpus for this symbol: split name + path words + signature + docstring head."""
        path_words = self.path.replace("/", " ").replace("_", " ").replace(".py", "")
        name_words = f"{_split_identifier(self.display)} {_split_identifier(self.name)}"
        doc_head = " ".join(self.docstring.split())[:240]
        return f"{self.display} {self.name} {name_words} {path_words} {self.signature} {doc_head}"

    def render(self, rank: int | None = None) -> str:
        """One-line candidate / CODE REFS form: 'path: Symbol — signature [(script rankN)]'."""
        tag = f" (script rank{rank})" if rank else ""
        return f"{self.path}: {self.display} — {self.signature}{tag}"


def _render_signature(name: str, args: ast.arguments, skip_self: bool) -> str:
    """Render an ordered call signature; defaults shown as '=...' (values elided)."""
    parts: list[str] = []
    posonly = list(getattr(args, "posonlyargs", []))
    pos = list(args.args)
    allpos = posonly + pos
    if skip_self and allpos and allpos[0].arg in ("self", "cls"):
        allpos = allpos[1:]
    ndef = len(args.defaults)
    for i, a in enumerate(allpos):
        has_default = i >= len(allpos) - ndef if ndef else False
        parts.append(a.arg + ("=..." if has_default else ""))
    if args.vararg is not None:
        parts.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        parts.append("*")
    for j, a in enumerate(args.kwonlyargs):
        has_default = j < len(args.kw_defaults) and args.kw_defaults[j] is not None
        parts.append(a.arg + ("=..." if has_default else ""))
    if args.kwarg is not None:
        parts.append("**" + args.kwarg.arg)
    return f"{name}({', '.join(parts)})"


def _docstring(node: ast.AST) -> str:
    try:
        return ast.get_docstring(node) or ""  # type: ignore[arg-type]
    except TypeError:
        return ""


def _index_file(py: Path, script_root: Path) -> list[SymbolDoc]:
    try:
        # Script library sources may contain invalid escapes (e.g. "\w" in non-raw
        # strings) → SyntaxWarning; we only read them, so silence the noise.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return []
    rel = py.relative_to(script_root).as_posix()
    out: list[SymbolDoc] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(SymbolDoc(
                name=node.name, kind="func", path=rel, lineno=node.lineno,
                signature=_render_signature(node.name, node.args, skip_self=False),
                docstring=_docstring(node), qualname=node.name,
            ))
        elif isinstance(node, ast.ClassDef):
            init = next((b for b in node.body
                         if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and b.name == "__init__"), None)
            ctor_args = init.args if init is not None else ast.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[])
            out.append(SymbolDoc(
                name=node.name, kind="class", path=rel, lineno=node.lineno,
                signature=_render_signature(node.name, ctor_args, skip_self=True),
                docstring=_docstring(node), qualname=node.name,
            ))
            # public methods — these are the call idioms (.assign, .rpmb_read_counter, ...)
            for b in node.body:
                if (isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not b.name.startswith("_")):
                    out.append(SymbolDoc(
                        name=b.name, kind="method", path=rel, lineno=b.lineno,
                        signature=_render_signature(b.name, b.args, skip_self=True),
                        docstring=_docstring(b), qualname=f"{node.name}.{b.name}",
                    ))
    return out


def build_symbol_index(script_root) -> list[SymbolDoc]:
    """Scan SCAN_DIRS under `script_root` → flat list of SymbolDoc (functions,
    classes, public methods). Returns [] if the root has no `api/` folder."""
    root = Path(script_root)
    if not (root / "api").is_dir():
        return []
    docs: list[SymbolDoc] = []
    seen: set[str] = set()
    for sub in SCAN_DIRS:
        base = root / sub
        if not base.is_dir():
            continue
        for py in sorted(base.rglob("*.py")):
            for d in _index_file(py, root):
                if d.uid in seen:
                    continue
                seen.add(d.uid)
                docs.append(d)
    return docs
