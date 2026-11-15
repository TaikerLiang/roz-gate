#!/usr/bin/env python3
# D3 · Every dispatch carries the seat's R&R row.
# Fixture: one inbox issue with no questions batch → patrol's async intake
# dispatches the product seat. The transcript's dispatch payload is the
# observation channel (the ledger's "structurally unobservable" was written
# with only the forge record in view; the upgrade was accepted).
# source: ledger D3 — "The payload contains the seat's Owns / Never row."
#   (a seat running without its contract produces plausible work, and
#   nothing in the record shows the row was missing)
# source: commands/patrol.md:18-23 — every role dispatch attaches the
#   seat's R&R row from references/workflow.md as its contract
# source: references/workflow.md:22 — product Owns: "actors, scenarios";
#   Never: "architecture, code, impl tests"
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()

# The row is matched by its terms, not its punctuation (#330 ruling 5): a
# dispatch that writes "Architecture, code and implementation tests are NOT
# yours" carries the Never column as surely as "Never: architecture, code,
# impl tests". The terms are searched in the decoded input, not its JSON: a
# term at the start of a prompt line follows a newline, which JSON writes as
# `\n`, and `\b` cannot see a boundary after its `n` (codex review, PR #340).
OWNS = (r"\bactors\b", r"\bscenarios\b")
NEVER = (r"\barchitecture\b", r"\bcode\b", r"\b(?:impl|implementation) tests\b")


def dispatch_carries_rr():
    for b in r.tool_uses(("Task", "Agent")):
        p = " ".join(str(v) for v in (b.get("input") or {}).values())
        if all(re.search(t, p, re.I) for t in OWNS + NEVER):
            return True
    return False

c.expect("ledger D3 + patrol.md:18-23 + workflow.md:22",
         "the product dispatch payload carries its Owns AND Never row",
         dispatch_carries_rr)
c.expect("patrol.md:130-133 (the dispatch's product)",
         "one **[intake]** batch was posted",
         any(b.startswith("**[intake]**")
             for b in r.issue_comment_bodies("9")))
c.finish()
