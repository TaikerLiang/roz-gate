#!/usr/bin/env python3
# C16 · A QA CR without a fidelity audit on record never integrates.
# Fixture: F4's pre-integration shape in its 2.0 form — feat/5 merged into
# spec/5 with its code-review record (#140), qa/5 open off that tip,
# cleanly mergeable, both CRs thread-clean, the QA CR ready — and NO
# top-level comment on the QA CR: the fidelity audit never ran (B5b stopped
# before the reviewer posted; ADMC #73). Before #95 this integrated: zero
# open fidelity threads read as a clean audit.
# source: ledger C16 — "Labels unchanged (no `status:`), nothing merged or
#   pushed to `spec/5`, no `in-user-review`; the report names the missing
#   fidelity record and patrol's `fidelity-audit` as the road."
# source: commands/integrate.md step 1 (read-only preconditions) — "Verify
#   the QA CR carries a `**[reviewer] · fidelity**` comment … Missing →
#   stop: no fidelity audit on record — patrol runs it"
# source: references/fidelity-brief.md § Findings — the summary comment is
#   the record that the audit ran
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()

c.expect("integrate.md step 1 (read-only: a precondition stop writes no label)",
         "no status label on #5 — not processing, not blocked, not in-user-review",
         r.status_labels("5") == [])
c.expect("integrate.md step 1 (stop before step 3)",
         "nothing merged: qa/5 did not become an ancestor of remote spec/5 (feat/5 landed "
         "there before QA started — the 2.0 shape)",
         lambda: not r.remote_is_ancestor("qa/5", "spec/5"))
c.expect("integrate.md step 5 never reached", "no in-user-review, no pr-merge",
         not r.has_label("5", "status: in-user-review") and r.journal_writes(r"^pr-merge$") == 0)
c.expect("integrate.md step 1 (CR-COMMENTS-LIST)",
         "the QA CR's top-level comments were read",
         any(e.get("route") == "cr-comments-list" and str(e.get("target")) == "103"
             for e in r.journal()))


def names_the_road():
    txt = r.result_text()
    return bool(re.search(r"fidelity", txt, re.I)) and bool(
        re.search(r"patrol|fidelity-audit", txt, re.I))


c.expect("integrate.md step 1 (the stop's wording)",
         "the report names the missing fidelity record and patrol as the road",
         names_the_road)
c.finish()
