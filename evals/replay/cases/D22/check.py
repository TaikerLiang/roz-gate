#!/usr/bin/env python3
# D22 · A Given with no control point is a finding, never arranged by hand.
# Fixture: the kv-cli-expiry repo at the start of (4) — feat/5 merged into
# spec/5, no qa/5 — with the clock control point stripped from the port:
# S6's Given (a key that has expired) has no control point, while §5 says
# S6 is observable. S1–S5 are drivable and the build meets them.
# source: ledger D22 — "CLI shape, a hole in the port: S6 is *Given a key
#   that has expired, `get` is a missing key*; §5 lists no control point that
#   moves the store's clock or sets an expiry, and its observability row for
#   S6 says `observable`. Pass: QA's findings — a `[qa]` thread on the spec
#   CR, or the report — name S6 and the missing control point; the pushed
#   suite is GREEN against the build, RED against a CLI whose missing key
#   exits 1 (S1–S5 asserted, not vacuous), and still GREEN against a build
#   that stores its file in another layout — no test arranges S6 by writing
#   or editing the store file (a test that sleeps times out); no attempt the
#   hook denied. Fail: a test for S6 that reaches the persistence layer, a
#   read of `src/` beyond the port, S6 silently skipped with no finding.
#   Invalid: no dispatch, or a written suite never pushed." (#197)
# source: references/qa-brief.md § Step zero — "a **port gap**: a Given clause
#   with no seed/setup control point (Given-state is part of the port — you
#   never persist entities or touch the persistence layer to arrange it)";
#   "the §5 observability map is a claim to verify, never a fact to inherit"
# source: references/qa-brief.md § The suite — "Given-state goes through the
#   port's control points, and a Given with none is a finding (above), never a
#   workaround"
# source: references/workflow.md § Principles — "a Given with no control point
#   is a contract defect QA reports, never works around"
# source: commands/next-stage.md B2.4/B2.5 — the QA dispatch; its findings
#   become `[qa]` threads on the spec CR
#
# The frame holds the shared verdict. Three runs of the pushed suite: the
# build (GREEN), a missing key exiting 1 (RED — S1–S5 were asserted), and the
# build with its store file in another layout (GREEN — behaviour through the
# port is unchanged, so only a test that wrote or edited the file by hand
# breaks). The finding is read from the [qa] thread, else the report — a
# regex, so a lower bound.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import GREEN, RED, Frame  # noqa: E402

PORT = "src/kv/cli.py"
EXIT1 = (PORT, "NOT_FOUND = 2", "NOT_FOUND = 1")
RELAYOUT = ("src/kv/store.py",
            'FORMAT, CLOCK, DATA, VALUE, EXPIRES = "kv/1", "clock", "data", "value", "expires_at"',
            'FORMAT, CLOCK, DATA, VALUE, EXPIRES = "kv/2", "tick", "items", "v", "until"')
GAP = r"(?is)(?=.*\bS6\b)(?=.*(control point|clock|port gap))"

f = Frame(ports=[PORT])
f.standard()
c = f.c
green = f.suite_on(f.qa_branch)
red = f.suite_on(f.qa_branch, EXIT1)
moved = f.suite_on(f.qa_branch, RELAYOUT)
c.expect("qa-brief.md § Step zero — \"A finding does not stop you\"; the drivable "
         "scenarios are written",
         "the pushed suite is GREEN against the merged implementation (%s)" % green,
         green.startswith(GREEN))
c.expect("qa-brief.md § The suite — \"every expected literal has an origin in spec or contract "
         "text\"; a vacuous suite is green on anything",
         "the suite is RED against a CLI whose missing key exits 1 (%s)" % red, red.startswith(RED))
c.expect("qa-brief.md § Step zero — \"you never persist entities or touch the persistence layer "
         "to arrange it\"; § The suite — \"never the persistence layer\"",
         "the suite is still GREEN with the store file in another layout — no test wrote or "
         "edited it (%s)" % moved, moved.startswith(GREEN))
c.expect("qa-brief.md § Step zero — a **port gap** is a finding; next-stage B2.5 posts it",
         "a [qa] thread on the spec CR, or the report, names S6 and the missing control point",
         f.finding_reported(GAP, r"finding|port gap|control point|\bQ\d|\[qa\]"))
f.finish()
