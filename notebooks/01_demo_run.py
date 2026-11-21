"""Notebook 01 -- demo run (runnable as a plain script).

Runs a small consolidation simulation: 40 ground-truth facts, the
regenerate-from-scratch policy, 6 cycles, and prints the per-cycle
drift table produced by the meter.

Run: python notebooks/01_demo_run.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from consolidation_drift.audit import audit_snapshots
from consolidation_drift.evaluate import DEFAULT_CONFIG
from consolidation_drift.generate import generate_facts
from consolidation_drift.policies import POLICIES, run_cycles
from consolidation_drift.report import cycle_table_markdown


def main():
    ground_truth = generate_facts(40, seed=DEFAULT_CONFIG["seed"])
    snapshots = run_cycles(
        ground_truth, POLICIES["regenerate"], 6, DEFAULT_CONFIG["seed"]
    )
    audits = audit_snapshots(ground_truth, snapshots)
    print("Demo: 40 facts, regenerate policy, 6 consolidation cycles")
    print("")
    print(cycle_table_markdown(audits))
    final = audits[-1]
    print(
        "Headline of the demo: %.1f%% of facts mutated by cycle 6; "
        "certainty inflation alone touches %.1f%%."
        % (
            100.0 * final.mutation_rate,
            100.0 * final.type_rate("certainty_inflation"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
