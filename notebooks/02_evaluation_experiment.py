"""Notebook 02 -- the headline evaluation experiment (runnable as a
plain script).

Runs the full seeded experiment (200 facts x 12 cycles x 3 policies)
and prints the aggregate headline numbers. It does not overwrite the
stored results; use `python -m consolidation_drift evaluate` for that.

Run: python notebooks/02_evaluation_experiment.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from consolidation_drift.evaluate import run_evaluation


def main():
    evaluation = run_evaluation()
    print("Aggregates:")
    print(json.dumps(evaluation["aggregates"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
