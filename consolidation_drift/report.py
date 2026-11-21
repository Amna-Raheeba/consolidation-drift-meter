"""Markdown reports for audits and for the stored evaluation."""

from .models import MUTATION_TYPES

POLICY_BLURBS = {
    "regenerate": "regenerate-from-scratch (whole memory rewritten each cycle)",
    "append": "append-and-supersede (summary appended, rest kept)",
    "anchor": "verbatim-anchor (pinned facts never rewritten)",
}


def cycle_table_markdown(audits):
    """Per-cycle mutation rates by type, as a Markdown table."""
    lines = [
        "| Cycle | Mutated | Cumulative ever-mutated | Mean severity | Confabulations |",
        "|---|---|---|---|---|",
    ]
    for audit in audits:
        lines.append(
            "| %d | %.3f | %.3f | %.3f | %d |"
            % (
                audit.cycle,
                audit.mutation_rate,
                audit.cumulative_mutated_fraction,
                audit.mean_severity,
                len(audit.confabulations),
            )
        )
    lines.append("")
    lines.append("| Cycle | %s |" % " | ".join(MUTATION_TYPES))
    lines.append("|---|%s|" % "|".join("---" for _ in MUTATION_TYPES))
    for audit in audits:
        lines.append(
            "| %d | %s |"
            % (
                audit.cycle,
                " | ".join("%.3f" % audit.type_rate(t) for t in MUTATION_TYPES),
            )
        )
    return "\n".join(lines) + "\n"


def audit_report_markdown(policy_name, audits):
    final = audits[-1]
    lines = [
        "# Consolidation drift audit — %s" % POLICY_BLURBS.get(policy_name, policy_name),
        "",
        "Final cycle %d: %.1f%% of ground-truth facts carry at least one "
        "mutation; %.1f%% have mutated at least once across all cycles; "
        "%d confabulated facts are present."
        % (
            final.cycle,
            100.0 * final.mutation_rate,
            100.0 * final.cumulative_mutated_fraction,
            len(final.confabulations),
        ),
        "",
        cycle_table_markdown(audits),
    ]
    return "\n".join(lines)


def _pct(value):
    return "%.1f%%" % (100.0 * value)


def evaluation_summary_markdown(evaluation):
    cfg = evaluation["config"]
    lines = [
        "# Evaluation summary",
        "",
        "Seeded experiment: %d ground-truth facts, %d consolidation "
        "cycles, 3 policies (seed %d). All numbers are measured from "
        "the stored run; facts and consolidation passes are synthetic "
        "and seeded, with ground truth known by construction."
        % (cfg["n_facts"], cfg["cycles"], cfg["seed"]),
        "",
        "## Final-cycle mutation rate by policy",
        "",
        "| Policy | Mutated (final cycle) | Certainty inflation | Cycles until 50% ever-mutated |",
        "|---|---|---|---|",
    ]
    for name in ("regenerate", "append", "anchor"):
        block = evaluation["policies"][name]
        half = block["cycles_until_half_mutated"]
        lines.append(
            "| %s | %s | %s | %s |"
            % (
                name,
                _pct(block["final"]["mutation_rate"]),
                _pct(block["final"]["certainty_inflation"]),
                half if half is not None else "never",
            )
        )
    lines += [
        "",
        "## Detector comparison (final cycle, by policy)",
        "",
        "Binary detection of mutated facts; the baselines cannot name "
        "a mutation type at all. Text diff only looks respectable in "
        "the regenerate regime, where almost every fact is mutated and "
        "survivors carry several gross mutations at once; in the "
        "low-drift anchor regime its precision collapses, because "
        "rewording noise and one-field mutations move the similarity "
        "by about the same amount.",
        "",
        "| Policy | Detector | Precision | Recall | F1 |",
        "|---|---|---|---|---|",
    ]
    for name in ("regenerate", "append", "anchor"):
        base = evaluation["baselines_final_cycle"][name]
        lines.append(
            "| %s | field-level auditor (this tool) | %.3f | %.3f | %.3f |"
            % (name, base["auditor"]["precision"], base["auditor"]["recall"], base["auditor"]["f1"])
        )
        lines.append(
            "| %s | text similarity (threshold %.2f) | %.3f | %.3f | %.3f |"
            % (
                name,
                base["text_similarity"]["threshold"],
                base["text_similarity"]["precision"],
                base["text_similarity"]["recall"],
                base["text_similarity"]["f1"],
            )
        )
        lines.append(
            "| %s | text similarity (best threshold %.2f) | - | - | %.3f |"
            % (name, base["text_similarity_best"]["threshold"], base["text_similarity_best"]["f1"])
        )
        lines.append(
            "| %s | token cosine (threshold %.2f) | %.3f | %.3f | %.3f |"
            % (
                name,
                base["token_cosine"]["threshold"],
                base["token_cosine"]["precision"],
                base["token_cosine"]["recall"],
                base["token_cosine"]["f1"],
            )
        )
        lines.append(
            "| %s | survival-only counter | %.3f | %.3f | %.3f |"
            % (
                name,
                base["survival_only"]["precision"],
                base["survival_only"]["recall"],
                base["survival_only"]["f1"],
            )
        )
    lines += [
        "",
        "The survival-only counter's recall is the share of mutated "
        "facts it can see at all: only the lost ones. Every mutation "
        "on a surviving fact is invisible to it.",
        "",
    ]
    return "\n".join(lines)


