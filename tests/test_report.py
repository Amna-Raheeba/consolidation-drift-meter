from consolidation_drift.audit import audit_snapshots
from consolidation_drift.evaluate import run_evaluation
from consolidation_drift.generate import generate_facts
from consolidation_drift.policies import POLICIES, run_cycles
from consolidation_drift.report import (
    audit_report_markdown,
    cycle_table_markdown,
    evaluation_summary_markdown,
    headline_markdown,
)


def test_cycle_table_contains_types():
    facts = generate_facts(30, seed=7)
    snapshots = run_cycles(facts, POLICIES["append"], 3, 7)
    audits = audit_snapshots(facts, snapshots)
    table = cycle_table_markdown(audits)
    assert "certainty_inflation" in table
    assert "confabulation" in table
    assert "| 0 |" in table


def test_audit_report_mentions_policy_and_rates():
    facts = generate_facts(30, seed=7)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 3, 7)
    audits = audit_snapshots(facts, snapshots)
    report = audit_report_markdown("regenerate", audits)
    assert "regenerate-from-scratch" in report
    assert "confabulated" in report


def test_evaluation_summary_sections():
    evaluation = run_evaluation({"n_facts": 40, "cycles": 3, "seed": 7})
    summary = evaluation_summary_markdown(evaluation)
    assert "Detector comparison" in summary
    assert "survival-only" in summary
    assert "anchor" in summary


def test_headline_mentions_certainty_inflation():
    evaluation = run_evaluation({"n_facts": 40, "cycles": 3, "seed": 7})
    headline = headline_markdown(evaluation)
    assert "Certainty inflation" in headline
    assert "Caveat" in headline
