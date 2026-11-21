"""Command line interface.

Usage:
    python -m consolidation_drift demo
    python -m consolidation_drift audit --policy regenerate --cycles 12
    python -m consolidation_drift evaluate --outdir results
"""

import argparse
import json
import os

from .audit import audit_snapshots
from .evaluate import DEFAULT_CONFIG, run_evaluation, write_results
from .generate import generate_facts
from .policies import POLICIES, run_cycles
from .report import audit_report_markdown, cycle_table_markdown


def build_parser():
    parser = argparse.ArgumentParser(
        prog="consolidation_drift",
        description=(
            "Measure how agent memory facts mutate under repeated "
            "consolidation: typed drift classification and severity."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("demo", help="Small drift demo (40 facts, regenerate, 6 cycles)")

    audit_parser = sub.add_parser("audit", help="Audit one policy run")
    audit_parser.add_argument(
        "--policy", choices=sorted(POLICIES), default="regenerate"
    )
    audit_parser.add_argument("--facts", type=int, default=200)
    audit_parser.add_argument("--cycles", type=int, default=12)
    audit_parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG["seed"])

    eval_parser = sub.add_parser("evaluate", help="Run the headline experiment")
    eval_parser.add_argument("--outdir", default="results")
    eval_parser.add_argument("--facts", type=int, default=DEFAULT_CONFIG["n_facts"])
    eval_parser.add_argument("--cycles", type=int, default=DEFAULT_CONFIG["cycles"])
    eval_parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG["seed"])
    return parser


def _demo():
    ground_truth = generate_facts(40, seed=DEFAULT_CONFIG["seed"])
    snapshots = run_cycles(ground_truth, POLICIES["regenerate"], 6, DEFAULT_CONFIG["seed"])
    audits = audit_snapshots(ground_truth, snapshots)
    print("Consolidation drift demo: 40 facts, regenerate policy, 6 cycles")
    print("")
    print(cycle_table_markdown(audits))
    final = audits[-1]
    print(
        "After 6 cycles: %.1f%% of facts mutated, %d confabulations present."
        % (100.0 * final.mutation_rate, len(final.confabulations))
    )
    return 0


def _audit(args):
    ground_truth = generate_facts(args.facts, seed=args.seed)
    snapshots = run_cycles(
        ground_truth, POLICIES[args.policy], args.cycles, args.seed
    )
    audits = audit_snapshots(ground_truth, snapshots)
    print(audit_report_markdown(args.policy, audits))
    return 0


def _evaluate(args):
    evaluation = run_evaluation(
        {"n_facts": args.facts, "cycles": args.cycles, "seed": args.seed}
    )
    write_results(evaluation, args.outdir)
    print(
        "Wrote evaluation results to %s"
        % os.path.abspath(args.outdir)
    )
    print(json.dumps(evaluation["aggregates"], indent=2, sort_keys=True))
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        return _demo()
    if args.command == "audit":
        return _audit(args)
    if args.command == "evaluate":
        return _evaluate(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
