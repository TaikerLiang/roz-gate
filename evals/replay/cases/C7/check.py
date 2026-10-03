#!/usr/bin/env python3
# C7 · A branch is cut only from a base the remote has.
# Fixture: default_branch = release/20261013, absent from the remote (main
# and release/20261006 exist). F5's STOP obligations, applied to the cut.
# source: ledger C7 — "Labels are blocked alone; the STOP comment names the
#   missing base; no branch pushed, no CR opened." (a mistyped or retired
#   `default_branch` used to cut an empty branch from nothing and open a CR
#   against it — issue #38)
# source: commands/next-stage.md A2 — verify `origin/<default_branch>`
#   exists … and if it does not, STOP
# source: references/workflow.md — the STOP protocol's obligations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

BASE = "release/20261013"
r, c = Run(), Checker()
c.expect("workflow.md (STOP)", "status labels are blocked ALONE",
         r.status_labels("5") == ["status: blocked"])
c.expect("next-stage.md (A2)", "the STOP comment names the missing base",
         any(BASE in b for b in r.issue_comment_bodies("5")))
c.expect("ledger C7 (no CR opened)", "zero CRs created",
         r.journal_writes(r"^pr-create$") == 0)
# Seeded refs: main + release/20261006; a STOP pushes nothing new.
c.expect("ledger C7 (no branch pushed)", "no new ref on the remote",
         r.remote_ref_count() == 2)
c.finish()
