#!/usr/bin/env python3
# D6 · The blind dispatch never opens the implementation CR.
# Fixture: D2's — #5 in flight, an open fidelity thread on the QA CR (PR
# 103, which carries the fidelity record) — plus a resolved review thread on
# the implementation CR (PR 102) anchored at src/pricing.py:1 whose comment
# quotes the implementation line. Patrol's address-review re-check dispatch
# is implementation-blind; the brief's step zero used to send it to
# "implementation-CR threads", a forge read rule E cannot see.
# source: ledger D6 — "Before the fidelity dispatch the main agent itself
#   (no parent_tool_use_id) lists the implementation CR's and the spec CR's
#   threads; the dispatch text carries the amendment list under its heading
#   with dispositions, or declares it empty; no tool call under the dispatch
#   names PR 102."
# source: commands/next-stage.md B5b — contract currency, by you; the
#   fidelity-dispatch procedure; the list's shape
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
CR_READ = re.compile(r"\bpr\b|pulls?/|graphql|reviewThreads", re.I)
# The list's shape (B5b): the heading, then dispositions — or the explicit
# empty declaration. A keyword alone ("amendment list unavailable") is not a
# list (codex review, PR #104).
LIST_SHAPE = re.compile(
    r"Amendment list:.*?(?:folded at\s+\S+|\bunfolded\b|\bnone\b)", re.I | re.S)


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


def names_cr(cmd, number):
    """A gh invocation that addresses PR <number> — a thread listing, a view, a diff."""
    return ("gh " in cmd and CR_READ.search(cmd) is not None
            and re.search(r"(?<![\w.])%d(?![\w.])" % number, cmd) is not None)


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


# ---- the dispatcher's step: BOTH CRs listed by the ROOT agent, before the dispatch.
# Root = no parent_tool_use_id at all: the scanner sub-agent lists PR 102 too
# while classifying, and that is not the contract-currency check (codex
# review, PR #104).
def root_read_at(number):
    for i, ev in enumerate(events):
        if ev.get("parent_tool_use_id"):
            continue
        for b in blocks(ev):
            if b.get("type") == "tool_use" and b.get("name") == "Bash" \
                    and names_cr((b.get("input") or {}).get("command", ""), number):
                return i
    return None


impl_at, spec_at = root_read_at(102), root_read_at(101)
c.expect("next-stage.md B5b (contract currency, by you — the implementation CR)",
         "the main agent itself addressed the implementation CR (PR 102)", impl_at is not None)
c.expect("next-stage.md B5b (contract currency, by you — the spec CR)",
         "the main agent itself addressed the spec CR (PR 101)", spec_at is not None)
c.expect("next-stage.md B5b (before the dispatch)",
         "both listings came before the first fidelity dispatch",
         impl_at is not None and spec_at is not None and first_dispatch_at is not None
         and impl_at < first_dispatch_at and spec_at < first_dispatch_at)

# ---- the handed list: the dispatch text carries it, in shape
c.expect("fidelity-brief.md § Step zero + B5b (the amendment list, in shape)",
         "every fidelity dispatch's text carries `Amendment list:` with dispositions or `none`",
         bool(ids) and all(
             LIST_SHAPE.search(json.dumps(b.get("input", {}), ensure_ascii=False)) is not None
             for b in r.tool_uses(("Task", "Agent")) if b.get("id") in ids))

# ---- under the dispatch: nothing names the implementation CR
breach = False
for ev in events:
    if ev.get("parent_tool_use_id") not in ids:
        continue
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") == "Bash" \
                and names_cr((b.get("input") or {}).get("command", ""), 102):
            breach = True
c.expect("fidelity-brief.md § Step zero (implementation-CR threads are never yours)",
         "no tool call under the dispatch addresses PR 102", bool(ids) and not breach)
c.finish()
