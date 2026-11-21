"""Seeded generator of ground-truth fact sets.

Facts are drawn from a fixed pool of (subject, attribute, value-pool)
slots covering the kinds of things an assistant agent stores: project
state, schedules, device status, people and preferences. Every fact
gets a certainty level, a source, a day timestamp, an importance and
three plausible alternative values (the pool a drift operator can
corrupt the value into). Generation is fully deterministic per seed.
"""

import random

from .models import Fact

SOURCES = (
    "user statement",
    "sensor log",
    "project document",
    "team message",
    "system monitor",
)

# (subject, attribute, value pool). Pools have >= 4 values so each fact
# can carry 3 alternatives distinct from its true value.
SLOTS = (
    ("project Atlas", "deadline", ("2026-03-14", "2026-04-02", "2026-05-21", "2026-06-30", "2026-02-11")),
    ("project Atlas", "lead engineer", ("Sara Iqbal", "Tom Meyer", "Priya Nair", "Jonas Weber", "Lena Fischer")),
    ("project Atlas", "status", ("on track", "at risk", "blocked", "in review", "ahead of schedule")),
    ("project Atlas", "budget remaining", ("42,000 USD", "18,500 USD", "67,250 USD", "9,800 USD", "51,000 USD")),
    ("project Beacon", "deadline", ("2026-01-19", "2026-03-08", "2026-07-15", "2026-09-01", "2026-11-23")),
    ("project Beacon", "status", ("on track", "at risk", "blocked", "in review", "paused")),
    ("project Beacon", "repository host", ("GitHub", "GitLab", "Bitbucket", "self-hosted", "Codeberg")),
    ("clinic ward 4", "bed occupancy", ("31 of 40", "38 of 40", "22 of 40", "40 of 40", "27 of 40")),
    ("clinic ward 4", "night nurse", ("Ayesha Khan", "Maria Garcia", "Chen Wei", "Fatima Noor", "Olga Petrova")),
    ("clinic ward 4", "isolation rooms free", ("0", "1", "2", "3", "4")),
    ("server db-01", "disk usage", ("61%", "74%", "83%", "47%", "92%")),
    ("server db-01", "backup status", ("completed", "failed", "running", "skipped", "partial")),
    ("server db-01", "maintenance window", ("Sunday 02:00", "Saturday 23:00", "Wednesday 01:00", "Friday 03:00", "Monday 00:30")),
    ("server web-02", "disk usage", ("38%", "55%", "69%", "81%", "44%")),
    ("server web-02", "tls certificate expiry", ("2026-05-01", "2026-08-19", "2027-01-10", "2026-12-02", "2026-03-27")),
    ("user", "preferred language", ("English", "Urdu", "German", "Spanish", "French")),
    ("user", "meeting preference", ("mornings", "afternoons", "evenings", "no Fridays", "weekends only")),
    ("user", "dietary restriction", ("none", "vegetarian", "halal", "gluten-free", "vegan")),
    ("user", "home city", ("Faisalabad", "Lahore", "Karachi", "Islamabad", "Multan")),
    ("team lead", "review day", ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")),
    ("team lead", "standup time", ("09:00", "09:30", "10:00", "10:30", "11:00")),
    ("supplier Helix", "contract renewal", ("2026-04-15", "2026-10-01", "2027-02-28", "2026-08-08", "2026-06-19")),
    ("supplier Helix", "payment terms", ("net 30", "net 45", "net 60", "on delivery", "net 15")),
    ("lab printer", "toner level", ("12%", "35%", "58%", "77%", "90%")),
    ("lab printer", "location", ("room 204", "room 118", "room 312", "library annex", "room 207")),
    ("field sensor S7", "battery level", ("23%", "41%", "66%", "88%", "9%")),
    ("field sensor S7", "last calibration", ("2026-01-05", "2026-02-17", "2026-03-29", "2025-12-12", "2026-04-21")),
    ("course CS-501", "exam date", ("2026-05-11", "2026-05-25", "2026-06-03", "2026-04-27", "2026-06-15")),
    ("course CS-501", "lecturer", ("Dr. Hamid", "Dr. Kanwal", "Dr. Reyes", "Dr. Novak", "Dr. Adeyemi")),
    ("office", "fire drill date", ("2026-02-20", "2026-03-13", "2026-05-08", "2026-09-18", "2026-11-06")),
)


def generate_facts(n_facts=200, seed=20261121):
    """Generate ``n_facts`` ground-truth facts, deterministically.

    Facts cycle through the slot pool (re-using a slot with a different
    value once the pool of slots is exhausted is avoided by suffixing
    the subject, so (subject, attribute) stays unique).
    """
    if n_facts < 1:
        raise ValueError("n_facts must be >= 1")
    rng = random.Random(seed)
    facts = []
    used_keys = set()
    round_no = 0
    index = 0
    while len(facts) < n_facts:
        subject, attribute, pool = SLOTS[index % len(SLOTS)]
        if round_no > 0:
            subject = "%s (unit %d)" % (subject, round_no + 1)
        index += 1
        if index % len(SLOTS) == 0:
            round_no += 1
        key = (subject, attribute)
        if key in used_keys:
            continue
        used_keys.add(key)
        value = pool[rng.randrange(len(pool))]
        alternatives = tuple(v for v in pool if v != value)[:3]
        certainty = rng.choice((0, 0, 1, 1, 1, 2, 2))
        importance = rng.choice((1, 2, 2, 3))
        facts.append(
            Fact(
                fact_id="fact-%03d" % (len(facts) + 1),
                subject=subject,
                attribute=attribute,
                value=value,
                certainty=certainty,
                source=rng.choice(SOURCES),
                timestamp=rng.randrange(0, 300),
                day_precision=True,
                importance=importance,
                pinned=False,
                alternatives=alternatives,
            )
        )
    # Pin a deterministic ~15% slice: every 7th fact starting at index 3.
    for position, fact in enumerate(facts):
        if position % 7 == 3:
            fact.pinned = True
    return facts