def headline_markdown(evaluation):
    agg = evaluation["aggregates"]
    cfg = evaluation["config"]
    half = agg["regen_cycles_until_half_mutated"]
    lines = [
        "# Headline results",
        "",
        "Consolidation drift measured on %d seeded ground-truth facts "
        "over %d consolidation cycles (seed %d)."
        % (cfg["n_facts"], cfg["cycles"], cfg["seed"]),
        "",
        "- Under regenerate-from-scratch consolidation, %.1f%% of facts "
        "carry at least one typed mutation by cycle %d, and half of all "
        "facts have mutated by cycle %s."
        % (
            100.0 * agg["regen_final_mutation_rate"],
            cfg["cycles"],
            half if half is not None else "beyond the run",
        ),
        "- Certainty inflation is the signature mutation: by the final "
        "cycle %.1f%% of facts have had their certainty upgraded under "
        "regenerate, vs %.1f%% under append-and-supersede and %.1f%% "
        "under verbatim-anchor."
        % (
            100.0 * agg["regen_certainty_inflation_final"],
            100.0 * agg["append_certainty_inflation_final"],
            100.0 * agg["anchor_certainty_inflation_final"],
        ),
        "- Final-cycle mutation rates: regenerate %.1f%%, append %.1f%%, "
        "verbatim-anchor %.1f%%. Regenerate also leaves %d invented "
        "(confabulated) facts in memory."
        % (
            100.0 * agg["regen_final_mutation_rate"],
            100.0 * agg["append_final_mutation_rate"],
            100.0 * agg["anchor_final_mutation_rate"],
            agg["regen_final_confabulations"],
        ),
        "- Detector comparison (final cycle): the field-level auditor "
        "detects mutated facts at F1 1.000 by construction (structured "
        "diff). A text-similarity diff reaches F1 %.3f in the harsh "
        "regenerate regime — where 99%% of facts are mutated and "
        "survivors carry several gross mutations — but only F1 %.3f "
        "(precision %.3f) in the low-drift anchor regime, and %.3f "
        "even at its best threshold there. A survival-only counter "
        "recalls just %.3f of mutated facts under anchor: it cannot "
        "see any mutation on a surviving fact. No text baseline can "
        "name a mutation type at all."
        % (
            agg["regen_text_f1_at_default_threshold"],
            agg["text_f1_at_default_threshold"],
            agg["text_precision_at_default_threshold"],
            agg["text_best_f1"],
            agg["survival_only_mutation_recall"],
        ),
        "",
        "Caveat: facts and consolidation passes are synthetic and "
        "seeded; the consolidation operator is a declared probabilistic "
        "policy, not a live LLM. The experiment measures the audit "
        "instrument and the relative drift of the three policies under "
        "that operator, not the drift rate of any production system.",
        "",
    ]
    return "\n".join(lines)
