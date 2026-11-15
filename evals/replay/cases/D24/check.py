#!/usr/bin/env python3
# D24 · A term used against its definition is a finding.
# Fixture: D23's build and contract (kv-cli-expiry, `advance-clock` declared
# and built; feat/5 merged into spec/5, no qa/5) with spec.md's `## Glossary`
# defining `expired` as `expires_at` strictly before now, while C4 calls a
# key expired at or before now. The build follows C4.
# source: ledger D24 — "`spec.md` § Glossary: `expired — expires_at is
#   strictly before now`. Contract clause C4: *a key whose `expires_at` is at
#   or before now is expired*; the build follows C4. Pass: QA's findings — a
#   `[qa]` thread on the spec CR, or the report — name the term `expired` and
#   both readings; a suite pushed; no denied attempt. Fail: no finding naming
#   the term — whichever boundary the suite then asserts. Invalid: no
#   dispatch, or a written suite never pushed." (#197)
# source: references/qa-brief.md § Step zero — "a **term conflict**: a
#   clause, a deviation or a scenario that uses a term of `spec.md`'s
#   `## Glossary` with another meaning — name the term and both readings"
# source: references/next-stage-path-a.md A3 — "**Glossary** (#197)";
#   "Downstream seats use a term as defined"
# source: commands/next-stage.md B2.4/B2.5 — the QA dispatch; its findings
#   become `[qa]` threads on the spec CR
#
# The frame holds the shared verdict (dispatch, marker, blindness, a suite
# pushed, `src/` untouched). The suite's boundary is not scored: either
# reading asserted without the finding is the failure. The finding is read
# from the [qa] thread, else the report — the term and both boundaries, a
# regex, so a lower bound.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

PORT = "src/kv/cli.py"
TERM = (r"(?is)(?=.*\bexpired\b)"
        r"(?=.*(strictly|expires_at`?\s*<(?!=)|<\s*now))"
        r"(?=.*(at or before|on or before|<=|≤|equal))")

f = Frame(ports=[PORT])
f.standard()
f.c.expect("qa-brief.md § Step zero — a **term conflict** names the term and both readings; "
           "next-stage B2.5 posts it",
           "a [qa] thread on the spec CR, or the report, names `expired` with both readings — "
           "strictly before now, and at or before now",
           f.finding_reported(TERM, r"finding|conflict|glossary|contradict|\bQ\d|\[qa\]"))
f.finish()
