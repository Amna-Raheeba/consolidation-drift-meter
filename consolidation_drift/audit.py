"""The drift meter: field-level diff of a memory against ground truth.

The auditor is the instrument this project contributes. It does not
look at rendered text; it diffs the structured fields of every memory
fact against its ground-truth ancestor and classifies the difference
with the typed taxonomy:

- fact missing from memory            -> LOSS
- value differs                       -> VALUE_DRIFT
- certainty higher than ground truth  -> CERTAINTY_INFLATION
- source is None but ground truth had one -> ATTRIBUTION_LOSS
- day precision dropped or date moved -> TEMPORAL_FLATTENING
- memory fact with no ground-truth origin -> CONFABULATION

A fact can carry several types at once. Severity combines the type
weights with the fact's importance (see models.severity_for).
"""

from .models import (
    ATTRIBUTION_LOSS,
    CERTAINTY_INFLATION,
    CONFABULATION,
    LOSS,
    TEMPORAL_FLATTENING,
    VALUE_DRIFT,
    CycleAudit,
    DriftRecord,
    severity_for,
)


def classify_fact(ground_truth_fact, memory_fact):
    """Return the tuple of mutation types for one surviving fact."""
    types = []
    if memory_fact.value != ground_truth_fact.value:
        types.append(VALUE_DRIFT)
    if memory_fact.certainty > ground_truth_fact.certainty:
        types.append(CERTAINTY_INFLATION)
    if ground_truth_fact.source is not None and memory_fact.source is None:
        types.append(ATTRIBUTION_LOSS)
    if (not memory_fact.day_precision) or (
        memory_fact.timestamp != ground_truth_fact.timestamp
    ):
        types.append(TEMPORAL_FLATTENING)
    return tuple(types)


def record_severity(ground_truth_fact, types):
    """A record's severity is its worst single mutation, importance-scaled."""
    if not types:
        return 0.0
    return max(severity_for(t, ground_truth_fact.importance) for t in types)


def audit_memory(ground_truth, memory, cycle, ever_mutated=frozenset()):
    """Audit one memory state against ground truth.

    ``ever_mutated`` carries the set of origin ids mutated in any
    earlier cycle, so the returned CycleAudit can report the cumulative
    mutated fraction. Returns a CycleAudit.
    """
    by_origin = {}
    confabulations = []
    for fact in memory:
        if fact.origin_id is None:
            confabulations.append(fact)
        else:
            by_origin[fact.origin_id] = fact
    records = []
    new_ever = set(ever_mutated)
    for gt in ground_truth:
        mem = by_origin.get(gt.fact_id)
        if mem is None:
            types = (LOSS,)
            detail = "fact absent from memory"
        else:
            types = classify_fact(gt, mem)
            detail = "; ".join(types) if types else "clean"
        record = DriftRecord(
            fact_id=gt.fact_id,
            cycle=cycle,
            types=types,
            severity=record_severity(gt, types),
            detail=detail,
        )
        records.append(record)
        if record.is_mutated:
            new_ever.add(gt.fact_id)
    confab_records = [
        DriftRecord(
            fact_id=fact.fact_id,
            cycle=cycle,
            types=(CONFABULATION,),
            severity=severity_for(CONFABULATION, fact.importance),
            detail="invented fact with no ground-truth origin",
        )
        for fact in confabulations
    ]
    return CycleAudit(
        cycle=cycle,
        n_ground_truth=len(ground_truth),
        records=records,
        confabulations=confab_records,
        ever_mutated=frozenset(new_ever),
    )


def audit_snapshots(ground_truth, snapshots):
    """Audit every snapshot from policies.run_cycles, threading the
    cumulative ever-mutated set through the cycles."""
    audits = []
    ever = frozenset()
    for cycle, memory in enumerate(snapshots):
        audit = audit_memory(ground_truth, memory, cycle, ever)
        audits.append(audit)
        ever = audit.ever_mutated
    return audits


def cycles_until_half_mutated(audits):
    """First cycle where >= 50% of ground-truth facts have ever mutated.

    Returns None if the threshold is never reached.
    """
    for audit in audits:
        if audit.cumulative_mutated_fraction >= 0.5:
            return audit.cycle
    return None


def fact_lineage(ground_truth_fact, snapshots):
    """Per-cycle state of one fact: a list of dicts with its field
    values and audit types at each cycle (state None once lost)."""
    lineage = []
    ever = frozenset()
    for cycle, memory in enumerate(snapshots):
        audit = audit_memory([ground_truth_fact], _single(memory, ground_truth_fact), cycle, ever)
        ever = audit.ever_mutated
        state = None
        for fact in memory:
            if fact.origin_id == ground_truth_fact.fact_id:
                state = fact
                break
        lineage.append(
            {
                "cycle": cycle,
                "present": state is not None,
                "value": state.value if state else None,
                "certainty": state.certainty if state else None,
                "source": state.source if state else None,
                "timestamp": state.timestamp if state else None,
                "day_precision": state.day_precision if state else None,
                "types": list(audit.records[0].types),
            }
        )
    return lineage


def _single(memory, ground_truth_fact):
    """The sub-memory relevant to one fact (itself or empty)."""
    return [
        fact for fact in memory if fact.origin_id == ground_truth_fact.fact_id
    ]
