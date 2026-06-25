"""Load the layered wiki into structured docs + parse the conflict log.

A wiki doc is one ingested page under wiki/concepts/ or wiki/entities/ (sources/
optional). Each carries frontmatter (type/title/tags/aliases/sources) and the
`[[wikilink]]` references found in its body — the raw material for the reference
graph and the BM25/dense corpora.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WIKI = _REPO_ROOT / "wiki"

# Directories that hold ingested, layered pages (have `type:` frontmatter).
LAYER_DIRS = ("concepts", "entities", "sources")

_WIKILINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9-]*)\]\]")
_LIST_RE = re.compile(r"^\s*(\w+):\s*\[(.*?)\]\s*$", re.MULTILINE)
_SCALAR_RE = re.compile(r'^\s*(\w+):\s*"?(.*?)"?\s*$', re.MULTILINE)


@dataclass
class WikiDoc:
    stem: str                       # filename without .md, e.g. "write-booster"
    path: str                       # repo-relative, e.g. "entities/write-booster.md"
    layer: str                      # "concept" | "entity" | "source" | "" (from type:)
    title: str
    tags: list = field(default_factory=list)
    aliases: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    body: str = ""
    refs: list = field(default_factory=list)   # wikilink target stems (deduped)

    def search_text(self) -> str:
        """Text used for BM25/dense. Title/aliases/tags are repeated to weight
        metadata above body (field boosting), so a page about X ranks high for X."""
        title = " ".join([self.title] * 3)
        aliases = " ".join(self.aliases * 3)
        tags = " ".join(self.tags * 2)
        return f"{title}\n{aliases}\n{tags}\n{self.body}"


def _split_frontmatter(content: str) -> tuple:
    """Return (frontmatter, body). Strips a leading YAML --- ... --- block."""
    if content.startswith("---"):
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
        if m:
            return m.group(1), m.group(2)
    return "", content


def _parse_list(fm: str, key: str) -> list:
    for m in _LIST_RE.finditer(fm):
        if m.group(1) == key:
            inner = m.group(2).strip()
            if not inner:
                return []
            return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
    return []


def _parse_scalar(fm: str, key: str, default: str = "") -> str:
    for m in _SCALAR_RE.finditer(fm):
        if m.group(1) == key:
            return m.group(2).strip()
    return default


def _title_from_body(body: str, fallback: str) -> str:
    hm = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return hm.group(1).strip() if hm else fallback


def extract_wikilinks(body: str) -> list:
    """Deduped, order-preserving list of [[wikilink]] target stems."""
    seen, out = set(), []
    for m in _WIKILINK_RE.finditer(body):
        t = m.group(1)
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_doc(md_path: Path, layer_dir: str) -> WikiDoc:
    content = md_path.read_text(encoding="utf-8", errors="ignore")
    fm, body = _split_frontmatter(content)
    stem = md_path.stem
    return WikiDoc(
        stem=stem,
        path=f"{layer_dir}/{md_path.name}",
        layer=_parse_scalar(fm, "type", ""),
        title=_parse_scalar(fm, "title", "") or _title_from_body(body, stem),
        tags=_parse_list(fm, "tags"),
        aliases=_parse_list(fm, "aliases"),
        sources=_parse_list(fm, "sources"),
        body=body,
        refs=extract_wikilinks(body),
    )


def load_corpus(wiki_root=None, layer_dirs=("concepts", "entities")) -> dict:
    """Load layered wiki docs keyed by stem. Defaults to concept + entity layers."""
    wiki_root = Path(wiki_root) if wiki_root else DEFAULT_WIKI
    docs: dict = {}
    for layer_dir in layer_dirs:
        d = wiki_root / layer_dir
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            doc = load_doc(md, layer_dir)
            docs[doc.stem] = doc
    return docs


# ---------------------------------------------------------------------------
# Conflict log — two independent rules; each conflict lists its Affected Pages.
# ---------------------------------------------------------------------------

@dataclass
class Conflict:
    title: str          # e.g. "WriteBooster LUN Restriction"
    rule: str           # e.g. "Rule 1 (CustomerReq vs Spec → CustomerReq WINS)"
    affected: list      # affected page stems, e.g. ["write-booster", "lun"]


def parse_conflicts(wiki_root=None) -> list:
    """Parse wiki/conflicts.md into per-conflict records with their affected pages.

    Each `## Conflict #N — <title>` block has a `**Rule**:` line and a
    `### Affected Wiki Pages` section listing `[[stem]]` entries.
    """
    wiki_root = Path(wiki_root) if wiki_root else DEFAULT_WIKI
    cf = wiki_root / "conflicts.md"
    if not cf.is_file():
        return []
    text = cf.read_text(encoding="utf-8", errors="ignore")

    conflicts: list = []
    # Split on conflict headers, keeping the title.
    blocks = re.split(r"^##\s+Conflict\s+#\d+\s*[—-]\s*(.+)$", text, flags=re.MULTILINE)
    # blocks[0] is the preamble; then pairs of (title, body)
    for i in range(1, len(blocks), 2):
        title = blocks[i].strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        rule_m = re.search(r"\*\*Rule\*\*:\s*(.+)", body)
        rule = rule_m.group(1).strip() if rule_m else ""
        affected = []
        aff_m = re.search(r"###\s+Affected Wiki Pages\s*(.+?)(?:\n##|\Z)", body, re.DOTALL)
        if aff_m:
            affected = extract_wikilinks(aff_m.group(1))
        conflicts.append(Conflict(title=title, rule=rule, affected=affected))
    return conflicts
