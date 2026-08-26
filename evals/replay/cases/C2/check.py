#!/usr/bin/env python3
# C2 · Stage (7) has no blocked exit.
# Fixture: review-answers cannot complete the item — the spec CR is CLOSED
# while status: in-user-review persists.
# source: ledger C2 — "in-user-review is retained; no blocked. The failure
#   is a prefixed comment." (blocked exists to stop the machine, not to
#   inform the human; at (7) there is no machine to stop)
# source: commands/review-answers.md:27-28 — "Missing or closed while the
#   label persists → report it and act on nothing."
# source: references/workflow.md:276-282 — (7) has no blocked exit; a
#   failure is a `**[review] · question**`, never a label
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("ledger C2 + workflow.md:276-282", "status: blocked was never applied",
         not r.has_label("5", "status: blocked"))
c.expect("ledger C2", "in-user-review is retained",
         r.has_label("5", "status: in-user-review"))
# review-answers.md:28 — act on NOTHING: no labels, no comments, no merges.
c.expect("review-answers.md:28", "no forge write at all on the closed-CR path",
         r.journal_writes() == 0)
c.finish()
