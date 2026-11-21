"""Baselines: what cheaper drift detectors see, and what they miss.

Real memory pipelines do not diff structured fields; they compare
rendered text, or they just count how many facts survived. This module
implements those two families fairly:

- ``TextSimilarityBaseline`` renders each ground-truth fact and each
  memory fact to a sentence and flags the fact as "changed" when the
  difflib similarity ratio falls below a threshold. The catch, by
  construction of the renderer: a clean fact is re-rendered each cycle
  with a different sentence template (summarisers reword), while a
  one-field mutation (certainty word, one value token) barely moves
  the ratio. No threshold separates the two populations cleanly.
- ``TokenCosineBaseline`` is the same idea with a bag-of-words cosine
  (the stdlib stand-in for an embedding similarity).
- ``SurvivalOnlyBaseline`` is the practitioner aggregate: it counts
  surviving facts and therefore sees LOSS and nothing else. Every
  mutation on a surviving fact is invisible to it.

All baselines output only a binary changed/clean verdict per
ground-truth fact: none of them can name a mutation type.
"""

import difflib
import math
import re
import zlib

CERTAINTY_PHRASES = {
    0: "This may not hold",
    1: "This is likely",
    2: "This is definitely the case",
}


def _variant(fact_id, cycle):
    """Deterministic template variant 0..2 for a render."""
    return zlib.crc32(("%s#%d" % (fact_id, cycle)).encode("utf-8")) % 3


def render_fact(fact, cycle=0):
    """Render a fact as one short paragraph of memory text.

    The template depends on a per-(fact, cycle) variant, mimicking a
    summariser that rewords surviving facts each pass. Field values
    appear verbatim; a missing source simply omits the source clause.
    """
    variant = _variant(fact.fact_id, cycle)
    certainty_phrase = CERTAINTY_PHRASES[fact.certainty]
    if fact.day_precision:
        date_text = "day %d" % fact.timestamp
    else:
        date_text = "around day %d" % fact.timestamp
    core = "%s of %s is %s" % (fact.attribute, fact.subject, fact.value)
    if variant == 0:
        parts = ["The %s." % core]
        if fact.source is not None:
            parts.append("Recorded from the %s." % fact.source)
        parts.append("Noted on %s." % date_text)
        parts.append("%s." % certainty_phrase)
    elif variant == 1:
        parts = ["%s." % certainty_phrase]
        parts.append("Memory: %s." % core)
        parts.append("As of %s." % date_text)
        if fact.source is not None:
            parts.append("Source: %s." % fact.source)
    else:
        parts = ["On %s, the %s was logged." % (date_text, fact.attribute)]
        parts.append("For %s it is %s." % (fact.subject, fact.value))
        if fact.source is not None:
            parts.append("Taken from the %s." % fact.source)
        parts.append("%s." % certainty_phrase)
    return " ".join(parts)


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def token_cosine(text_a, text_b):
    """Bag-of-words cosine similarity between two texts."""
    counts_a = {}
    for token in _tokens(text_a):
        counts_a[token] = counts_a.get(token, 0) + 1
    counts_b = {}
    for token in _tokens(text_b):
        counts_b[token] = counts_b.get(token, 0) + 1
    if not counts_a or not counts_b:
        return 0.0
    dot = sum(count * counts_b.get(token, 0) for token, count in counts_a.items())
    norm_a = math.sqrt(sum(c * c for c in counts_a.values()))
    norm_b = math.sqrt(sum(c * c for c in counts_b.values()))
    return dot / (norm_a * norm_b)


class TextSimilarityBaseline(object):
    """Flags a fact changed when its re-rendered text drifts too far."""

    name = "text_similarity"

    def __init__(self, threshold=0.85):
        self.threshold = threshold

    def similarity(self, ground_truth_fact, memory_fact, cycle):
        original = render_fact(ground_truth_fact, cycle=0)
        current = render_fact(memory_fact, cycle=cycle)
        return difflib.SequenceMatcher(None, original, current).ratio()

    def flag_changed(self, ground_truth, memory, cycle):
        """Return the set of ground-truth fact ids flagged as changed."""
        by_origin = {}
        for fact in memory:
            if fact.origin_id is not None:
                by_origin[fact.origin_id] = fact
        flagged = set()
        for gt in ground_truth:
            mem = by_origin.get(gt.fact_id)
            if mem is None:
                flagged.add(gt.fact_id)
            elif self.similarity(gt, mem, cycle) < self.threshold:
                flagged.add(gt.fact_id)
        return flagged


class TokenCosineBaseline(TextSimilarityBaseline):
    name = "token_cosine"

    def __init__(self, threshold=0.90):
        self.threshold = threshold

    def similarity(self, ground_truth_fact, memory_fact, cycle):
        original = render_fact(ground_truth_fact, cycle=0)
        current = render_fact(memory_fact, cycle=cycle)
        return token_cosine(original, current)


class SurvivalOnlyBaseline(object):
    """Sees only whether the fact still exists."""

    name = "survival_only"

    def flag_changed(self, ground_truth, memory, cycle):
        present = set(
            fact.origin_id for fact in memory if fact.origin_id is not None
        )
        return set(gt.fact_id for gt in ground_truth if gt.fact_id not in present)


def detection_scores(flagged, mutated_ids, all_ids):
    """Precision / recall / F1 of a binary detector vs the auditor."""
    flagged = set(flagged)
    mutated_ids = set(mutated_ids)
    all_ids = set(all_ids)
    true_pos = len(flagged & mutated_ids)
    false_pos = len(flagged - mutated_ids)
    false_neg = len(mutated_ids - flagged)
    precision = true_pos / float(true_pos + false_pos) if (true_pos + false_pos) else 1.0
    recall = true_pos / float(true_pos + false_neg) if (true_pos + false_neg) else 1.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}
