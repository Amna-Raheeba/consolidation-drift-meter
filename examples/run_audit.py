"""Example: audit a small fact set under two policies and print the
side-by-side drift reports.

Run: python examples/run_audit.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from consolidation_drift.audit import audit_snapshots
from consolidation_drift.models import Fact
from consolidation_drift.policies import POLICIES, run_cycles
from consolidation_drift.report import audit_report_markdown


def main():
    path = os.path.join(os.path.dirname(__file__), "demo_facts.json")
    with open(path) as handle:
        facts = [Fact.from_dict(row) for row in json.load(handle)]
    for name in ("regenerate", "anchor"):
        snapshots = run_cycles(facts, POLICIES[name], 12, 20261121)
        audits = audit_snapshots(facts, snapshots)
        print(audit_report_markdown(name, audits))
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
