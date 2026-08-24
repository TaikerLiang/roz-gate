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
# Stated limit (README, cannot-see list): this observes the ABSENCE of any
# feat/5 touch in the transcript; in-context leakage through text already
# in the session is invisible to any transcript check.
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()

def qa_checkout():
    for b in r.tool_uses(("Bash",)):
        blob = json.dumps(b.get("input", {}), ensure_ascii=False)
        if "qa/5" in blob and "checkout" in blob:
            return True
    return False

def feat_untouched():
    for b in r.tool_uses():
        if "feat/5" in json.dumps(b.get("input", {}), ensure_ascii=False):
            return False
    return True

c.expect("patrol.md:84-85 (the work happens on qa/5)",
         "qa/5 was checked out", qa_checkout)
c.expect("ledger D2 + next-stage.md:305-310",
         "no tool call ever references feat/5", feat_untouched)
c.finish()
