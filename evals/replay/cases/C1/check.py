#!/usr/bin/env python3
# C1 · A STOP strips the gate label.
# Fixture: Path B entry at ready-for-dev STOPs on an `(unverified)` claim.
# source: ledger C1 — "Labels become blocked alone — never ready-for-dev +
#   blocked." (patrol treats a gate label as unconditionally actionable;
#   leaving it re-invokes the command every pass)
# source: commands/next-stage.md:218-227 — the unverified-claim check is
#   the STOP exit
# source: references/workflow.md:270-271 — STOP: "replace the issue's
#   status labels with `blocked` alone"
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("workflow.md:270-271", "status labels are blocked ALONE",
         r.status_labels("5") == ["status: blocked"])
c.expect("ledger C1", "the gate label ready-for-dev is gone",
         not r.has_label("5", "status: ready-for-dev"))
c.expect("workflow.md:272 (STOP obligation 3)",
         "an issue comment names the evidence",
         any("unverified" in b for b in r.issue_comment_bodies("5")))
c.finish()
