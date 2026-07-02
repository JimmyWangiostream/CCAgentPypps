"""Tests for the deterministic wiki lint (wiki_retrieval.lint)."""
import os
import time

from wiki_retrieval.lint import lint_wiki


def _kinds(findings):
    return {f["kind"] for f in findings}


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _good_concept(stem, body_ref="entity-a"):
    return (f"---\ntype: concept\ntitle: {stem.title()}\n---\n\n"
            f"# {stem.title()}\n\nA solid concept body long enough to clear the stub "
            f"threshold, linking to [[{body_ref}]] for graph expansion coverage and more.\n")


def _good_entity(stem):
    return (f"---\ntype: entity\ntitle: {stem.title()}\n---\n\n"
            f"# {stem.title()}\n\nA solid entity body long enough to clear the stub threshold "
            f"so the orphan/stub checks are exercised cleanly across the corpus here.\n")


def _clean_wiki(root):
    _write(root / "concepts" / "concept-a.md", _good_concept("concept-a", "entity-a"))
    _write(root / "entities" / "entity-a.md", _good_entity("entity-a"))
    # entity-a is linked from concept-a (has in-edge); concept-a links out -> neither orphan
    _write(root / "default.md", "# defaults\n")
    _write(root / "conflicts.md", "# Conflict Log\n")


def test_clean_wiki_has_no_errors(tmp_path):
    _clean_wiki(tmp_path)
    findings = lint_wiki(tmp_path)
    assert not [f for f in findings if f["level"] == "error"], findings


def test_dangling_wikilink_flagged(tmp_path):
    _clean_wiki(tmp_path)
    _write(tmp_path / "concepts" / "concept-b.md",
           _good_concept("concept-b", "does-not-exist"))
    assert "dangling_wikilink" in _kinds(lint_wiki(tmp_path))


def test_missing_type_flagged(tmp_path):
    _clean_wiki(tmp_path)
    _write(tmp_path / "concepts" / "no-type.md",
           "# No Type\n\nBody long enough to avoid the stub flag but missing frontmatter type.\n")
    kinds = _kinds(lint_wiki(tmp_path))
    assert "missing_type" in kinds


def test_orphan_and_stub_flagged(tmp_path):
    _clean_wiki(tmp_path)
    _write(tmp_path / "entities" / "lonely.md", "---\ntype: entity\ntitle: Lonely\n---\n\n# Lonely\n\nx\n")
    kinds = _kinds(lint_wiki(tmp_path))
    assert "orphan_page" in kinds and "stub_page" in kinds


def test_unused_code_tree_is_error(tmp_path):
    _clean_wiki(tmp_path)
    _write(tmp_path / "Script" / "api" / "mod.py", "def f():\n    return 1\n")
    findings = lint_wiki(tmp_path)
    assert any(f["kind"] == "unused_code_tree" and f["level"] == "error" for f in findings)


def test_default_stale_flagged(tmp_path):
    _clean_wiki(tmp_path)
    # default.md older than a UserPrompt source -> stale
    dflt = tmp_path / "default.md"
    old = time.time() - 1000
    os.utime(dflt, (old, old))
    _write(tmp_path / "UserPrompt" / "up.md", "# user prompt newer than default\n")
    assert "default_stale" in _kinds(lint_wiki(tmp_path))
