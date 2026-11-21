import pytest

from consolidation_drift.models import (
    CERTAINTY_LABELS,
    CONFABULATION,
    VALUE_DRIFT,
    ATTRIBUTION_LOSS,
    CycleAudit,
    DriftRecord,
    Fact,
    severity_for,
)


def make_fact(**overrides):
    base = {
        "fact_id": "fact-001",
        "subject": "project Atlas",
        "attribute": "status",
        "value": "on track",
        "certainty": 1,
        "source": "project document",
        "timestamp": 100,
        "importance": 2,
        "alternatives": ("at risk", "blocked"),
    }
    base.update(overrides)
    return Fact(**base)


def test_certainty_labels():
    assert len(CERTAINTY_LABELS) == 3
    assert CERTAINTY_LABELS[0] == "uncertain"
    assert CERTAINTY_LABELS[2] == "certain"


def test_severity_confabulation_importance3_is_max():
    assert severity_for(CONFABULATION, 3) == 1.0


def test_severity_increases_with_importance():
    low = severity_for(VALUE_DRIFT, 1)
    mid = severity_for(VALUE_DRIFT, 2)
    high = severity_for(VALUE_DRIFT, 3)
    assert low < mid < high


def test_severity_type_ordering():
    assert severity_for(CONFABULATION, 2) > severity_for(VALUE_DRIFT, 2)
    assert severity_for(VALUE_DRIFT, 2) > severity_for(ATTRIBUTION_LOSS, 2)


def test_severity_unknown_type_raises():
    with pytest.raises(ValueError):
        severity_for("not_a_type", 2)


def test_severity_bad_importance_raises():
    with pytest.raises(ValueError):
        severity_for(VALUE_DRIFT, 4)


def test_fact_origin_defaults_to_own_id():
    fact = make_fact()
    assert fact.origin_id == "fact-001"


def test_confab_fact_keeps_none_origin():
    fact = make_fact(fact_id="confab-001", origin_id=None)
    assert fact.origin_id is None


def test_fact_bad_certainty_raises():
    with pytest.raises(ValueError):
        make_fact(certainty=5)


def test_fact_dict_roundtrip():
    fact = make_fact(pinned=True)
    clone = Fact.from_dict(fact.to_dict())
    assert clone == fact


def test_drift_record_clean_flags():
    record = DriftRecord(fact_id="fact-001", cycle=1)
    assert record.is_clean
    assert not record.is_mutated
    mutated = DriftRecord(fact_id="fact-001", cycle=1, types=(VALUE_DRIFT,))
    assert mutated.is_mutated
    assert not mutated.is_clean


def test_cycle_audit_empty_ground_truth():
    audit = CycleAudit(cycle=0, n_ground_truth=0)
    assert audit.mutation_rate == 0.0
    assert audit.type_rate(VALUE_DRIFT) == 0.0
    assert audit.mean_severity == 0.0
    assert audit.cumulative_mutated_fraction == 0.0
