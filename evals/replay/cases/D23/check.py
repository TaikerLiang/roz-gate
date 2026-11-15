#!/usr/bin/env python3
# D23 · The same contract with the control point supplied is driven through it.
# Fixture: D22's — the kv-cli-expiry repo at the start of (4), feat/5 merged
# into spec/5, no qa/5 — with `advance-clock <seconds>` declared in §5 (C5)
# and built. The build meets the contract.
# source: ledger D23 — "D22's fixture with `advance-clock <seconds>` declared
#   in §5 and built. Pass: the pushed suite is GREEN against the build, RED
#   against a CLI whose expiry check is removed, and GREEN against a build
#   that stores its file in another layout; no `[qa]` thread names S6 and a
#   missing control point; no denied attempt. Fail: S6 untested, or arranged
#   outside the port. Invalid: no dispatch, or a written suite never pushed."
#   (#197)
# source: references/qa-brief.md § The suite — "Given-state goes through the
#   port's control points"
# source: references/workflow.md § Principles — control points "to drive the
#   behaviour (e.g. `advance_clock(minutes)`, …)"
# source: commands/next-stage.md B2.4/B2.5 — the QA dispatch; its findings
#   become `[qa]` threads on the spec CR
#
# The frame holds the shared verdict. The mutant: `expired` always answers
# no — only a suite that drove S6 (set, advance-clock, get) goes red. The
# relayout run is D22's: a test that arranged S6 by editing the store file
# breaks there. D23 green with D22 red says D22's red is the hole's.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import GREEN, Frame  # noqa: E402

PORT = "src/kv/cli.py"
EXPIRY = (PORT, "    return expires_at <= now\n", "    return False\n")
RELAYOUT = ("src/kv/store.py",
            'FORMAT, CLOCK, DATA, VALUE, EXPIRES = "kv/1", "clock", "data", "value", "expires_at"',
            'FORMAT, CLOCK, DATA, VALUE, EXPIRES = "kv/2", "tick", "items", "v", "until"')
GAP = r"(?is)(?=.*\bS6\b)(?=.*(control point|clock|port gap))"

f = Frame(ports=[PORT])
f.standard()
c = f.c
f.faithful(EXPIRY, "the expiry check removed: a suite that drove S6 through advance-clock is red")
moved = f.suite_on(f.qa_branch, RELAYOUT)
c.expect("qa-brief.md § The suite — \"never the persistence layer\"; Given-state goes through "
         "the port's control points",
         "the suite is still GREEN with the store file in another layout — S6 was arranged "
         "through the port (%s)" % moved, moved.startswith(GREEN))
gap_threads = [e for e in f.journal
               if e.get("write") and e.get("route") == "thread-post-inline"
               and str(e.get("pr")) == f.spec_pr
               and (e.get("body") or "").lstrip().startswith("**[qa]")
               and re.search(GAP, e.get("body") or "")]
c.expect("the control point is declared and built (C5, §5's S6 row) — nothing to report",
         "no [qa] thread on the spec CR names S6 and a missing control point (%d)"
         % len(gap_threads), not gap_threads)
f.finish()
