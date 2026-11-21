"""The headline experiment.

200 ground-truth facts x 12 consolidation cycles x 3 policies, all
seeded. For every policy the meter reports the per-cycle mutation rate
by type, the final certainty-inflation rate, the mean severity and the
first cycle at which half of all facts have mutated at least once.
Baselines are scored against the auditor on the final cycle of the
regenerate policy (the harshest): binary detection precision / recall
/ F1, plus the text baseline's best F1 over a threshold sweep so the
baseline is judged at its most favourable setting too. Baselines are
scored at the final cycle of every policy, because detection quality
depends on the drift regime: text diff only looks good when almost
every fact is mutated and survivors carry several gross mutations at
once; in the low-drift anchor regime its precision collapses.
"""

import csv
import io
import json
import os

from .audit import audit_snapshots, cycles_until_half_mutated
from .baselines import (
    SurvivalOnlyBaseline,
    TextSimilarityBaseline,
    TokenCosineBaseline,
    detection_scores,
)
from .generate import generate_facts
from .models import MUTATION_TYPES
from .policies import POLICIES, run_cycles

DEFAULT_CONFIG = {
    "n_facts": 200,
    "cycles": 12,
    "seed": 20261121,
    "policies": ["regenerate", "append", "anchor"],
}

# Aggregates compared by scripts/reproduce_results.py.
DRIFT_KEYS = (
    "regen_final_mutation_rate",
    "append_final_mutation_rate",
    "anchor_final_mutation_rate",
    "regen_certainty_inflation_final",
    "anchor_certainty_inflation_final",
    "regen_cycles_until_half_mutated",
    "text_f1_at_default_threshold",
    "text_best_f1",
    "survival_only_mutation_recall",
)

DRIFT_TOLERANCE = 0.02


def _policy_block(ground_truth, policy, cycles, seed):
    snapshots = run_cycles(ground_truth, policy, cycles, seed)
    audits = audit_snapshots(ground_truth, snapshots)
    per_cycle = []
    for audit in audits:
        row = {
            "cycle": audit.cycle,
            "mutation_rate": round(audit.mutation_rate, 4),
            "cumulative_mutated_fraction": round(
                audit.cumulative_mutated_fraction, 4
            ),
            "mean_severity": round(audit.mean_severity, 4),
            "n_confabulations": len(audit.confabulations),
        }
        for mutation_type in MUTATION_TYPES:
            row[mutation_type] = round(audit.type_rate(mutation_type), 4)
        # Confabulations are additions, not mutations of a GT fact:
        # report them as a rate relative to the ground-truth size.
        row["confabulation"] = round(
            len(audit.confabulations) / float(len(ground_truth)), 4
        )
        per_cycle.append(row)
    final = audits[-1]
    return {
        "per_cycle": per_cycle,
        "final": per_cycle[-1],
        "cycles_until_half_mutated": cycles_until_half_mutated(audits),
        "snapshots": snapshots,
        "audits": audits,
        "final_audit": final,
    }


def _baseline_block(ground_truth, snapshots, audits, cycle):
    final_memory = snapshots[cycle]
    final_audit = audits[cycle]
    mutated_ids = set(r.fact_id for r in final_audit.records if r.is_mutated)
    all_ids = set(gt.fact_id for gt in ground_truth)

    text = TextSimilarityBaseline()
    text_scores = detection_scores(
        text.flag_changed(ground_truth, final_memory, cycle), mutated_ids, all_ids
    )
    best_f1 = -1.0
    best_threshold = None
    for step in range(0, 30):
        threshold = 0.70 + 0.01 * step
        candidate = TextSimilarityBaseline(threshold=threshold)
        scores = detection_scores(
            candidate.flag_changed(ground_truth, final_memory, cycle),
            mutated_ids,
            all_ids,
        )
        if scores["f1"] > best_f1:
            best_f1 = scores["f1"]
            best_threshold = threshold
    cosine = TokenCosineBaseline()
    cosine_scores = detection_scores(
        cosine.flag_changed(ground_truth, final_memory, cycle),
        mutated_ids,
        all_ids,
    )
    survival = SurvivalOnlyBaseline()
    survival_scores = detection_scores(
        survival.flag_changed(ground_truth, final_memory, cycle),
        mutated_ids,
        all_ids,
    )
    return {
        "cycle": cycle,
        "text_similarity": dict(
            text_scores, threshold=text.threshold
        ),
        "text_similarity_best": {"f1": best_f1, "threshold": best_threshold},
        "token_cosine": dict(cosine_scores, threshold=cosine.threshold),
        "survival_only": survival_scores,
        "auditor": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
    }


