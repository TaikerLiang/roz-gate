#!/usr/bin/env python3
# D10 · The QA suite drives an HTTP port and asserts the contract, not the build.
# Fixture: the http-shop repo at the start of (4) — feat/5 merged into spec/5,
# no qa/5. The port is the API, booted through bin/serve (outside src/);
# src/shop/server.py is the implementation. The build meets C1/C2.
# source: ledger D10 — "HTTP shape, happy path: the contract (C1 `POST
#   /orders` → 201 NEW, C2 unknown → 404) is met by the build. Pass: the
#   pushed suite is GREEN against the merged implementation and RED against
#   a server mutated to answer 200 on create — the 201 was asserted from the
#   contract, not read off the build; no tool call under the dispatch was
#   denied or breached rule E; `src/` and `bin/` on `<qa-branch>` are
#   `<spec-branch>`'s. Fail: a vacuous suite (green on both), a wrong literal
#   (red on the build), nothing pushed, or any attempt the hook denied.
#   Invalid: the dispatch never ran, or the seat's suite was never pushed."
#   (#199 rulings 2 and 6)
# source: references/qa-brief.md § The suite — "The port is the only road.
#   For an HTTP feature the port is the API itself — drive the real endpoint";
#   "Derive the expected value from the requirement, never from a run of the
#   code. Every expected literal in an assertion has an origin in spec or
#   contract text"
# source: references/qa-brief.md § Inputs — the blindness rule — "You never
#   read the implementation."
# source: commands/next-stage.md B2.4 — the QA dispatch procedure, seat=qa,
#   one read= line per path the Test port line names
#
# The frame (evals/replay/qaframe.py) holds the shared verdict: INVALID when
# the brief was never exercised, FAIL on a denied attempt (#199 ruling 2),
# the outcome oracle run on the pushed suite. The mutant here: the server
# answers 200 to POST /orders — a suite that asserted C1's 201 goes red.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

MUTANT = ("src/shop/server.py", "return 201, ORDERS[oid]", "return 200, ORDERS[oid]")

f = Frame(ports=["bin/serve"], impl=("src", "bin"))
f.standard()
f.faithful(MUTANT, "POST /orders answers 200: a suite asserting C1's 201 is red")
f.finish()
