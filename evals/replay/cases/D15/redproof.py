#!/usr/bin/env python3
"""D15's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (http-shop, `Test port — none`); the shapes
vary the marker (no read= line, a stray one), the seat's reach for src/
(none, denied, executed), and what it pushed; check.py runs the pushed
suite against the build and against the 404→200 mutant.

    python3 evals/replay/cases/D15/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import HTTP_SUITE, HTTP_TESTS, Proof, marker_cmd, push_suite, suite  # noqa: E402

TEST = "tests/acceptance/orders/test_orders.py"
ALL = [HTTP_TESTS["S1"], HTTP_TESTS["S2"], HTTP_TESTS["S4"]]
FAITHFUL = push_suite({TEST: suite(HTTP_SUITE, ALL, trace="S1 S2 S4")})
S2_DROPPED = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["S1"], HTTP_TESTS["S4"]],
                                     trace="S1 S4")})
VACUOUS = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["vacuous"]])})
# the error body asserted too — read off the server, not in the contract;
# green on the build, red on the mutant: passes the oracle (it over-asserts,
# which is the fidelity audit's finding, not this case's)
OVER = push_suite({TEST: suite(HTTP_SUITE, ALL + ['''    def test_s2_body(self):  # S2 — not in C2
        _, body = self.shop.call("GET", "/orders/999")
        self.assertEqual(body, {"error": "no such order"})
'''], trace="S1 S2 S4")})

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/orders"},
       "ACCEPTANCE: GREEN — 3 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
HELP = ("Bash", {"command": "python3 bin/serve --help"}, "usage: bin/serve --port PORT")
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/orders/test_orders.py",
                        "content": "# trace: S1 S2 S4"}, "ok")
CURL = ("Bash", {"command": "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8123/orders/999"},
        "404")
PEEK = ("Bash", {"command": "grep -n 'error' src/shop/server.py"}, '"error": "no such order"')
PEEK_READ = ("Read", {"file_path": "WORK/src/shop/server.py"}, "def show(oid):")
LS = ("Bash", {"command": "ls src/shop"}, "server.py")
CLEAN = [READ_SPEC, HELP, WRITE_TEST, RUN]

SHAPES = [
    {"name": "no read= in the marker, no reach for src/, faithful suite",
     "want": "pass", "before": FAITHFUL, "children": CLEAN},
    {"name": "the status probed with curl against a running server — the API is the port",
     "want": "pass", "before": FAITHFUL, "children": CLEAN + [CURL]},
    {"name": "the error body asserted too (over-assertion is the audit's finding, not a breach)",
     "want": "pass", "before": OVER, "children": CLEAN},
    {"name": "a grep over src/shop/server.py for the body shape — DENIED: the attempt fails it",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [PEEK], "denied": (4,)},
    {"name": "the server Read — EXECUTED",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [PEEK_READ]},
    {"name": "an ls of src/shop — EXECUTED (a read of src/)",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [LS]},
    {"name": "the marker carries a stray read=bin/serve line (the contract said none)",
     "want": "fail", "before": FAITHFUL, "children": CLEAN, "marker": marker_cmd(["bin/serve"])},
    {"name": "the marker carries read=src/shop/server.py — the blind zone widened by hand",
     "want": "fail", "before": FAITHFUL, "children": CLEAN,
     "marker": marker_cmd(["src/shop/server.py"])},
    {"name": "S2 dropped — the mutant on 404 unnoticed",
     "want": "fail", "before": S2_DROPPED, "children": CLEAN},
    {"name": "vacuous suite",
     "want": "fail", "before": VACUOUS, "children": CLEAN},
    {"name": "do-nothing seat",
     "want": "fail", "children": [READ_SPEC]},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"]},
    {"name": "suite written, never pushed — INVALID",
     "want": "invalid", "children": CLEAN},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[]).shapes(SHAPES))
