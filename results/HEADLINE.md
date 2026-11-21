# Headline results

Consolidation drift measured on 200 seeded ground-truth facts over 12 consolidation cycles (seed 20261121).

- Under regenerate-from-scratch consolidation, 99.0% of facts carry at least one typed mutation by cycle 12, and half of all facts have mutated by cycle 2.
- Certainty inflation is the signature mutation: by the final cycle 38.0% of facts have had their certainty upgraded under regenerate, vs 28.0% under append-and-supersede and 12.5% under verbatim-anchor.
- Final-cycle mutation rates: regenerate 99.0%, append 89.5%, verbatim-anchor 59.0%. Regenerate also leaves 36 invented (confabulated) facts in memory.
- Detector comparison (final cycle): the field-level auditor detects mutated facts at F1 1.000 by construction (structured diff). A text-similarity diff reaches F1 0.987 in the harsh regenerate regime — where 99% of facts are mutated and survivors carry several gross mutations — but only F1 0.711 (precision 0.626) in the low-drift anchor regime, and 0.803 even at its best threshold there. A survival-only counter recalls just 0.136 of mutated facts under anchor: it cannot see any mutation on a surviving fact. No text baseline can name a mutation type at all.

Caveat: facts and consolidation passes are synthetic and seeded; the consolidation operator is a declared probabilistic policy, not a live LLM. The experiment measures the audit instrument and the relative drift of the three policies under that operator, not the drift rate of any production system.
