import copy

from consolidation_drift.audit import (
    audit_memory,
    audit_snapshots,
    classify_fact,
    cycles_until_half_mutated,
    fact_lineage,
)
from consolidation_drift.generate import generate_facts
from consolidation_drift.models import (
    ATTRIBUTION_LOSS,
    CERTAINTY_INFLATION,
    CONFABULATION,
    LOSS,
    TEMPORAL_FLATTENING,
    VALUE_DRIFT,
    CycleAudit,
    Fact,
)
from consolidation_drift.policies import POLICIES, run_cycles

SEED = 20261121


def gt_fact(**overrides):
    base = {
        "fact_id": "fact-001",
        "subject": "project Atlas",
        "attribute": "status",
        "value": "on track",
        "certainty": 1,
        "source": "project document",
        "timestamp": 100,
        "importance": 3,
        "alternatives": ("at risk", "blocked"),
    }
    base.update(overrides)
    return Fact(**base)


def test_classify_clean():
    gt = gt_fact()
    assert classify_fact(gt, copy.deepcopy(gt)) == ()


def test_classify_value_drift():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.value = "at risk"
    assert classify_fact(gt, mem) == (VALUE_DRIFT,)


def test_classify_certainty_inflation():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.certainty = 2
    assert classify_fact(gt, mem) == (CERTAINTY_INFLATION,)


def test_classify_certainty_same_or_lower_is_not_inflation():
    gt = gt_fact(certainty=2)
    mem = copy.deepcopy(gt)
    mem.certainty = 1
    assert CERTAINTY_INFLATION not in classify_fact(gt, mem)


def test_classify_attribution_loss():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.source = None
    assert classify_fact(gt, mem) == (ATTRIBUTION_LOSS,)


def test_classify_temporal_flattening_by_precision():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.day_precision = False
    mem.timestamp = 90
    assert classify_fact(gt, mem) == (TEMPORAL_FLATTENING,)


def test_classify_temporal_flattening_by_timestamp_move():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.timestamp = 101
    assert classify_fact(gt, mem) == (TEMPORAL_FLATTENING,)


def test_classify_multiple_types():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.value = "blocked"
    mem.certainty = 2
    mem.source = None
    types = classify_fact(gt, mem)
    assert set(types) == {VALUE_DRIFT, CERTAINTY_INFLATION, ATTRIBUTION_LOSS}


def test_audit_loss():
    gt = gt_fact()
    audit = audit_memory([gt], [], 1)
    assert audit.records[0].types == (LOSS,)
    assert audit.mutation_rate == 1.0


def test_audit_confabulation():
    gt = gt_fact()
    confab = Fact(
        fact_id="confab-001",
        subject="user",
        attribute="favourite colour",
        value="teal",
        certainty=2,
        source=None,
        timestamp=10,
        importance=2,
        origin_id=None,
    )
    audit = audit_memory([gt], [copy.deepcopy(gt), confab], 1)
    assert audit.records[0].is_clean
    assert len(audit.confabulations) == 1
    assert audit.confabulations[0].types == (CONFABULATION,)
    assert audit.confabulations[0].severity > 0


def test_audit_severity_worst_type_wins():
    gt = gt_fact()
    mem = copy.deepcopy(gt)
    mem.value = "blocked"
    mem.source = None
    audit = audit_memory([gt], [mem], 1)
    # value drift (0.9) beats attribution loss (0.4) at importance 3.
    assert audit.records[0].severity == 0.9


def test_audit_ever_mutated_threads():
    facts = generate_facts(40, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 6, SEED)
    audits = audit_snapshots(facts, snapshots)
    fractions = [a.cumulative_mutated_fraction for a in audits]
    assert fractions == sorted(fractions)
    assert fractions[-1] >= audits[-1].mutation_rate


def test_cycles_until_half_mutated_synthetic():
    def make(cycle, ever):
        return CycleAudit(
            cycle=cycle, n_ground_truth=10, ever_mutated=frozenset(ever)
        )

    audits = [make(0, ()), make(1, (1, 2)), make(2, (1, 2, 3, 4, 5))]
    assert cycles_until_half_mutated(audits) == 2
    assert cycles_until_half_mutated(audits[:2]) is None


def test_fact_lineage_pinned_anchor_stays_clean():
    facts = generate_facts(60, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["anchor"], 5, SEED)
    pinned = [f for f in facts if f.pinned][0]
    lineage = fact_lineage(pinned, snapshots)
    assert len(lineage) == 6
    for entry in lineage:
        assert entry["present"]
        assert entry["types"] == []
        assert entry["value"] == pinned.value


def test_fact_lineage_structure():
    facts = generate_facts(60, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 5, SEED)
    lineage = fact_lineage(facts[0], snapshots)
    assert [entry["cycle"] for entry in lineage] == [0, 1, 2, 3, 4, 5]
    assert lineage[0]["types"] == []
