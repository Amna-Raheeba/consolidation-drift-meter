"""Streamlit dashboard for consolidation-drift-meter.

Three tabs:
1. Drift by policy -- run the seeded simulation for one consolidation
   policy and watch the per-cycle mutation rates by type.
2. Fact lineage -- follow one ground-truth fact through the cycles:
   what it said, and when (and how) it mutated.
3. Evaluation -- the stored headline results (results/evaluation.json).

Run: streamlit run app.py
"""

import json
import os

import streamlit as st

from consolidation_drift.audit import audit_snapshots, fact_lineage
from consolidation_drift.evaluate import DEFAULT_CONFIG
from consolidation_drift.generate import generate_facts
from consolidation_drift.models import CERTAINTY_LABELS, MUTATION_TYPES
from consolidation_drift.policies import POLICIES, run_cycles

st.set_page_config(page_title="Consolidation Drift Meter", layout="wide")

SEED = DEFAULT_CONFIG["seed"]


@st.cache_data
def load_simulation(policy_name, n_facts, cycles):
    ground_truth = generate_facts(n_facts, seed=SEED)
    snapshots = run_cycles(ground_truth, POLICIES[policy_name], cycles, SEED)
    audits = audit_snapshots(ground_truth, snapshots)
    return ground_truth, snapshots, audits


def tab_drift():
    st.header("Drift by policy")
    st.write(
        "Each consolidation cycle, a seeded summariser policy rewrites "
        "the memory. The meter diffs every fact against ground truth "
        "and classifies the mutation. Facts do not just fade: they "
        "mutate, and certainty inflation is the mutation that makes a "
        "surviving fact dangerous."
    )
    col1, col2, col3 = st.columns(3)
    policy_name = col1.selectbox("Consolidation policy", sorted(POLICIES))
    n_facts = col2.slider("Ground-truth facts", 40, 200, 200, 20)
    cycles = col3.slider("Cycles", 2, 12, 12, 1)
    ground_truth, snapshots, audits = load_simulation(policy_name, n_facts, cycles)
    rows = []
    for audit in audits:
        row = {
            "cycle": audit.cycle,
            "mutated": round(audit.mutation_rate, 3),
            "cumulative ever-mutated": round(audit.cumulative_mutated_fraction, 3),
            "mean severity": round(audit.mean_severity, 3),
            "confabulations": len(audit.confabulations),
        }
        for mutation_type in MUTATION_TYPES:
            row[mutation_type] = round(audit.type_rate(mutation_type), 3)
        rows.append(row)
    st.dataframe(rows, use_container_width=True)
    chart_data = {}
    for mutation_type in MUTATION_TYPES:
        chart_data[mutation_type] = [
            audit.type_rate(mutation_type) for audit in audits
        ]
    chart_data["cumulative ever-mutated"] = [
        audit.cumulative_mutated_fraction for audit in audits
    ]
    st.line_chart(chart_data)
    final = audits[-1]
    st.metric(
        "Mutated at final cycle",
        "%.1f%%" % (100.0 * final.mutation_rate),
    )


def tab_lineage():
    st.header("Fact lineage")
    st.write(
        "Pick a fact and a policy; the table shows the fact's stored "
        "state after every cycle and the audit verdict for that cycle."
    )
    col1, col2 = st.columns(2)
    policy_name = col1.selectbox(
        "Consolidation policy", sorted(POLICIES), key="lineage_policy"
    )
    ground_truth, snapshots, audits = load_simulation(policy_name, 200, 12)
    fact_ids = [fact.fact_id for fact in ground_truth]
    chosen = col2.selectbox("Fact", fact_ids)
    gt = [fact for fact in ground_truth if fact.fact_id == chosen][0]
    st.write(
        "Ground truth: %s of %s is %s (certainty %s, source %s, day %d, "
        "importance %d, pinned %s)."
        % (
            gt.attribute,
            gt.subject,
            gt.value,
            CERTAINTY_LABELS[gt.certainty],
            gt.source,
            gt.timestamp,
            gt.importance,
            gt.pinned,
        )
    )
    lineage = fact_lineage(gt, snapshots)
    rows = []
    for entry in lineage:
        rows.append(
            {
                "cycle": entry["cycle"],
                "present": entry["present"],
                "value": entry["value"],
                "certainty": (
                    CERTAINTY_LABELS[entry["certainty"]]
                    if entry["certainty"] is not None
                    else None
                ),
                "source": entry["source"],
                "timestamp": entry["timestamp"],
                "day precision": entry["day_precision"],
                "audit types": ", ".join(entry["types"]) or "clean",
            }
        )
    st.dataframe(rows, use_container_width=True)


def tab_evaluation():
    st.header("Evaluation (stored results)")
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
        "evaluation.json",
    )
    if not os.path.exists(path):
        st.warning("No stored evaluation found at %s" % path)
        return
    with open(path) as handle:
        evaluation = json.load(handle)
    agg = evaluation["aggregates"]
    st.dataframe(
        [
            {"metric": key, "value": value}
            for key, value in sorted(agg.items())
        ],
        use_container_width=True,
    )
    st.write("Detector comparison, final cycle, by policy:")
    rows = []
    for policy_name, base in evaluation["baselines_final_cycle"].items():
        for detector, scores in (
            ("field-level auditor (this tool)", base["auditor"]),
            ("text similarity", base["text_similarity"]),
            ("token cosine", base["token_cosine"]),
            ("survival-only", base["survival_only"]),
        ):
            row = {"policy": policy_name, "detector": detector}
            row.update(scores)
            rows.append(row)
    st.dataframe(rows, use_container_width=True)


tab1, tab2, tab3 = st.tabs(["Drift by policy", "Fact lineage", "Evaluation"])
with tab1:
    tab_drift()
with tab2:
    tab_lineage()
with tab3:
    tab_evaluation()
