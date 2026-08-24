#!/usr/bin/env python3
# A2 · A review whose whole content is its body is invisible.
# Fixture: one CHANGES_REQUESTED review with a non-empty body, zero inline
# comments, zero issue comments — it appears in neither THREADS-LIST nor
# the comments endpoint.
# source: ledger A2 — "Detected as unheard via REVIEWS-LIST." (a repository
#   could scan perfectly clean while a reviewer had blocked the change)
# source: commands/patrol.md:56 — the CR is read on all three channels
# source: references/forge-github.md:114-125 — REVIEWS-LIST; a non-empty
#   body counts on all three states
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("patrol.md:56 + forge-github.md:114", "REVIEWS-LIST was actually read",
         any(e.get("route") == "reviews-list" for e in r.journal()))
c.expect("ledger A2 + patrol.md:56",
         "the body-only review was classified unheard and acted on",
         r.route_taken("5"))
c.finish()
