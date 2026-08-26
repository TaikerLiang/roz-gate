#!/usr/bin/env python3
# D2 · The fidelity dispatch is blind by topology.
# Fixture: the QA CR carries an open fidelity thread (human's answer last);
# the implementation CR is thread-clean. Address-review dispatches the QA
# side; the fidelity re-check must live on qa/5 and never touch feat/5.
# source: ledger D2 — "Checkout is qa/<n>; abort if the context ever
#   touched feat/<n>. Blindness asserted in a prompt is a request;
#   blindness enforced by which branch is checked out is a fact."
# source: commands/patrol.md:83-91 — QA CR fidelity threads → dispatch qa
#   on qa/<n>; re-checks use a fresh implementation-blind dispatch on
#   qa/<n> only
# source: commands/next-stage.md:305-310 (B5b) — the qa/<n> checkout is
#   what makes the dispatch structurally implementation-blind
#
# Scope (codex review, PR #1): patrol itself LEGITIMATELY touches feat/5 —
# CR-FIND for feat/<n> is its own step 2 (patrol.md:54). Only the fidelity
# DISPATCH must be blind. The assertion binds to the dispatch payload and
# to any transcript events parented to that dispatch, never to the root
# pass.
#
# Stated limit (README, cannot-see list): this observes the dispatch's
# payload and its visible child events; in-context leakage through text
# already in the session is invisible to any transcript check.
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()

def fidelity_dispatches():
    """QA-side dispatches: payload names qa/5 or the fidelity brief."""
    out = []
    for b in r.tool_uses(("Task", "Agent")):
        p = json.dumps(b.get("input", {}), ensure_ascii=False)
        if "qa/5" in p or "fidelity" in p.lower():
            out.append(b)
    return out

def dispatch_on_qa5():
    return any("qa/5" in json.dumps(b.get("input", {}), ensure_ascii=False)
               for b in fidelity_dispatches())

def dispatch_blind():
    ds = fidelity_dispatches()
    if not ds:
        return False
    ids = {b.get("id") for b in ds}
    for b in ds:  # the payload itself must not point at the implementation
        if "feat/5" in json.dumps(b.get("input", {}), ensure_ascii=False):
            return False
    for ev in r.transcript_events():  # nor any event parented to it
        if ev.get("parent_tool_use_id") in ids \
                and "feat/5" in json.dumps(ev, ensure_ascii=False):
            return False
    return True

c.expect("patrol.md:84-85 (the work happens on qa/5)",
         "a fidelity-side dispatch targets qa/5", dispatch_on_qa5)
c.expect("ledger D2 + next-stage.md:305-310",
         "the fidelity dispatch and its child events never reference feat/5",
         dispatch_blind)
c.finish()
