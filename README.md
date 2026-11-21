# Consolidation Drift Meter

Facts don't just fade, they mutate. This tool measures how an agent's
long-term memory facts change every time the memory is consolidated
(summarised into itself): it diffs each fact against ground truth at
field level after every cycle, classifies the change with a typed
mutation taxonomy, scores its severity, and compares consolidation
policies by *how* their facts drift — not just how many survive.

Author: Amna Raheeba. MIT license. Pure Python stdlib; no API keys, no
model downloads, no network. Fully deterministic and seeded.

## 1. What it is

Agent memory systems periodically consolidate: old entries are
summarised, merged and rewritten to keep the store small. The standard
health metric for that process is survival — what fraction of facts is
still there afterwards (practitioner estimates put it near 0.85 per
regeneration). Survival hides the dangerous half of the story: a fact
that *survives but mutates*. A deadline that quietly moves, a "may"
that becomes "definitely", a source that evaporates — the memory still
answers confidently, and it answers wrong.

The Consolidation Drift Meter is an offline audit instrument for that
process. Facts enter memory with known ground-truth value, certainty,
source and timestamp. A seeded consolidation policy rewrites the
memory cycle after cycle, and after every cycle the meter diffs the
whole memory against ground truth and reports, per fact and per
cycle, exactly what kind of drift happened.

## 2. The novel mechanism

**A typed mutation taxonomy over field-level diffs.** Every surviving
fact is classified into one or more of:

| Type | Meaning |
|---|---|
| `loss` | the fact is gone from memory |
| `value_drift` | the stored value differs from ground truth |
| `certainty_inflation` | certainty was upgraded (uncertain → likely → certain) |
| `attribution_loss` | the source was dropped |
| `temporal_flattening` | a day-precise date collapsed to month precision |
| `confabulation` | a fact exists that has no ground-truth origin |

Each mutation is severity-scored (type weight × importance), each
fact's lineage is tracked across all cycles, and the meter reports
per-cycle mutation rates by type, the cumulative ever-mutated
fraction, and the cycle at which half of all facts have mutated.

**Three consolidation policies are compared under the same operator
family:** regenerate-from-scratch (whole memory rewritten each cycle,
pinned facts unprotected), append-and-supersede (summary appended,
lower rewrite rates), and verbatim-anchor (pinned facts are never
rewritten; the rest drift slowly; no confabulation).

**The baselines are the point.** The meter is benchmarked against what
pipelines actually use: a text-similarity diff over rendered memory
text, a bag-of-words cosine diff, and a survival-only counter. The
baselines can only answer "changed / unchanged" — none can name a
mutation type — and §4 shows their detection quality collapses
exactly in the low-drift regime where an audit matters most.

## 3. Prior art and the differentiator

SSGM (Stability and Safety Governed Memory) is a conceptual governance
framework that names semantic drift as a risk; it ships no measurement
tool and no mutation taxonomy. Practitioner analyses estimate
aggregate recall decay per regeneration but never classify *how*
facts change. The portfolio's own governed-shared-memory governs
provenance at write/read time, and memory-autopsy does post-mortem
blame for a finished run; neither measures the consolidation operator
itself. Differentiator: per-cycle, per-type, per-fact drift
measurement with lineage — drift as a typed, severity-scored signal,
not a single survival number.

## 4. Measured headline results

Seeded experiment: 200 ground-truth facts × 12 consolidation cycles ×
3 policies (seed 20261121; `results/evaluation.json`).

- **Regenerate-from-scratch destroys memory fast:** 99.0% of facts
  carry at least one mutation by cycle 12, and half of all facts have
  mutated by **cycle 2**. It also leaves **36 confabulated facts** in
  memory.
- **Final-cycle mutation rates:** regenerate 99.0%, append 89.5%,
  verbatim-anchor 59.0%. Cycles until 50% of facts have ever mutated:
  2 (regenerate), 4 (append), 10 (anchor).
- **Certainty inflation is the signature mutation.** Final-cycle
  rates: regenerate **38.0%**, append 28.0%, verbatim-anchor 12.5% —
  under the harshest policy, more than a third of the memory asserts
  things more confidently than they were ever known.
