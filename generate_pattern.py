#!/usr/bin/env python3
"""CLI for the deterministic stages. LLM steps (IR annotation, .py generation,
C1/C2/C3 grading) are performed by the current Claude Code model between calls —
see README.md."""
import argparse
import json
from pathlib import Path

from ir_generator.config import Config
from ir_generator.prepare_ir import prepare_ir, finalize_ir
from pattern_generator.config import PGConfig
from pattern_generator.prepare import prepare_pattern, prepare_unit
from pattern_generator.validator import validate


def main():
    ap = argparse.ArgumentParser(description="UFS pattern generation — deterministic stages")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prepare-ir", help="TC .md -> IR skeleton + enrich prompt")
    p1.add_argument("tc_file")

    pf = sub.add_parser("finalize-ir",
                        help="ir_skeleton.json + annotations.json -> final <id>-ir.json (in folder)")
    pf.add_argument("skeleton_file", help="generated/<ID>/ir_skeleton.json from prepare-ir")
    pf.add_argument("annotations_file", help="annotations JSON produced by the LLM step")

    p2 = sub.add_parser("prepare", help="IR json -> scaffold + units + first unit prompt")
    p2.add_argument("ir_file")

    pu = sub.add_parser("prepare-unit",
                        help="build unit N's prompt (embeds upstream unit methods)")
    pu.add_argument("run_dir", help="generated/<ID>/ directory")
    pu.add_argument("unit_index", type=int, help="1-based unit number")

    pa = sub.add_parser("assemble", help="scaffold.py + phase_*_methods.py -> final .py")
    pa.add_argument("run_dir", help="generated/<ID>/ directory")
    pa.add_argument("pattern_name", help="Output filename without .py extension")

    p3 = sub.add_parser("validate", help="validate a generated .py against its IR")
    p3.add_argument("py_file")
    p3.add_argument("ir_file")
    p3.add_argument("--script-root", default=None,
                    help="Root of the Script/ library for the API-reality check "
                         "(default: PGConfig.script_root)")

    args = ap.parse_args()

    if args.cmd == "prepare-ir":
        out = prepare_ir(Path(args.tc_file), Config())
        print(f"Run dir: {out['run_dir']}")
        print(f"Next (LLM): read {out['run_dir']}/enrich_prompt.txt, produce annotations JSON.")
    elif args.cmd == "finalize-ir":
        bundle = json.loads(Path(args.skeleton_file).read_text(encoding="utf-8"))
        annotations = json.loads(Path(args.annotations_file).read_text(encoding="utf-8"))
        out = finalize_ir(bundle["skeleton"], annotations, bundle["wiki_refs"], Config())
        print(f"Final IR: {out}")
    elif args.cmd == "prepare":
        out = prepare_pattern(Path(args.ir_file), PGConfig())
        print(f"Run dir: {out['run_dir']}")
        print(f"Units: {out['unit_count']} (one stepN per step/loop-wrapper; loop "
              f"sub-steps are helper methods)")
        print(f"Scaffold: {out['run_dir']}/scaffold.py")
        if out["first_prompt_file"]:
            methods_file = out["first_prompt_file"].replace("_prompt.txt", "_methods.py")
            print(f"Next (LLM): read {out['run_dir']}/{out['first_prompt_file']} → write {methods_file}")
        if out["unit_count"] > 1:
            print(f"Then for k=2..{out['unit_count']}: "
                  f"python generate_pattern.py prepare-unit {out['run_dir']} k  (→ read prompt → write methods)")
            print("  (loop-wrapper units are deterministic — prepare-unit writes them "
                  "automatically and reports 'skip'; do NOT hand-write their methods.)")
        print(f"Finally: python generate_pattern.py assemble {out['run_dir']} <PatternName>")
    elif args.cmd == "prepare-unit":
        out = prepare_unit(Path(args.run_dir), args.unit_index, PGConfig())
        if out.get("skipped"):
            print(f"Unit {out['unit_index']}/{out['unit_count']}: loop wrapper — "
                  f"deterministic methods file already written; skip (no LLM prompt).")
        else:
            methods_file = out["prompt_file"].replace("_prompt.txt", "_methods.py")
            print(f"Unit {out['unit_index']}/{out['unit_count']}: "
                  f"read {out['run_dir']}/{out['prompt_file']} → write {methods_file}")
    elif args.cmd == "assemble":
        from pattern_generator.assemble import assemble_pattern
        run_dir = Path(args.run_dir)
        src = assemble_pattern(run_dir, args.pattern_name,
                               script_root=PGConfig().script_root)
        out_path = run_dir.parent / f"{args.pattern_name}.py"
        print(f"Assembled: {out_path} ({len(src.splitlines())} lines)")
        print(f"By-products: {run_dir}")
    elif args.cmd == "validate":
        ir = json.loads(Path(args.ir_file).read_text(encoding="utf-8"))
        src = Path(args.py_file).read_text(encoding="utf-8")
        script_root = args.script_root or PGConfig().script_root
        report = validate(src, ir, script_root=script_root)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
