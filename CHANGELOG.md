# Changelog

## 0.1.0 — 2026-11-21

- Initial release.
- Structured fact model with ground-truth value, certainty, source,
  day timestamp, importance, plausible alternatives and a pinned flag;
  seeded generator over a 30-slot fact pool (200 canonical facts).
- Typed mutation taxonomy: loss, value drift, certainty inflation,
  attribution loss, temporal flattening, confabulation — with
  importance-scaled severity scoring and per-fact lineage tracking.
- Three seeded consolidation policies: regenerate-from-scratch,
  append-and-supersede, verbatim-anchor (pinned facts never rewritten).
- Baselines: text-similarity diff and token-cosine diff over rendered
  memory text (with per-cycle rewording), and a survival-only counter.
- Headline experiment: 200 facts × 12 cycles × 3 policies. Regenerate
  mutates 99.0% of facts by cycle 12 (half by cycle 2) with 38.0%
  certainty inflation and 36 confabulations; verbatim-anchor holds
  mutation to 59.0% and inflation to 12.5%. Text diff collapses to
  F1 0.711 in the low-drift regime; survival-only recall is 0.136.
- Streamlit dashboard (drift by policy, fact lineage, evaluation),
  CLI (demo / audit / evaluate), and a reproduce script with a
  headline-drift guard.
