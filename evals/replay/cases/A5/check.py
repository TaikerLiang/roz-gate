#!/usr/bin/env python3
# A5 · The fast track resolves to its own CR.
# Fixture: track: fast + in-user-review, unanswered comment on fast/5's CR.
# No spec CR exists anywhere in the fixture.
# source: ledger A5 — "CR resolves to fast/<n> and the item is detected."
#   (the row said "spec CR", so the A4 fix would have covered only half
#   the tracks)
# source: commands/patrol.md:56 — "`spec/<n>` for `track: spec`,
#   `fast/<n>` for `track: fast`"
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("patrol.md:56", "the fast CR's channels were read (CR 102, head fast/5)",
         any(e.get("route") == "cr-comments-list" and e.get("target") == "102"
             for e in r.journal()))
c.expect("ledger A5 + patrol.md:56",
         "the fast-track comment was detected and acted on",
         r.route_taken("5"))
c.finish()
