#!/usr/bin/env python3
# A3 · Top-level comments are read as a channel.
# Fixture: unanswered top-level comment on the CR; every inline thread
# already carries an agent marker as its last entry.
# source: ledger A3 — "Actionable. Top-level is the default affordance on
#   the PR page and the only one usable from a phone."
# source: commands/patrol.md:56 — all three channels, CR-COMMENTS-LIST
#   included
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("patrol.md:56", "CR-COMMENTS-LIST was actually read",
         any(e.get("route") == "cr-comments-list" for e in r.journal()))
c.expect("ledger A3 + patrol.md:56 + review-answers.md:63 (cites the URL)",
         "a marker reply binds to the top-level comment itself",
         r.item_bound_reply("#issuecomment-800", "剛好過期"))
c.finish()
