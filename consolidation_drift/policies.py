"""Seeded consolidation policies: simulated summariser passes.

Each policy takes the current memory (a list of Fact copies) and one
consolidation cycle later returns a new memory. A cycle applies, per
fact and independently, a set of mutation operators with policy
specific probabilities:

- drop the fact (becomes LOSS),
- replace its value with a plausible alternative (VALUE_DRIFT),
- upgrade its certainty one level (CERTAINTY_INFLATION),
- drop its source (ATTRIBUTION_LOSS),
- collapse its day timestamp to month precision (TEMPORAL_FLATTENING),
- and, per cycle, invent a small number of new facts (CONFABULATION).

The three policies differ only in their operator rates and in whether
pinned facts are protected:

- ``regenerate`` rewrites the whole memory from scratch each cycle:
  the highest drift, and pinned facts are *not* protected (the
  summariser does not know they matter).
- ``append`` appends a superseding summary and keeps the rest: lower
  rates across the board.
- ``anchor`` (verbatim-anchor) never rewrites pinned facts at all and
  drifts the rest slowly; it never confabulates.

All randomness flows from one seeded ``random.Random`` per simulation,
so a (facts, policy, cycles, seed) run is exactly reproducible.
"""

import copy
import random

from .models import Fact

# Plausible inventions for confabulation: slots that are NOT in the
# ground-truth slot pool, so an invented fact never accidentally
# coincides with a real one.
CONFAB_SLOTS = (
    ("project Atlas", "sponsor", ("Northwind Trust", "Helix Labs", "City Council", "Vertex Fund")),
    ("clinic ward 4", "visiting hours", ("14:00-16:00", "10:00-12:00", "16:00-18:00", "09:00-11:00")),
    ("user", "favourite colour", ("teal", "maroon", "ochre", "slate blue")),
    ("office", "wifi password rotation", ("monthly", "quarterly", "weekly", "never")),
    ("server db-01", "replication lag", ("2 s", "15 s", "40 s", "3 min")),
)


class Policy(object):
    """Base class: operator rates + confabulation count per cycle."""

    name = "base"
    protect_pinned = False
    rates = {
        "loss": 0.0,
        "value_drift": 0.0,
        "certainty_inflation": 0.0,
        "attribution_loss": 0.0,
        "temporal_flattening": 0.0,
    }
    confabulations_per_cycle = 0

    def consolidate(self, memory, rng, cycle, confab_counter):
        """Return (new_memory, next_confab_counter) after one cycle."""
        new_memory = []
        for fact in memory:
            if fact.origin_id is None:
                # Confabulations persist verbatim once invented.
                new_memory.append(copy.deepcopy(fact))
                continue
            if self.protect_pinned and fact.pinned:
                new_memory.append(copy.deepcopy(fact))
                continue
            if rng.random() < self.rates["loss"]:
                continue  # dropped: does not survive the cycle
            mutant = copy.deepcopy(fact)
            if rng.random() < self.rates["value_drift"] and mutant.alternatives:
                mutant.value = rng.choice(mutant.alternatives)
            if (
                rng.random() < self.rates["certainty_inflation"]
                and mutant.certainty < 2
            ):
                mutant.certainty += 1
            if rng.random() < self.rates["attribution_loss"]:
                mutant.source = None
            if rng.random() < self.rates["temporal_flattening"] and mutant.day_precision:
                mutant.day_precision = False
                mutant.timestamp = (mutant.timestamp // 30) * 30
            new_memory.append(mutant)
        for _ in range(self.confabulations_per_cycle):
            confab_counter += 1
            subject, attribute, pool = CONFAB_SLOTS[
                rng.randrange(len(CONFAB_SLOTS))
            ]
            new_memory.append(
                Fact(
                    fact_id="confab-%03d" % confab_counter,
                    subject=subject,
                    attribute=attribute,
                    value=rng.choice(pool),
                    certainty=2,
                    source=None,
                    timestamp=rng.randrange(0, 300),
                    day_precision=True,
                    importance=2,
                    pinned=False,
                    alternatives=(),
                    origin_id=None,
                )
            )
        return new_memory, confab_counter


class RegeneratePolicy(Policy):
    name = "regenerate"
    protect_pinned = False
    rates = {
        "loss": 0.06,
        "value_drift": 0.10,
        "certainty_inflation": 0.14,
        "attribution_loss": 0.18,
        "temporal_flattening": 0.12,
    }
    confabulations_per_cycle = 3


class AppendPolicy(Policy):
    name = "append"
    protect_pinned = False
    rates = {
        "loss": 0.02,
        "value_drift": 0.04,
        "certainty_inflation": 0.05,
        "attribution_loss": 0.06,
        "temporal_flattening": 0.04,
    }
    confabulations_per_cycle = 1


class AnchorPolicy(Policy):
    name = "anchor"
    protect_pinned = True
    rates = {
        "loss": 0.01,
        "value_drift": 0.02,
        "certainty_inflation": 0.02,
        "attribution_loss": 0.03,
        "temporal_flattening": 0.02,
    }
    confabulations_per_cycle = 0


POLICIES = {
    "regenerate": RegeneratePolicy(),
    "append": AppendPolicy(),
    "anchor": AnchorPolicy(),
}


def initial_memory(ground_truth):
    """Cycle-0 memory: a verbatim copy of ground truth."""
    return [copy.deepcopy(fact) for fact in ground_truth]


def run_cycles(ground_truth, policy, cycles, seed):
    """Run ``cycles`` consolidation cycles; return per-cycle memories.

    The returned list has ``cycles + 1`` entries: index 0 is the
    verbatim initial memory, index k is the memory after k cycles.
    """
    if cycles < 0:
        raise ValueError("cycles must be >= 0")
    rng = random.Random(seed)
    memory = initial_memory(ground_truth)
    snapshots = [memory]
    confab_counter = 0
    for cycle in range(1, cycles + 1):
        memory, confab_counter = policy.consolidate(
            memory, rng, cycle, confab_counter
        )
        snapshots.append(memory)
    return snapshots
