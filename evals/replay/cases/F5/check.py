#!/usr/bin/env python3
# F5 · A STOP leaves nothing half-done.
# Fixture: Path B entry with an `(unverified)` claim in the spec (same
# fixture as C1 — C1 pins the label discipline, F5 the whole-run STOP).
# source: ledger F5 — "Labels are blocked alone; an issue comment names the
#   claims and the remedy; no branch pushed, no CR opened, no remote write
#   of any kind." (five obligations in one paragraph; four of five
#   honoured looks like success in every log)
# source: commands/next-stage.md:218-227 — STOP lists the claims,
#   recommendation: measure or demote
# source: references/workflow.md:269-273 — the STOP protocol's obligations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
bodies = r.issue_comment_bodies("5")
c.expect("workflow.md:270-271", "status labels are blocked ALONE",
         r.status_labels("5") == ["status: blocked"])
c.expect("next-stage.md:219-220 (lists the claims)",
         "the STOP comment names the unverified claim",
         any("unverified" in b for b in bodies))
c.expect("next-stage.md:220-221 (the remedy)",
         "the STOP comment carries the measure-or-demote recommendation",
         any("measure" in b.lower() or "assumed-empirical" in b for b in bodies))
c.expect("ledger F5 (no CR opened)", "zero CRs created",
         r.journal_writes(r"^pr-create$") == 0)
# Seeded refs are main + spec/5; a STOP pushes nothing new.
c.expect("ledger F5 (no branch pushed, no remote write)",
         "no new ref on the remote", r.remote_ref_count() == 2)
c.finish()
