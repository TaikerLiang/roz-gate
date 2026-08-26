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
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()

def dispatch_carries_rr():
    for b in r.tool_uses(("Task", "Agent")):
        p = json.dumps(b.get("input", {}), ensure_ascii=False)
        if "actors, scenarios" in p and "impl tests" in p:
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