- **Per-type rates at cycle 12 (regenerate):** attribution loss
  48.0%, loss 45.5%, temporal flattening 45.0%, value drift 39.5%,
  certainty inflation 38.0%. Under verbatim-anchor the same rates are
  21.5%, 8.0%, 15.5%, 17.5% and 12.5% — anchoring helps everywhere,
  but does not stop drift on unpinned facts.
- **Detector comparison (final cycle):** the field-level auditor
  detects mutated facts at F1 1.000 by construction (structured
  diff). A text-similarity diff reaches F1 0.987 in the regenerate
  regime — where 99% of facts are mutated and survivors carry several
  gross mutations — but only **F1 0.711 (precision 0.626)** in the
  low-drift anchor regime, and 0.803 even at its best threshold there:
  rewording noise and a one-field mutation move text similarity by
  about the same amount. A survival-only counter recalls just **0.136**
  of mutated facts under anchor, because it cannot see any mutation on
  a surviving fact.

## 5. Quick start

```bash
pip install -r requirements.txt
python -m consolidation_drift demo          # small 40-fact demo
python -m consolidation_drift audit --policy regenerate --cycles 12
python -m consolidation_drift evaluate --outdir results
streamlit run app.py                        # dashboard
pytest -q                                   # test suite
```

## 6. How it works

1. `generate.py` builds the ground-truth fact set from a fixed slot
   pool (subject, attribute, plausible values), assigning certainty,
   source, timestamp, importance, alternatives and a pinned flag.
2. `policies.py` applies one consolidation cycle: per fact, seeded
   operators drop, corrupt, inflate, strip or flatten fields, and the
   policy may invent confabulated facts. Mutations are sticky — once
   drifted, a field stays drifted — matching how a rewritten memory
   entry becomes the next cycle's input.
3. `audit.py` diffs every memory fact against its ground-truth
   ancestor (lineage via `origin_id`), classifies the mutation types,
   and scores severity.
4. `evaluate.py` runs the full grid, scores the baselines against the
   auditor's mutated set, and writes `results/`.
5. `baselines.py` renders facts to text (with per-cycle rewording, as
   a summariser would) for the text-similarity and cosine baselines.

## 7. Repository layout

```
consolidation_drift/   package: models, generate, policies, audit,
                       baselines, evaluate, report, cli
data/                  canonical ground-truth + demo fact sets (JSON)
examples/              demo facts, run_audit.py, sample_report.md
notebooks/             01_demo_run.py, 02_evaluation_experiment.py
scripts/               build_cases.py, reproduce_results.py
results/               evaluation.json/.csv, evaluation_summary.md,
                       HEADLINE.md
tests/                 pytest suite
app.py                 Streamlit dashboard (drift, lineage, evaluation)
```

## 8. Honest limits

- Facts and consolidation passes are **synthetic and seeded**. The
  consolidation operator is a declared probabilistic policy with
  stated per-type rates, not a live LLM summariser; the experiment
  measures the audit instrument and the *relative* drift of the three
  policies under that operator, not the drift rate of any production
  memory system.
- The auditor's F1 of 1.000 is **by construction**: it diffs
  structured fields against known ground truth. That is the intended
  scope — an increasing share of agent memory stores *are* structured
  fact stores — but on free-text memory the field extraction problem
  returns, and the text baselines in §4 are the honest picture of that
  harder setting.
- Mutations are modelled as independent per fact and per cycle, and
  certainty only inflates (never deflates) under these policies; real
  summarisers also merge facts, split facts and drift correlated
  clusters together. Those operators are future work.
- Severity weights are declared constants, not fitted values; they
  encode the judgement that confabulation and value drift are worse
  than attribution loss. Rankings between policies do not depend on
  the exact weights (the per-type rates are reported separately).

## 9. Reproducing the results

```bash
python scripts/build_cases.py        # rebuild data/ from the seed
python -m consolidation_drift evaluate --outdir results
python scripts/reproduce_results.py  # drift guard: PASS/FAIL
```

## 10. License

MIT — see `LICENSE`.
