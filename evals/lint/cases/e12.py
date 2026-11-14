"""E12 · A [qa] finding does not stop a scenario's test  (#243)
The #199 Haiku reading: 12 of 15 FAILs were a QA seat that raised a `[qa]`
question on the only scenario (D18/D19: "is `expires_at` in seconds or
days?") and then wrote no runnable test — step zero said "continue with the
scenarios it does not touch", which, when the question touches every
scenario, permits an empty suite. Ruling 1: the test is written against the
clause as it stands whenever the contract can drive it; only an undrivable
scenario waits, with why; a test changes on an approved contract change,
never on observed behaviour (the maintainer's review on #243). Replay
D18/D19 measure the run; this case holds the statements.
"""

from lib.lintkit import src

META = {
    "id": 'E12',
    "title": "A `[qa]` finding does not stop a scenario's test",
    "tier": 'lint (defect 2.12.0-, #243)',
    "ledger": None,
}

src("E12: step zero — a questioned scenario is not an undrivable one", "references/qa-brief.md",
    "a questioned scenario is not an\n   undrivable one")
src("E12: a drivable scenario's test is written now, against the clause as it stands",
    "references/qa-brief.md",
    "write its test now, against the\n   clause as it stands")
src("E12: undrivable is narrow — no usable clause, or a missing control/observation point",
    "references/qa-brief.md",
    "**Undrivable** only when no usable clause states its outcome, or the\n"
    "   declared port lacks a control or observation point it needs")
src("E12: only an undrivable scenario waits, and the report says why", "references/qa-brief.md",
    "and why each is\nundrivable")
src("E12: an approved answer changes the test; observed behaviour never does",
    "references/qa-brief.md",
    "update the test\nto the newly approved contract, never to what the implementation returned\n"
    "(QA-4)")
src("E12: the deliverable names why a scenario waits", "references/qa-brief.md",
    "(each with why it is undrivable)")
src("E12: B2.5 — every drivable scenario is already written", "references/next-stage-path-b2.md",
    "is already written, a questioned one included (only an undrivable scenario\nwaits)")
