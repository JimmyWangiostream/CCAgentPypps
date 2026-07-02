#!/usr/bin/env python3
"""Lint the layered wiki (SCHEMA.md's third operation).

    python wiki_lint.py [--wiki wiki]

A deterministic structural health check so the wiki doesn't feed bad/missing info into
generation prompts: dangling [[wikilinks]], pages missing `type:` frontmatter, orphans,
stale default.md, conflicts referencing missing pages, and unused source/code trees under
wiki/. Exits 1 if any ERROR (CI-able), 0 otherwise. Reports only — never edits the wiki.

With `--script-root <Script>` it ALSO runs the grounding-consistency layer: cross-checks the
wiki's machine facts (struct fields, bit positions, api./ExecuteCMD./lib. calls) against the
real Script AST index, so a wrong fact (e.g. WriteBooster = bit[0] when the struct puts it at
bit[8]) is caught deterministically instead of silently teaching the model the wrong thing.
"""
import argparse
import sys

from wiki_retrieval.lint import lint_wiki, format_findings, summary
from wiki_retrieval.grounding_lint import lint_wiki_grounding


def main() -> int:
    ap = argparse.ArgumentParser(description="Structural health check for the layered wiki")
    ap.add_argument("--wiki", default=None, help="wiki root (default: ./wiki)")
    ap.add_argument("--script-root", default=None,
                    help="Script library root; enables the grounding-consistency (factual) layer")
    args = ap.parse_args()

    findings = lint_wiki(args.wiki)
    if args.script_root:
        findings += lint_wiki_grounding(args.wiki, args.script_root)
    s = summary(findings)
    if not findings:
        print("wiki lint: clean (no structural issues)")
        return 0

    errors = [f for f in findings if f["level"] == "error"]
    warns = [f for f in findings if f["level"] == "warn"]
    if errors:
        print(f"== ERRORS ({len(errors)}) ==")
        print("\n".join(format_findings(errors)))
    if warns:
        print(f"== WARNINGS ({len(warns)}) ==")
        print("\n".join(format_findings(warns)))
    print(f"\nwiki lint: {s['errors']} error(s), {s['warnings']} warning(s)")
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
