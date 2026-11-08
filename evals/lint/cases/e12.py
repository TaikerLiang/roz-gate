"""E12 · A [qa] finding does not stop a scenario's test  (#243)
The #199 Haiku reading: 12 of 15 FAILs were a QA seat that raised a `[qa]`
question on the only scenario (D18/D19: "is `expires_at` in seconds or
days?") and then wrote no runnable test — step zero said "continue with the
scenarios it does not touch", which, when the question touches every
scenario, permits an empty suite. Ruling 1: the test is written against the
clause as it stands whenever the contract can drive it; only an undrivable
scenario waits, with why. Replay D18/D19 measure the run; this case holds
the statements.
"""

from lib.lintkit import src

META = {
    "id": 'E12',
    "title": "A `[qa]` finding does not stop a scenario's test",
    "tier": 'lint (defect 2.12.0-, #243)',
    "ledger": None,
}

src("E12: step zero — a finding does not stop a scenario's test", "references/qa-brief.md",
    "**a finding does not stop a scenario's test**")
src("E12: the test is written against the clause as it stands", "references/qa-brief.md",
    "`Q<k>` touches included — against the clause as it stands now")
src("E12: only an undrivable scenario waits", "references/qa-brief.md",
    "`Q<k>` only when no clause and no control point of the port can drive it")
src("E12: the report says why each waiting scenario cannot be driven",
    "references/qa-brief.md", "and why each cannot be driven")
src("E12: the deliverable names why a scenario waits", "references/qa-brief.md",
    "(each with why no clause or control point\ndrives it)")
src("E12: B2.5 — every drivable scenario is already written", "commands/next-stage.md",
    "every scenario the contract can drive\nis already written, one a finding touches included")
