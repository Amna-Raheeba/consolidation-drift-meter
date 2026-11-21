import pytest

from consolidation_drift.audit import audit_snapshots
from consolidation_drift.generate import generate_facts
from consolidation_drift.policies import POLICIES, initial_memory, run_cycles

SEED = 20261121


def test_initial_memory_is_a_copy():
    facts = generate_facts(10, seed=SEED)
    memory = initial_memory(facts)
    memory[0].value = "tampered"
    assert facts[0].value != "tampered"


def test_run_cycles_length_and_cycle0_clean():
    facts = generate_facts(40, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 4, SEED)
    assert len(snapshots) == 5
    audits = audit_snapshots(facts, snapshots)
    assert audits[0].mutation_rate == 0.0
    assert audits[0].n_clean == 40


def test_negative_cycles_raises():
    facts = generate_facts(10, seed=SEED)
    with pytest.raises(ValueError):
        run_cycles(facts, POLICIES["append"], -1, SEED)


def test_determinism():
    facts = generate_facts(40, seed=SEED)
    first = run_cycles(facts, POLICIES["append"], 5, SEED)
    second = run_cycles(facts, POLICIES["append"], 5, SEED)
    assert [[f.to_dict() for f in snap] for snap in first] == [
        [f.to_dict() for f in snap] for snap in second
    ]


def test_anchor_never_mutates_pinned():
    facts = generate_facts(200, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["anchor"], 12, SEED)
    audits = audit_snapshots(facts, snapshots)
    pinned_ids = set(f.fact_id for f in facts if f.pinned)
    assert pinned_ids
    for audit in audits:
        for record in audit.records:
            if record.fact_id in pinned_ids:
                assert record.is_clean


def test_regenerate_does_mutate_some_pinned():
    facts = generate_facts(200, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 12, SEED)
    audits = audit_snapshots(facts, snapshots)
    pinned_ids = set(f.fact_id for f in facts if f.pinned)
    final = audits[-1]
    mutated_pinned = [
        r for r in final.records if r.fact_id in pinned_ids and r.is_mutated
    ]
    assert mutated_pinned


def test_confabulation_counts_per_policy():
    facts = generate_facts(60, seed=SEED)
    for name, expected_per_cycle in (("regenerate", 3), ("append", 1), ("anchor", 0)):
        snapshots = run_cycles(facts, POLICIES[name], 4, SEED)
        audits = audit_snapshots(facts, snapshots)
        assert len(audits[-1].confabulations) == expected_per_cycle * 4


def test_presence_is_monotone():
    facts = generate_facts(60, seed=SEED)
    for policy in POLICIES.values():
        snapshots = run_cycles(facts, policy, 6, SEED)
        previous = None
        for snap in snapshots:
            present = set(f.origin_id for f in snap if f.origin_id is not None)
            if previous is not None:
                assert present <= previous
            previous = present


def test_certainty_never_decreases_for_survivors():
    facts = generate_facts(60, seed=SEED)
    snapshots = run_cycles(facts, POLICIES["regenerate"], 6, SEED)
    last_seen = {}
    for snap in snapshots:
        for fact in snap:
            if fact.origin_id is None:
                continue
            if fact.origin_id in last_seen:
                assert fact.certainty >= last_seen[fact.origin_id]
            last_seen[fact.origin_id] = fact.certainty


def test_policy_ordering_final_mutation():
    facts = generate_facts(200, seed=SEED)
    rates = {}
    for name, policy in POLICIES.items():
        snapshots = run_cycles(facts, policy, 12, SEED)
        audits = audit_snapshots(facts, snapshots)
        rates[name] = audits[-1].mutation_rate
    assert rates["regenerate"] > rates["append"] > rates["anchor"]
