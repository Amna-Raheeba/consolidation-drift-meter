import pytest

from consolidation_drift.generate import SOURCES, generate_facts


def test_count():
    assert len(generate_facts(200, seed=1)) == 200
    assert len(generate_facts(5, seed=1)) == 5
    assert len(generate_facts(1, seed=1)) == 1


def test_zero_facts_raises():
    with pytest.raises(ValueError):
        generate_facts(0)


def test_determinism():
    first = [f.to_dict() for f in generate_facts(50, seed=42)]
    second = [f.to_dict() for f in generate_facts(50, seed=42)]
    assert first == second


def test_different_seeds_differ():
    first = [f.to_dict() for f in generate_facts(50, seed=1)]
    second = [f.to_dict() for f in generate_facts(50, seed=2)]
    assert first != second


def test_unique_ids_and_keys():
    facts = generate_facts(200, seed=3)
    assert len(set(f.fact_id for f in facts)) == 200
    assert len(set(f.key() for f in facts)) == 200


def test_alternatives_exclude_value():
    for fact in generate_facts(200, seed=3):
        assert fact.value not in fact.alternatives
        assert len(fact.alternatives) == 3


def test_field_ranges():
    for fact in generate_facts(200, seed=3):
        assert fact.certainty in (0, 1, 2)
        assert fact.importance in (1, 2, 3)
        assert 0 <= fact.timestamp < 300
        assert fact.source in SOURCES
        assert fact.day_precision is True


def test_pinned_share():
    facts = generate_facts(200, seed=3)
    pinned = [f for f in facts if f.pinned]
    assert 20 <= len(pinned) <= 40
