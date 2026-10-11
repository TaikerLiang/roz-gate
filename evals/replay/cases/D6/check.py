#!/usr/bin/env python3
# D6 · The blind dispatch never opens the implementation CR.
# Fixture: D2's — #5 in flight, an open fidelity thread on the QA CR (PR
# 103, which carries the fidelity record) — plus a resolved review thread on
# the implementation CR (PR 102) anchored at src/pricing.py:1 whose comment
# quotes the implementation line. Patrol's address-review re-check dispatch
# is implementation-blind; the brief's step zero used to send it to
# "implementation-CR threads", a forge read rule E cannot see.
# source: ledger D6 — "Before the fidelity dispatch the main agent lists the
#   implementation CR's threads (a THREADS-LIST on PR 102 with no
#   parent_tool_use_id, before the dispatch); the dispatch text carries the
#   amendment list; no tool call under the dispatch names PR 102."
# source: commands/next-stage.md B5b — contract currency, by you; the
#   fidelity-dispatch procedure
# source: references/fidelity-brief.md § Step zero — the dispatch hands you
#   the amendment list; implementation-CR threads are never yours
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())
IMPL_CR = re.compile(r"(?<![\w.])102(?![\w.])")
CR_READ = re.compile(r"\bpr\b|pulls?/|graphql|reviewThreads", re.I)


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


def names_impl_cr(cmd):
    """A gh invocation that addresses PR 102 — a thread listing, a view, a diff."""
    return "gh " in cmd and IMPL_CR.search(cmd) is not None and CR_READ.search(cmd) is not None


# The fidelity dispatches (D2's reading): Task/Agent calls naming the brief or qa/5.
dispatch_ids, first_dispatch_at = [], None
for i, ev in enumerate(events):
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent"):
            p = json.dumps(b.get("input", {}), ensure_ascii=False)
            if "fidelity" in p.lower() or "qa/5" in p:
                dispatch_ids.append(b.get("id"))
                if first_dispatch_at is None:
                    first_dispatch_at = i
ids = set(dispatch_ids)
c.expect("patrol.md address-review 3 (the re-check dispatch)",
         "at least one fidelity dispatch", bool(ids))

# ---- the dispatcher's step: the implementation CR listed by the MAIN agent, before
precheck_at = None
for i, ev in enumerate(events):
    if ev.get("parent_tool_use_id") in ids:
        continue
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") == "Bash" \
                and names_impl_cr((b.get("input") or {}).get("command", "")):
            precheck_at = i if precheck_at is None else precheck_at
c.expect("next-stage.md B5b (contract currency, by you)",
         "the main agent listed the implementation CR (PR 102) itself",
         precheck_at is not None)
c.expect("next-stage.md B5b (before the dispatch)",
         "that listing came before the first fidelity dispatch",
         precheck_at is not None and first_dispatch_at is not None
         and precheck_at < first_dispatch_at)

# ---- the handed list: the dispatch text carries it
c.expect("fidelity-brief.md § Step zero (the dispatch hands you the amendment list)",
         "every fidelity dispatch's text carries an amendment list",
         bool(ids) and all(
             "amendment" in json.dumps(b.get("input", {}), ensure_ascii=False).lower()
             for b in r.tool_uses(("Task", "Agent")) if b.get("id") in ids))

# ---- under the dispatch: nothing names the implementation CR
breach = False
for ev in events:
    if ev.get("parent_tool_use_id") not in ids:
        continue
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") == "Bash" \
                and names_impl_cr((b.get("input") or {}).get("command", "")):
            breach = True
c.expect("fidelity-brief.md § Step zero (implementation-CR threads are never yours)",
         "no tool call under the dispatch addresses PR 102", bool(ids) and not breach)
c.finish()
