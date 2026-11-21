from consolidation_drift.baselines import (
    SurvivalOnlyBaseline,
    TextSimilarityBaseline,
    TokenCosineBaseline,
    detection_scores,
    render_fact,
    token_cosine,
)
from consolidation_drift.generate import generate_facts
from consolidation_drift.models import Fact
from consolidation_drift.policies import initial_memory

SEED = 20261121


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
        "alternatives": ("at risk",),
    }
    base.update(overrides)
    return Fact(**base)


def test_render_deterministic():
    fact = make_fact()
    assert render_fact(fact, cycle=3) == render_fact(fact, cycle=3)


def test_render_contains_value_and_subject():
    text = render_fact(make_fact(), cycle=0)
    assert "on track" in text
    assert "project Atlas" in text


def test_render_variants_differ_for_some_cycle():
    fact = make_fact()
    texts = set(render_fact(fact, cycle=c) for c in range(6))
    assert len(texts) > 1


def test_render_omits_source_clause_when_source_missing():
    with_source = render_fact(make_fact(), cycle=0)
    without = render_fact(make_fact(source=None), cycle=0)
    assert "project document" in with_source
    assert "project document" not in without


def test_token_cosine_identical_is_one():
    text = "the deadline is march"
    assert token_cosine(text, text) == 1.0


def test_token_cosine_disjoint_is_zero():
    assert token_cosine("alpha beta", "gamma delta") == 0.0


def test_text_baseline_clean_memory_flags_nothing():
    facts = generate_facts(30, seed=SEED)
    baseline = TextSimilarityBaseline()
    flagged = baseline.flag_changed(facts, initial_memory(facts), 0)
    assert flagged == set()


def test_text_baseline_flags_missing_fact():
    facts = generate_facts(30, seed=SEED)
    memory = initial_memory(facts)[1:]
    baseline = TextSimilarityBaseline()
    flagged = baseline.flag_changed(facts, memory, 0)
    assert flagged == {facts[0].fact_id}


def test_cosine_baseline_flags_missing_fact():
    facts = generate_facts(30, seed=SEED)
    memory = initial_memory(facts)[1:]
    baseline = TokenCosineBaseline()
    flagged = baseline.flag_changed(facts, memory, 0)
    assert flagged == {facts[0].fact_id}


def test_survival_baseline_flags_exactly_the_lost():
    facts = generate_facts(30, seed=SEED)
    memory = initial_memory(facts)
    dropped = {memory[2].fact_id, memory[5].fact_id}
    memory = [f for f in memory if f.fact_id not in dropped]
    baseline = SurvivalOnlyBaseline()
    assert baseline.flag_changed(facts, memory, 3) == dropped


def test_detection_scores_perfect():
    scores = detection_scores({"a", "b"}, {"a", "b"}, {"a", "b", "c"})
    assert scores == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_detection_scores_partial():
    scores = detection_scores({"a", "x"}, {"a", "b"}, {"a", "b", "x"})
    assert scores["precision"] == 0.5
    assert scores["recall"] == 0.5
    assert scores["f1"] == 0.5
