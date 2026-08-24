#!/usr/bin/env python3
# C5 · Post-integration re-entry has a branch of its own.
# Fixture: in-spec-review re-entered from (7); feat/5 and qa/5 both MERGED,
# spec CR open with the holder's answer waiting in a thread.
# source: ledger C5 — "Folds, re-runs if behaviour changed, returns the
#   issue to in-user-review." (without it the first-pass branch fires and
#   tells a shipped feature it is ready to move to implementation)
# source: commands/spec-answers.md:139-149 — post-integration re-entry:
#   fold, hand-back re-run, LABEL-REMOVE in-spec-review+processing,
#   LABEL-ADD in-user-review
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("spec-answers.md:147-148", "issue returned to in-user-review",
         r.has_label("5", "status: in-user-review"))
c.expect("spec-answers.md:147", "in-spec-review removed",
         not r.has_label("5", "status: in-spec-review"))
c.expect("spec-answers.md:147", "processing lock not left behind",
         not r.has_label("5", "status: processing"))
# The wrong branch announces "ready for approval to move to implementation"
# (spec-answers.md:130-131) — on a shipped feature that is the C5 defect.
c.expect("ledger C5 (never back to implementation)",
         "no ready-for-implementation announcement",
         not any("move to implementation" in b
                 for b in r.issue_comment_bodies("5")))
c.expect("spec-answers.md:93-95", "the thread was resolved with the ✅ marker",
         any(e.get("route") == "thread-resolve" for e in r.journal()))
c.finish()
