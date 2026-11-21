"""Core data model for the consolidation drift meter.

A *fact* is a single structured memory item with a ground-truth value,
a certainty level, a source (attribution) and a timestamp. Long-term
agent memory stores increasingly look like this (JSON fact stores), and
every consolidation (summarisation) pass rewrites them. This module
defines the fact, the typed mutation taxonomy used to classify what a
consolidation pass did to a fact, and the severity scoring.
"""

from dataclasses import dataclass, field

# Certainty levels, weakest to strongest. Consolidation summarises often
# upgrade hedged facts ("may") into flat assertions ("definitely"); the
# level is an integer so inflation is a measurable field change.
CERTAINTY_LABELS = ("uncertain", "likely", "certain")
CERTAINTY_UNCERTAIN = 0
CERTAINTY_LIKELY = 1
CERTAINTY_CERTAIN = 2

# Typed mutation taxonomy. A surviving fact can carry several types at
# once (e.g. value drift *and* attribution loss); a lost fact is LOSS;
# an invented fact with no ground-truth origin is CONFABULATION.
CLEAN = "clean"
LOSS = "loss"
VALUE_DRIFT = "value_drift"
CERTAINTY_INFLATION = "certainty_inflation"
ATTRIBUTION_LOSS = "attribution_loss"
TEMPORAL_FLATTENING = "temporal_flattening"
CONFABULATION = "confabulation"

MUTATION_TYPES = (
    LOSS,
    VALUE_DRIFT,
    CERTAINTY_INFLATION,
    ATTRIBUTION_LOSS,
    TEMPORAL_FLATTENING,
    CONFABULATION,
)

# Base severity per mutation type, before the importance multiplier.
# Confabulation is worst: the memory now asserts something that was
# never true. Value drift corrupts the payload itself. Certainty
# inflation keeps the value but upgrades its epistemic status, which is
# what makes a surviving-but-mutated fact dangerous downstream.
# Attribution loss and temporal flattening degrade the fact without
# changing what it asserts.
TYPE_WEIGHTS = {
    CONFABULATION: 1.0,
    VALUE_DRIFT: 0.9,
    CERTAINTY_INFLATION: 0.8,
    LOSS: 0.7,
    TEMPORAL_FLATTENING: 0.5,
    ATTRIBUTION_LOSS: 0.4,
}


def severity_for(mutation_type, importance):
    """Severity of one mutation on one fact.

    severity = type weight * (0.5 + importance / 6), so an importance-3
    fact scores the full type weight and an importance-1 fact scores
    two thirds of it.
    """
    if mutation_type not in TYPE_WEIGHTS:
        raise ValueError("unknown mutation type: %r" % (mutation_type,))
    if importance not in (1, 2, 3):
        raise ValueError("importance must be 1, 2 or 3, got %r" % (importance,))
    return TYPE_WEIGHTS[mutation_type] * (0.5 + importance / 6.0)


@dataclass
class Fact:
    """One structured memory fact.

    For ground-truth facts, ``origin_id`` equals ``fact_id``. A memory
    copy keeps the ``origin_id`` of the ground-truth fact it descends
    from (its lineage); a confabulated memory fact has ``origin_id``
    set to None.
    """

    fact_id: str
    subject: str
    attribute: str
    value: str
    certainty: int = CERTAINTY_LIKELY
    source: object = None  # str, or None once attribution is lost
    timestamp: int = 0  # day index
    day_precision: bool = True  # False once the date is flattened to a month
    importance: int = 2
    pinned: bool = False
    alternatives: tuple = ()  # other plausible values for this attribute
    origin_id: object = None  # str for descendants, None for confabulations

    def __post_init__(self):
        if self.origin_id is None and not self.fact_id.startswith("confab-"):
            self.origin_id = self.fact_id
        if self.certainty not in (0, 1, 2):
            raise ValueError("certainty must be 0, 1 or 2")

    def key(self):
        """The (subject, attribute) slot this fact fills."""
        return (self.subject, self.attribute)

    def to_dict(self):
        return {
            "fact_id": self.fact_id,
            "subject": self.subject,
            "attribute": self.attribute,
            "value": self.value,
            "certainty": self.certainty,
            "source": self.source,
            "timestamp": self.timestamp,
            "day_precision": self.day_precision,
            "importance": self.importance,
            "pinned": self.pinned,
            "alternatives": list(self.alternatives),
            "origin_id": self.origin_id,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            fact_id=data["fact_id"],
            subject=data["subject"],
            attribute=data["attribute"],
            value=data["value"],
            certainty=data["certainty"],
            source=data["source"],
            timestamp=data["timestamp"],
            day_precision=data["day_precision"],
            importance=data["importance"],
            pinned=data["pinned"],
            alternatives=tuple(data["alternatives"]),
            origin_id=data["origin_id"],
        )


@dataclass
class DriftRecord:
    """The audit verdict for one ground-truth fact (or confabulation)."""

    fact_id: str  # origin id; for confabulations, the invented fact's id
    cycle: int
    types: tuple = ()  # mutation types found; empty means clean
    severity: float = 0.0
    detail: str = ""

    @property
    def is_clean(self):
        return len(self.types) == 0

    @property
    def is_mutated(self):
        return len(self.types) > 0


@dataclass
class CycleAudit:
    """Aggregate audit of one memory state against ground truth."""

    cycle: int
    n_ground_truth: int
    records: list = field(default_factory=list)  # DriftRecord per GT fact
    confabulations: list = field(default_factory=list)  # DriftRecord per invention
    ever_mutated: frozenset = frozenset()  # origin ids mutated in any cycle so far

    def count_type(self, mutation_type):
        return sum(1 for r in self.records if mutation_type in r.types)

    def type_rate(self, mutation_type):
        """Fraction of ground-truth facts currently showing this type."""
        if self.n_ground_truth == 0:
            return 0.0
        return self.count_type(mutation_type) / float(self.n_ground_truth)

    @property
    def n_mutated(self):
        return sum(1 for r in self.records if r.is_mutated)

    @property
    def n_clean(self):
        return sum(1 for r in self.records if r.is_clean)

    @property
    def mutation_rate(self):
        if self.n_ground_truth == 0:
            return 0.0
        return self.n_mutated / float(self.n_ground_truth)

    @property
    def cumulative_mutated_fraction(self):
        if self.n_ground_truth == 0:
            return 0.0
        return len(self.ever_mutated) / float(self.n_ground_truth)

    @property
    def mean_severity(self):
        if not self.records:
            return 0.0
        return sum(r.severity for r in self.records) / float(len(self.records))
