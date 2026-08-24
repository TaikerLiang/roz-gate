#!/usr/bin/env python3
# A1 · A human's ✅ acknowledgement reads as an agent marker.
# Fixture: latest top-level CR comment is the human's, body begins with a
# BARE ✅ (`✅ 看起來可以…`) — not the agent marker `✅ [`.
# source: ledger A1 — "Classified unheard → actionable. The agent marker is
#   `✅ [`, never a bare ✅." (the single highest-value message in the
#   channel was the one the predicate could not see)
# source: commands/patrol.md:56 — unheard = latest entry does not start
#   with `**[` or `✅ [`
# source: commands/review-answers.md:35 — the review turn opens by taking
#   the processing lock
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("ledger A1 + patrol.md:56",
         "the bare-✅ comment was classified unheard and acted on",
         r.route_taken("5"))
c.finish()
