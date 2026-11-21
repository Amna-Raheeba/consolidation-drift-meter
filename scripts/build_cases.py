"""Build the committed data files: the canonical ground-truth fact
set and a small demo set, both generated with the canonical seed.

Run: python scripts/build_cases.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from consolidation_drift.evaluate import DEFAULT_CONFIG
from consolidation_drift.generate import generate_facts


def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    facts = generate_facts(
        DEFAULT_CONFIG["n_facts"], seed=DEFAULT_CONFIG["seed"]
    )
    with open(os.path.join(data_dir, "ground_truth_facts.json"), "w") as handle:
        json.dump([fact.to_dict() for fact in facts], handle, indent=2)
    demo = generate_facts(12, seed=DEFAULT_CONFIG["seed"])
    with open(os.path.join(data_dir, "demo_facts.json"), "w") as handle:
        json.dump([fact.to_dict() for fact in demo], handle, indent=2)
    examples_dir = os.path.join(root, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    with open(os.path.join(examples_dir, "demo_facts.json"), "w") as handle:
        json.dump([fact.to_dict() for fact in demo], handle, indent=2)
    print(
        "Wrote %d ground-truth facts and %d demo facts."
        % (len(facts), len(demo))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
