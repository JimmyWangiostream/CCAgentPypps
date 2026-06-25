#!/usr/bin/env python3
"""Query the layered wiki and print the extractive essence (pipeline steps 4 + 5).

    python wiki_retrieve.py "write booster flush enable"
    python wiki_retrieve.py "PSA state" --no-dense --top 5

Returns the "concept -> entity -> reference -> conflict override" essence plus the
RRF top-N reference list. Replaces the old keyword-only wiki_query.py for grounding.
"""
import argparse
import io
import sys

from wiki_retrieval.retrieve import retrieve
from wiki_retrieval.essence import build_essence, format_top_refs


def _utf8_stdout():
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="Layered wiki retrieval (RRF + essence)")
    ap.add_argument("query", nargs="+", help="query terms")
    ap.add_argument("--wiki", default=None)
    ap.add_argument("--no-dense", action="store_true")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    _utf8_stdout()

    q = " ".join(args.query)
    result = retrieve(q, wiki_root=args.wiki, use_dense=not args.no_dense, top_n=args.top)

    print(f"# Wiki retrieval — dense={'on' if result.dense_used else 'off'}")
    print(f"## top {args.top} (RRF)")
    refs = format_top_refs(result)
    print("\n".join(f"- {r}" for r in refs) if refs else "- (NO MATCH)")
    print()
    print(build_essence(result))


if __name__ == "__main__":
    main()
