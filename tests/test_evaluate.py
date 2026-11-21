from consolidation_drift.evaluate import (
    DRIFT_KEYS,
    evaluation_csv,
    run_evaluation,
)

SMALL = {"n_facts": 60, "cycles": 5, "seed": 20261121}


def test_run_evaluation_structure():
    evaluation = run_evaluation(SMALL)
    assert set(evaluation["policies"]) == {"regenerate", "append", "anchor"}
    for block in evaluation["policies"].values():
        assert len(block["per_cycle"]) == 6  # cycles 0..5
    assert set(evaluation["baselines_final_cycle"]) == {
        "regenerate",
        "append",
        "anchor",
    }


def test_aggregates_present():
    evaluation = run_evaluation(SMALL)
    for key in DRIFT_KEYS:
        assert key in evaluation["aggregates"]


def test_policy_ordering_small():
    evaluation = run_evaluation(SMALL)
    agg = evaluation["aggregates"]
    assert (
        agg["regen_final_mutation_rate"]
        > agg["append_final_mutation_rate"]
        > agg["anchor_final_mutation_rate"]
    )


def test_certainty_inflation_ordering_small():
    evaluation = run_evaluation(SMALL)
    agg = evaluation["aggregates"]
    assert (
        agg["regen_certainty_inflation_final"]
        > agg["anchor_certainty_inflation_final"]
    )


def test_baseline_anchor_text_f1_below_auditor():
    evaluation = run_evaluation(SMALL)
    base = evaluation["baselines_final_cycle"]["anchor"]
    assert base["auditor"]["f1"] == 1.0
    assert base["text_similarity"]["f1"] < 1.0
    assert base["survival_only"]["recall"] < 0.5


def test_evaluation_csv_shape():
    evaluation = run_evaluation(SMALL)
    text = evaluation_csv(evaluation)
    lines = text.strip().splitlines()
    assert lines[0] == "policy,cycle,mutation_type,rate"
    # 3 policies x 6 cycles x 6 types + header
    assert len(lines) == 1 + 3 * 6 * 6
