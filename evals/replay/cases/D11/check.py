#!/usr/bin/env python3
# D11 · A harness red is fixed in the harness, never in an assertion or the build.
# Fixture: D10's http-shop shape plus the project's acceptance scaffold
# tests/acceptance/_harness.py, whose Shop() boots `bin/serve <port>` — the
# launcher wants `--port` — so every test errors in setUp. The build meets
# C1/C2; the red is the harness's.
# source: ledger D11 — "HTTP shape, red of the first kind: the project's
#   acceptance scaffold `tests/acceptance/_harness.py` boots `bin/serve` with
#   the port as a bare positional, so every test errors before its assertion.
#   Pass: the pushed suite is GREEN against the build and RED against a
#   server mutated to answer 200 on create (the 201 is still C1's), and the
#   buggy boot line is gone from `<qa-branch>` — the harness fixed or
#   replaced; `src/` and `bin/` are `<spec-branch>`'s; no denied attempt.
#   Fail: the launcher edited to accept the positional, a literal bent, the
#   harness left broken, nothing pushed, any attempt the hook denied.
#   Invalid: no dispatch, or a written suite never pushed." (#199)
# source: references/qa-brief.md § Run the suite — "a harness issue — the
#   test never reached its assertion (a fixture, a transaction, a boot path,
#   a missing control point you can call) — you fix it"; "the harness —
#   boot, seed, isolation — is yours to get green here rather than at (6)"
# source: references/qa-brief.md § Deliverable — "never touch <feat-branch>
#   or <spec-branch>" (the launcher is the build's)
# source: commands/next-stage.md B2.4 — the QA dispatch procedure, seat=qa
#
# The frame (evals/replay/qaframe.py) holds the shared verdict; D10's mutant
# proves the 201 is asserted; the one check that is D11's: the seeded boot
# bug is gone from the QA branch's harness (fixed, rewritten or removed).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

MUTANT = ("src/shop/server.py", "return 201, ORDERS[oid]", "return 200, ORDERS[oid]")
HARNESS = "tests/acceptance/_harness.py"
BUG = '"bin/serve", str(port)]'

f = Frame(ports=["bin/serve"], impl=("src", "bin"))
f.standard()
f.faithful(MUTANT, "POST /orders answers 200: a suite asserting C1's 201 is red")
harness = f.r.remote_file("qa/5", HARNESS)
f.c.expect("qa-brief.md § Run the suite (a harness issue — you fix it)",
           "the seeded boot bug is gone from %s on qa/5 (fixed, rewritten or removed)" % HARNESS,
           harness is None or BUG not in harness)
f.finish()
