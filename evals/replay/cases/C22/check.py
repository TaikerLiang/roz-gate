#!/usr/bin/env python3
# C22 · The implementation review has a record, and review-clean is
# record-current + zero threads.
# Fixture: C20's — the implementation CR (PR 102) open with zero threads and
# NO `**[reviewer] · code-review**` comment (or, in the red-proof, a stale
# one). Zero threads alone used to read as review-clean; since #140 ruling 9
# the record is required where the threads were — B2.1 stops here.
# source: ledger C22 — "An implementation CR with zero open threads and no
#   `**[reviewer] · code-review**` record (or a record whose `reviewed-sha`
#   is not the head) never merges into `<spec-branch>`: next-stage B2.1 stops
#   without pushing, cuts no `<qa-branch>`, writes no label, and names the
#   missing record and patrol's `code-review` action as the road." (#95's
#   lesson, applied to the implementation→QA transition)
# source: commands/next-stage.md B2.1 — "no record or a stale one is patrol's
#   `code-review` action … never merge on zero threads alone"
# source: references/workflow.md (5) — review-clean defined: the record
#   present and its reviewed-sha equal to the CR head and zero open threads
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
journal = r.journal()
c.expect("next-stage.md B2.1 (unlock and report — not a STOP)",
         "no status label on #5 — not processing, not blocked, not in-spec-review",
         r.status_labels("5") == [])
c.expect("next-stage.md B2.1 (stop before B2.2)",
         "nothing merged: feat/5 is not an ancestor of remote spec/5",
         lambda: not r.remote_is_ancestor("feat/5", "spec/5"))
c.expect("next-stage.md B2.1 (stop before B2.3)", "no qa/5 on the remote",
         lambda: r.git("rev-parse", "--verify", "-q", "qa/5")[0] != 0)
c.expect("next-stage.md B2.1 (the record is read, not assumed)",
         "the implementation CR's comments were listed",
         any(e.get("route") == "cr-comments-list" and str(e.get("target")) == "102"
             for e in journal))
c.expect("next-stage.md B2.4/B2.6 never reached", "no QA dispatch, no QA CR",
         not any(e.get("write") and e.get("route") == "pr-create" for e in journal)
         and not any("qa-brief.md" in str(b.get("input", {}))
                     for b in r.tool_uses(("Task", "Agent"))))


def names_the_road():
    txt = r.result_text()
    return bool(re.search(r"code-review|record", txt, re.I)) and bool(
        re.search(r"patrol|code-review", txt, re.I))


c.expect("next-stage.md B2.1 (the report names which precondition and the road)",
         "the report names the missing code-review record and patrol as the road",
         names_the_road)
c.finish()
