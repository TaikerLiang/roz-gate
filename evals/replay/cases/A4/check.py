#!/usr/bin/env python3
# A4 · in-user-review is a listening state, not a terminal one.
# Fixture: issue at in-user-review with an unanswered human top-level CR
# comment three days old (no agent marker anywhere after it).
# source: ledger A4 — "Actionable → review-answers. Not 'waiting on the
#   user'." (the original defect: comments sat unanswered while every pass
#   reported the loop was waiting on the human)
# source: commands/patrol.md:56 — an item whose latest entry does not start
#   with `**[` or `✅ [` is unheard → actionable → review-answers
# source: commands/review-answers.md:35 — the review-answers turn opens by
#   taking the processing lock (LABEL-ADD status: processing)
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("ledger A4 + patrol.md:56 + review-answers.md:35",
         "the pass acted on the unheard comment (lock taken or marker reply posted)",
         r.route_taken("5"))
c.finish()