def run_evaluation(config=None):
    """Run the full experiment; return the results dict (JSON-safe
    except for the per-policy internals, which are stripped)."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    ground_truth = generate_facts(cfg["n_facts"], seed=cfg["seed"])
    policies_out = {}
    internals = {}
    for name in cfg["policies"]:
        block = _policy_block(
            ground_truth, POLICIES[name], cfg["cycles"], cfg["seed"]
        )
        internals[name] = block
        policies_out[name] = {
            "per_cycle": block["per_cycle"],
            "final": block["final"],
            "cycles_until_half_mutated": block["cycles_until_half_mutated"],
        }
    regen = internals["regenerate"]
    baselines = {
        name: _baseline_block(
            ground_truth,
            internals[name]["snapshots"],
            internals[name]["audits"],
            cfg["cycles"],
        )
        for name in cfg["policies"]
    }
    anchor_base = baselines["anchor"]
    aggregates = {
        "regen_final_mutation_rate": regen["final"]["mutation_rate"],
        "append_final_mutation_rate": internals["append"]["final"]["mutation_rate"],
        "anchor_final_mutation_rate": internals["anchor"]["final"]["mutation_rate"],
        "regen_certainty_inflation_final": regen["final"]["certainty_inflation"],
        "append_certainty_inflation_final": internals["append"]["final"][
            "certainty_inflation"
        ],
        "anchor_certainty_inflation_final": internals["anchor"]["final"][
            "certainty_inflation"
        ],
        "regen_cycles_until_half_mutated": regen["cycles_until_half_mutated"],
        "append_cycles_until_half_mutated": internals["append"][
            "cycles_until_half_mutated"
        ],
        "anchor_cycles_until_half_mutated": internals["anchor"][
            "cycles_until_half_mutated"
        ],
        "regen_final_confabulations": regen["final"]["n_confabulations"],
        # Baseline aggregates are taken from the anchor (low-drift)
        # regime, where detection is actually hard; the full
        # per-policy baseline table is in baselines_final_cycle.
        "text_f1_at_default_threshold": anchor_base["text_similarity"]["f1"],
        "text_precision_at_default_threshold": anchor_base["text_similarity"][
            "precision"
        ],
        "text_best_f1": anchor_base["text_similarity_best"]["f1"],
        "text_best_threshold": anchor_base["text_similarity_best"]["threshold"],
        "cosine_f1_at_default_threshold": anchor_base["token_cosine"]["f1"],
        "survival_only_mutation_recall": anchor_base["survival_only"]["recall"],
        "regen_text_f1_at_default_threshold": baselines["regenerate"][
            "text_similarity"
        ]["f1"],
    }
    return {
        "config": cfg,
        "policies": policies_out,
        "baselines_final_cycle": baselines,
        "aggregates": aggregates,
    }


def evaluation_csv(evaluation):
    """Long-format CSV: one row per policy x cycle x mutation type."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["policy", "cycle", "mutation_type", "rate"])
    for name, block in evaluation["policies"].items():
        for row in block["per_cycle"]:
            for mutation_type in MUTATION_TYPES:
                writer.writerow([name, row["cycle"], mutation_type, row[mutation_type]])
    return buffer.getvalue()


def write_results(evaluation, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "evaluation.json"), "w") as handle:
        json.dump(evaluation, handle, indent=2, sort_keys=True)
    with open(os.path.join(outdir, "evaluation.csv"), "w") as handle:
        handle.write(evaluation_csv(evaluation))
    from .report import evaluation_summary_markdown, headline_markdown

    with open(os.path.join(outdir, "evaluation_summary.md"), "w") as handle:
        handle.write(evaluation_summary_markdown(evaluation))
    with open(os.path.join(outdir, "HEADLINE.md"), "w") as handle:
        handle.write(headline_markdown(evaluation))


def check_drift(stored, fresh, tolerance=DRIFT_TOLERANCE):
    """Compare DRIFT_KEYS aggregates between two evaluation dicts."""
    problems = []
    for key in DRIFT_KEYS:
        stored_value = stored.get("aggregates", {}).get(key)
        fresh_value = fresh.get("aggregates", {}).get(key)
        if stored_value is None and fresh_value is None:
            continue
        if stored_value is None or fresh_value is None:
            problems.append((key, stored_value, fresh_value, None))
            continue
        if isinstance(stored_value, (int, float)) and isinstance(
            fresh_value, (int, float)
        ):
            diff = abs(stored_value - fresh_value)
            if diff > tolerance:
                problems.append((key, stored_value, fresh_value, diff))
        elif stored_value != fresh_value:
            problems.append((key, stored_value, fresh_value, None))
    return (len(problems) == 0), problems
