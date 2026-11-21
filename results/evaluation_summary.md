# Evaluation summary

Seeded experiment: 200 ground-truth facts, 12 consolidation cycles, 3 policies (seed 20261121). All numbers are measured from the stored run; facts and consolidation passes are synthetic and seeded, with ground truth known by construction.

## Final-cycle mutation rate by policy

| Policy | Mutated (final cycle) | Certainty inflation | Cycles until 50% ever-mutated |
|---|---|---|---|
| regenerate | 99.0% | 38.0% | 2 |
| append | 89.5% | 28.0% | 4 |
| anchor | 59.0% | 12.5% | 10 |

## Detector comparison (final cycle, by policy)

Binary detection of mutated facts; the baselines cannot name a mutation type at all. Text diff only looks respectable in the regenerate regime, where almost every fact is mutated and survivors carry several gross mutations at once; in the low-drift anchor regime its precision collapses, because rewording noise and one-field mutations move the similarity by about the same amount.

| Policy | Detector | Precision | Recall | F1 |
|---|---|---|---|---|
| regenerate | field-level auditor (this tool) | 1.000 | 1.000 | 1.000 |
| regenerate | text similarity (threshold 0.85) | 0.995 | 0.980 | 0.987 |
| regenerate | text similarity (best threshold 0.90) | - | - | 0.997 |
| regenerate | token cosine (threshold 0.90) | 0.995 | 1.000 | 0.997 |
| regenerate | survival-only counter | 1.000 | 0.460 | 0.630 |
| append | field-level auditor (this tool) | 1.000 | 1.000 | 1.000 |
| append | text similarity (threshold 0.85) | 0.901 | 0.866 | 0.883 |
| append | text similarity (best threshold 0.98) | - | - | 0.955 |
| append | token cosine (threshold 0.90) | 0.906 | 0.916 | 0.911 |
| append | survival-only counter | 1.000 | 0.212 | 0.350 |
| anchor | field-level auditor (this tool) | 1.000 | 1.000 | 1.000 |
| anchor | text similarity (threshold 0.85) | 0.626 | 0.822 | 0.711 |
| anchor | text similarity (best threshold 0.99) | - | - | 0.803 |
| anchor | token cosine (threshold 0.90) | 0.628 | 0.831 | 0.715 |
| anchor | survival-only counter | 1.000 | 0.136 | 0.239 |

The survival-only counter's recall is the share of mutated facts it can see at all: only the lost ones. Every mutation on a surviving fact is invisible to it.
