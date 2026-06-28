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
    p2.add_argument("--grounding", choices=["gitnexus", "direct"], default="gitnexus",
                    help="code grounding: 'gitnexus' (default, MCP) or 'direct' "
                         "(inject candidates straight from Script; no MCP server)")
    p2.add_argument("--generated-dir", default=None,
                    help="output base dir (default: PGConfig.generated_dir; "
                         "for --grounding direct: <repo>/generate_without_gitnexus)")

    pu = sub.add_parser("prepare-unit",
                        help="build unit N's prompt (embeds upstream unit methods)")
    pu.add_argument("run_dir", help="generated/<ID>/ directory")
    pu.add_argument("unit_index", type=int, help="1-based unit number")
    pu.add_argument("--grounding", choices=["gitnexus", "direct"], default=None,
                    help="override grounding mode (default: read from run dir's _run_meta.json)")

    pa = sub.add_parser("assemble", help="scaffold.py + phase_*_methods.py -> final .py")
    pa.add_argument("run_dir", help="generated/<ID>/ directory")
    pa.add_argument("pattern_name", help="Output filename without .py extension")

    p3 = sub.add_parser("validate", help="validate a generated .py against its IR")
    p3.add_argument("py_file")
    p3.add_argument("ir_file")
    p3.add_argument("--script-root", default=None,
                    help="Root of the Script/ library for the API-reality check "
                         "(default: PGConfig.script_root)")
    p3.add_argument("--gate-log-dir", default=None,
                    help="folder for the append-only gate history (default: PGConfig.gate_log_dir)")
    p3.add_argument("--no-mypy", action="store_true",
                    help="skip the mypy type-check gate (default: run it)")

    sub.add_parser("rules", help="list the prescriptive rule pack (the pitfall checklist)")

    sub.add_parser("build-defaults",
                   help="merge wiki/UserPrompt + wiki/ModelDefault (+conflicts) -> wiki/default.md")

    pr = sub.add_parser("review",
                        help="build the review->repair prompt (checkpoints + rule pack + code)")
    pr.add_argument("py_file")
    pr.add_argument("ir_file")

    pw = sub.add_parser("prepare-wholefile",
                        help="Stage 3: scaffold + ONE whole-file authoring prompt "
                             "(idiom anchors + rule pack + data-flow contract)")
    pw.add_argument("ir_file")
    pw.add_argument("--generated-dir", default=None)
    pw.add_argument("--script-root", default=None)

    pg = sub.add_parser("finish",
                        help="gate driver: validate; on fail emit a repair prompt "
                             "(findings + review) to loop, on pass emit the review prompt")
    pg.add_argument("py_file")
    pg.add_argument("ir_file")
    pg.add_argument("--script-root", default=None)
    pg.add_argument("--max-rounds", type=int, default=3)
    pg.add_argument("--gate-log-dir", default=None,
                    help="folder for all gate by-products + append-only history "
                         "(default: PGConfig.gate_log_dir)")
    pg.add_argument("--no-mypy", action="store_true",
                    help="skip the mypy type-check gate (default: run it)")

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
        base = PGConfig()
        if args.generated_dir:
            gen_dir = Path(args.generated_dir)
        elif args.grounding == "direct":
            gen_dir = base.repo_root / "generate_without_gitnexus"
        else:
            gen_dir = base.generated_dir
        cfg = PGConfig(generated_dir=gen_dir, grounding_mode=args.grounding)
        out = prepare_pattern(Path(args.ir_file), cfg)
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
        cfg = PGConfig(grounding_mode=args.grounding) if args.grounding else PGConfig()
        out = prepare_unit(Path(args.run_dir), args.unit_index, cfg)
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
        from pattern_generator.gate_log import append_record
        base = PGConfig()
        ir = json.loads(Path(args.ir_file).read_text(encoding="utf-8"))
        py_file = Path(args.py_file)
        src = py_file.read_text(encoding="utf-8")
        script_root = args.script_root or base.script_root
        report = validate(src, ir, script_root=script_root,
                          py_path=str(py_file), run_mypy=not args.no_mypy)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        log_dir = Path(args.gate_log_dir) if args.gate_log_dir else base.gate_log_dir
        lp = append_record(log_dir, ir["pattern_id"], py_file.name, "validate", None, report)
        print(f"Gate log: {lp}")
    elif args.cmd == "rules":
        from pattern_generator.rules import RULES, format_rules
        print(f"Rule pack — {len(RULES)} prescriptive rules (the pitfall checklist):\n")
        print(format_rules(RULES))
    elif args.cmd == "build-defaults":
        from wiki_retrieval.defaults import write_defaults
        path = write_defaults(PGConfig().wiki_path)
        print(f"Wrote {path} ({len(path.read_text(encoding='utf-8').splitlines())} lines)")
        print("This is the single always-injected 'project defaults' doc "
              "(UserPrompt > ModelDefault). Regenerate after editing the sources.")
    elif args.cmd == "prepare-wholefile":
        from pattern_generator.wholefile import build_wholefile_prompt
        from pattern_generator.run_logger import RunDir
        from pattern_generator.stepwise import build_scaffold
        base = PGConfig()
        gen_dir = Path(args.generated_dir) if args.generated_dir else base.generated_dir
        script_root = args.script_root or base.script_root
        ir = json.loads(Path(args.ir_file).read_text(encoding="utf-8"))
        run = RunDir(gen_dir, ir["pattern_id"])
        scaffold = build_scaffold(ir)
        run.write_text("scaffold.py", scaffold)
        from wiki_retrieval.defaults import load_defaults
        prompt = build_wholefile_prompt(ir, script_root, scaffold=scaffold,
                                        defaults=load_defaults(base.wiki_path))
        run.write_text("wholefile_prompt.txt", prompt)
        print(f"Run dir: {run.path}")
        print(f"Next (LLM): read {run.path}/wholefile_prompt.txt → write the COMPLETE "
              f"<PatternName>.py in {gen_dir}")
        print(f"Then: python generate_pattern.py validate {gen_dir}/<PatternName>.py {args.ir_file}")
    elif args.cmd == "review":
        from pattern_generator.review import build_review_prompt
        from wiki_retrieval.defaults import load_defaults
        ir = json.loads(Path(args.ir_file).read_text(encoding="utf-8"))
        py_file = Path(args.py_file)
        src = py_file.read_text(encoding="utf-8")
        prompt = build_review_prompt(src, ir, defaults=load_defaults(PGConfig().wiki_path))
        out_path = py_file.with_name(py_file.stem + "_review_prompt.txt")
        out_path.write_text(prompt, encoding="utf-8")
        print(f"Review prompt: {out_path}")
        print(f"Next (LLM): read it, write the corrected {py_file.name}, then "
              f"re-run: python generate_pattern.py validate {py_file.name} {Path(args.ir_file).name}")
    elif args.cmd == "finish":
        import sys
        from pattern_generator.driver import run_gate, build_repair_prompt
        from pattern_generator.review import build_review_prompt
        from pattern_generator.gate_log import append_record
        from wiki_retrieval.defaults import load_defaults
        base = PGConfig()
        defaults = load_defaults(base.wiki_path)
        ir = json.loads(Path(args.ir_file).read_text(encoding="utf-8"))
        pattern_id = ir["pattern_id"]
        py_file = Path(args.py_file)
        src = py_file.read_text(encoding="utf-8")
        script_root = args.script_root or base.script_root
        gate = run_gate(src, ir, script_root=script_root,
                        py_path=str(py_file), run_mypy=not args.no_mypy)
        print(json.dumps(gate["report"], ensure_ascii=False, indent=2))

        # All by-products + history live in ONE folder, named by pattern_id.
        log_dir = Path(args.gate_log_dir) if args.gate_log_dir else base.gate_log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        state_file = log_dir / f"{pattern_id}_gate_state.json"
        rnd = 1
        if state_file.exists():
            try:
                rnd = int(json.loads(state_file.read_text(encoding="utf-8")).get("round", 0)) + 1
            except (OSError, ValueError):
                rnd = 1

        lp = append_record(log_dir, pattern_id, py_file.name, "finish", rnd, gate["report"])

        if gate["failures"]:
            if rnd > args.max_rounds:
                print(f"GATE FAIL: max rounds ({args.max_rounds}) reached — needs a human.")
                print(f"Gate log: {lp}")
                state_file.unlink(missing_ok=True)
                sys.exit(1)
            prompt = build_repair_prompt(src, ir, gate["report"], defaults=defaults)
            out_path = log_dir / f"{pattern_id}_repair_prompt.txt"
            out_path.write_text(prompt, encoding="utf-8")
            state_file.write_text(json.dumps({"round": rnd}), encoding="utf-8")
            print(f"GATE FAIL (round {rnd}/{args.max_rounds}). Repair prompt: {out_path}")
            print(f"Gate log: {lp}")
            print(f"Next (LLM): read the repair prompt, rewrite {py_file.name} fixing every "
                  f"finding, then re-run: python generate_pattern.py finish {py_file.name} {Path(args.ir_file).name}")
            sys.exit(1)
        else:
            state_file.unlink(missing_ok=True)  # converged; reset the loop counter
            prompt = build_review_prompt(src, ir, defaults=defaults)
            out_path = log_dir / f"{pattern_id}_review_prompt.txt"
            out_path.write_text(prompt, encoding="utf-8")
            print("GATE PASS (structural). A structural pass is NOT rule-clean — do one "
                  "rule-level review pass for assert-discipline / protocol correctness.")
            print(f"Review prompt: {out_path}  (read → rewrite → re-run finish to confirm)")
            print(f"Gate log: {lp}")


if __name__ == "__main__":
    main()
