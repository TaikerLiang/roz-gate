#!/usr/bin/env python3
"""D17's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (http-shop, C3 as built = RESERVED, the
drafted HELD in the history); the shapes push suites asserting the as-built
literal, the drafted one, neither, or nothing; check.py runs each against
the build and against the server mutated back to HELD.

    python3 evals/replay/cases/D17/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import HTTP_SUITE, HTTP_TESTS, Proof, push_suite, suite  # noqa: E402

PORT = "bin/serve"
TEST = "tests/acceptance/orders/test_orders.py"
TRACE = "S1 S3 S4"
AS_BUILT = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["S1"], HTTP_TESTS["S3"],
                                               HTTP_TESTS["S4"]], trace=TRACE)})
DRAFTED = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["S1"], HTTP_TESTS["S3-drafted"],
                                               HTTP_TESTS["S4"]], trace=TRACE)})
S3_DROPPED = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["S1"], HTTP_TESTS["S4"]],
                                     trace="S1 S4")})
# S3 asserted on the status code only — the deviation's literal never checked
S3_CODE = '''    def test_s3_reserve(self):  # S3 — C3, the status code alone
        _, order = self.shop.call("POST", "/orders")
        code, _ = self.shop.call("POST", "/orders/%d/reserve" % order["id"])
        self.assertEqual(code, 200)
'''
S3_STATUS_ONLY = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["S1"], S3_CODE, HTTP_TESTS["S4"]],
                                         trace=TRACE)})
VACUOUS = push_suite({TEST: suite(HTTP_SUITE, [HTTP_TESTS["vacuous"]])})

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/orders"},
       "ACCEPTANCE: GREEN — 3 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
READ_PORT = ("Read", {"file_path": "WORK/bin/serve"}, "#!/usr/bin/env python3")
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/orders/test_orders.py",
                        "content": "# trace: S1 S3 S4"}, "ok")
PEEK = ("Bash", {"command": "grep -n RESERVED src/shop/server.py"}, 'o["status"] = "RESERVED"')
CR_THREADS = ("Bash", {"command": "gh api repos/acme/demo/pulls/102/comments"}, "[]")
CLEAN = [READ_SPEC, READ_PORT, WRITE_TEST, RUN]

SHAPES = [
    {"name": "the as-built RESERVED asserted — green on the build, red on the HELD mutant",
     "want": "pass", "before": AS_BUILT, "children": CLEAN},
    {"name": "the drafted HELD asserted — red on the build",
     "want": "fail", "before": DRAFTED, "children": CLEAN},
    {"name": "S3 dropped — the mutant unnoticed",
     "want": "fail", "before": S3_DROPPED, "children": CLEAN},
    {"name": "S3 asserted on the status code alone — the deviation's literal never checked",
     "want": "fail", "before": S3_STATUS_ONLY, "children": CLEAN},
    {"name": "vacuous suite",
     "want": "fail", "before": VACUOUS, "children": CLEAN},
    {"name": "the literal confirmed by grepping the server — DENIED: the attempt fails it",
     "want": "fail", "before": AS_BUILT, "children": CLEAN + [PEEK], "denied": (4,)},
    {"name": "the literal confirmed by grepping the server — EXECUTED",
     "want": "fail", "before": AS_BUILT, "children": CLEAN + [PEEK]},
    {"name": "the implementation CR's comments listed from inside the dispatch — not a src/ read "
             "(D6's gap: rule E cannot see it; recorded, not scored here)",
     "want": "pass", "before": AS_BUILT, "children": CLEAN + [CR_THREADS]},
    {"name": "do-nothing seat",
     "want": "fail", "children": [READ_SPEC]},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"]},
    {"name": "suite written, never pushed — INVALID",
     "want": "invalid", "children": CLEAN},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
