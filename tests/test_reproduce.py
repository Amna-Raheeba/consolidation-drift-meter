import copy
import subprocess
import sys

from consolidation_drift.evaluate import DRIFT_KEYS, check_drift, run_evaluation

SMALL = {"n_facts": 60, "cycles": 5, "seed": 20261121}


def test_check_drift_identical_passes():
    evaluation = run_evaluation(SMALL)
    ok, problems = check_drift(evaluation, evaluation)
    assert ok
    assert problems == []


def test_check_drift_detects_perturbation():
    evaluation = run_evaluation(SMALL)
    perturbed = copy.deepcopy(evaluation)
    perturbed["aggregates"]["regen_final_mutation_rate"] -= 0.5
    ok, problems = check_drift(evaluation, perturbed)
    assert not ok
    keys = [problem[0] for problem in problems]
    assert "regen_final_mutation_rate" in keys


def test_check_drift_missing_key_fails():
    evaluation = run_evaluation(SMALL)
    broken = copy.deepcopy(evaluation)
    del broken["aggregates"][DRIFT_KEYS[0]]
    ok, problems = check_drift(evaluation, broken)
    assert not ok


def test_reproduce_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/reproduce_results.py"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout
