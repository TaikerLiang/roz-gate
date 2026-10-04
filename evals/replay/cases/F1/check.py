#!/usr/bin/env python3
# F1 · A quiet loop stays quiet.
# Fixture: every open issue waiting on the human; no unheard items anywhere.
#   #5 in-user-review — spec CR's only unresolved thread ends with the agent's
#   `**[review] · question**` (waiting on the user, patrol.md:56), latest
#   top-level comment starts `✅ [` (heard); #7 inbox — questions batch already
#   posted, no `summary` request (not actionable, patrol.md:130-135).
# source: ledger F1 — "Report says no action. Zero label writes, zero
#   comments, one dispatch — the scanner — and no other, no processing left
#   behind." (amended for #59: the scan is a read-only sub-agent)
# source: commands/patrol.md:67 — "If nothing is actionable, act on nothing."
# source: commands/patrol.md:7 — "Follow these steps; do nothing beyond them."
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
c.expect("ledger F1", "zero forge writes of any kind", r.journal_writes() == 0)
# 1.25.0 (#59): the scan is itself one read-only dispatch — the scanner,
# whose prompt names its brief. Exactly that one, and no other.
_disp = list(r.tool_uses(("Task", "Agent")))
c.expect("ledger F1 (as amended for #59)", "exactly one dispatch, and it is the scanner",
         len(_disp) == 1
         and "patrol-scan.md" in json.dumps(_disp[0].get("input", {}), ensure_ascii=False))
c.expect("ledger F1 (no processing left behind)",
         "no issue wears status: processing",
         not any("status: processing" in i.get("labels", [])
                 for i in r.state()["issues"].values()))
# patrol.md:7 — nothing beyond the steps; a quiet pass has no push step.
c.expect("commands/patrol.md:7", "no ref pushed to the remote",
         r.remote_ref_count() == 1)
c.finish()
