#!/usr/bin/env python3
# C12 · A merged CR is never re-merged — integrate validates the spec tip.
# Fixture: feat/5 and qa/5 MERGED into spec/5 on the forge; spec/5 moved
# since (one later commit reworded the expiry reason); the two stale tips
# are not ancestors of spec/5 and conflict with it on re-merge.
# source: ledger C12 — "Both CRs merged, spec/<n> moved since: nothing
#   merged — neither tip becomes an ancestor of spec/<n>, the moved tip's
#   content is intact on the remote, the suites ran against it, labels end
#   at in-user-review alone, no STOP comment, and the claim reads 'green
#   against the pre-rework spec, at SHA x'." (integrate re-merged two
#   already-incorporated branches into a spec/<n> that had moved
#   independently and stopped on a two-line conflict in a test file — a
#   re-merge of stale inputs reported as a failed verdict attempt — #77)
# source: commands/integrate.md step 3 — merge what is open, never what is
#   merged; both merged → nothing is merged, a re-verdict on the tip
# source: commands/integrate.md step 5 — finalize, the licensed claim
# source: commands/integrate.md step 6 — the STOP exit this run must not take
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
MOVED = 'reason({"expires_at": 1}, now=2), "offer expired"'
ACCEPT = "unittest discover -s tests/acceptance"

c.expect("integrate.md step 3 (never what is merged)",
         "neither stale tip became an ancestor of remote spec/5 — nothing merged",
         lambda: not r.remote_is_ancestor("feat/5", "spec/5")
             and not r.remote_is_ancestor("qa/5", "spec/5"))
c.expect("integrate.md step 3 (the tip as it stands)",
         "remote spec/5 still carries the moved wording in the suite",
         lambda: MOVED in (r.remote_file("spec/5", "tests/acceptance/test_expiry.py") or ""))
c.expect("integrate.md step 4 (run the verdict)",
         "the configured acceptance_test ran",
         any(ACCEPT in (b.get("input") or {}).get("command", "")
             for b in r.tool_uses(("Bash",))))
c.expect("integrate.md step 5.5 (labels)", "in-user-review alone — no blocked, no processing",
         r.status_labels("5") == ["status: in-user-review"])
c.expect("integrate.md step 6 (no STOP exit)", "no blocked comment on the issue",
         not any("blocked" in b for b in r.issue_comment_bodies("5")))
c.expect("integrate.md (CR-MERGE is the human's act at (7))", "gh pr merge was never invoked",
         r.journal_writes(r"^pr-merge$") == 0)


def claim_ok():
    txt = r.result_text()
    if "green against the pre-rework spec" not in txt:
        return False
    # "verified" standing alone is the forbidden claim; "unverified" is legal.
    return not re.search(r"(?<!un)verified", txt)


c.expect("integrate.md step 5 (the licensed claim, verbatim)",
         "report claims 'green against the pre-rework spec', never 'verified'",
         claim_ok)
c.finish()
