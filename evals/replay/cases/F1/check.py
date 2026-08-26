#!/usr/bin/env python3
# F1 · A quiet loop stays quiet.
# Fixture: every open issue waiting on the human; no unheard items anywhere.
#   #5 in-user-review — spec CR's only unresolved thread ends with the agent's
#   `**[review] · question**` (waiting on the user, patrol.md:56), latest
#   top-level comment starts `✅ [` (heard); #7 inbox — questions batch already
#   posted, no `summary` request (not actionable, patrol.md:130-135).
# source: ledger F1 — "Report says no action. Zero label writes, zero
#   comments, zero dispatches, no processing left behind."
# source: commands/patrol.md:67 — "If nothing is actionable, act on nothing."
# source: commands/patrol.md:7 — "Follow these steps; do nothing beyond them."
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("ledger F1", "zero forge writes of any kind", r.journal_writes() == 0)
c.expect("ledger F1", "zero seat dispatches", r.dispatch_count() == 0)
c.expect("ledger F1 (no processing left behind)",
         "no issue wears status: processing",
         not any("status: processing" in i.get("labels", [])
                 for i in r.state()["issues"].values()))
# patrol.md:7 — nothing beyond the steps; a quiet pass has no push step.
c.expect("commands/patrol.md:7", "no ref pushed to the remote",
         r.remote_ref_count() == 1)
c.finish()
