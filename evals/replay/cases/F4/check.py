#!/usr/bin/env python3
# F4 · A green verdict makes the claim it is entitled to.
# Fixture: review-clean implementation CR, ready QA CR, suite passes.
# source: ledger F4 — "Both merged, suite captured, branch pushed,
#   in-user-review applied — and the claim printed reads 'green against
#   the pre-rework spec, at SHA x', never 'verified'." (the weakened claim
#   is one sentence in a long command, exactly the kind that silently
#   reverts to the confident phrasing)
# source: commands/integrate.md:75-100 — finalize: push spec/<n>, labels,
#   and the licensed claim verbatim
# source: commands/integrate.md:63 — CR-MERGE is the human's act at (7);
#   commands never run it
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("integrate.md:53-54,75-76 (both merged, branch pushed)",
         "remote spec/5 contains the feat/5 and qa/5 tips",
         lambda: r.remote_is_ancestor("feat/5", "spec/5")
             and r.remote_is_ancestor("qa/5", "spec/5"))
c.expect("integrate.md:96 (labels)", "in-user-review applied, processing removed",
         r.status_labels("5") == ["status: in-user-review"])
c.expect("integrate.md:63", "gh pr merge was never invoked",
         r.journal_writes(r"^pr-merge$") == 0)

def claim_ok():
    txt = r.result_text()
    if "green against the pre-rework spec" not in txt:
        return False
    # The forbidden confident claim: "verified" standing alone ("unverified"
    # is a different word and legal). Lower bound: paraphrases evade regex.
    return not re.search(r"(?<!un)verified", txt)

c.expect("ledger F4 + integrate.md:98-100 (the licensed claim, verbatim)",
         "report claims 'green against the pre-rework spec', never 'verified'",
         claim_ok)
c.finish()
