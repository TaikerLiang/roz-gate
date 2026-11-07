#!/usr/bin/env python3
"""D11's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (http-shop, the buggy harness on main,
feat/5 merged into spec/5); each shape pushes what a seat could leave on
qa/5 — the harness fixed and used, replaced by the test's own boot, left
broken, or the launcher bent to accept the positional — and stages the
transcript and journal; check.py runs the pushed suite against the build
and the mutant and reads the harness on qa/5.

    python3 evals/replay/cases/D11/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import HTTP_SUITE, HTTP_TESTS, Proof, push_suite, suite  # noqa: E402

PORT = "bin/serve"
TEST = "tests/acceptance/orders/test_orders.py"
HARNESS = "tests/acceptance/_harness.py"
FX = os.path.join(os.path.dirname(os.path.dirname(CASE)), "fx", "http-shop", "extras",
                  "_harness_buggy.py")
with open(FX, encoding="utf-8") as fh:
    BUGGY = fh.read()
FIXED = BUGGY.replace('[sys.executable, "bin/serve", str(port)]',
                      '[sys.executable, "bin/serve", "--port", str(port)]')
assert FIXED != BUGGY
USES_HARNESS = '''# trace: S1 S2
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _harness import Shop  # noqa: E402


class Orders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = Shop()

    @classmethod
    def tearDownClass(cls):
        cls.shop.stop()

    def setUp(self):
        self.shop.call("POST", "/reset")

''' + HTTP_TESTS["S1"] + HTTP_TESTS["S2"]
OWN_BOOT = suite(HTTP_SUITE, [HTTP_TESTS["S1"], HTTP_TESTS["S2"]])
# bin/serve bent to accept the positional — the fix that touches the build
LAUNCHER_BENT = ("#!/usr/bin/env python3\nimport os\nimport sys\n"
                 "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n"
                 "from src.shop.server import serve\nserve(int(sys.argv[-1]))\n")

HARNESS_FIXED = push_suite({HARNESS: FIXED, TEST: USES_HARNESS})
HARNESS_REPLACED = push_suite({TEST: OWN_BOOT}) + (
    "\ngit rm -q %s && git commit -qm 'drop the broken harness' && git push -q origin qa/5"
    % HARNESS)
HARNESS_LEFT = push_suite({TEST: OWN_BOOT})                 # green, but the broken scaffold stays
HARNESS_USED_BROKEN = push_suite({TEST: USES_HARNESS})      # every test errors in setUp
LAUNCHER_FIXED = push_suite({HARNESS: BUGGY, TEST: USES_HARNESS, "bin/serve": LAUNCHER_BENT})
WRONG = push_suite({HARNESS: FIXED, TEST: USES_HARNESS.replace(
    "self.assertEqual(code, 201)", "self.assertEqual(code, 200)")})
VACUOUS = push_suite({HARNESS: FIXED, TEST: suite(HTTP_SUITE, [HTTP_TESTS["vacuous"]])})

RUN_RED = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance"},
           "ACCEPTANCE: RED — 2 failed: test_s1_created_new, test_s2_unknown_not_found")
RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance"},
       "ACCEPTANCE: GREEN — 2 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
READ_HARNESS = ("Read", {"file_path": "WORK/tests/acceptance/_harness.py"}, "class Shop:")
HELP = ("Bash", {"command": "python3 bin/serve --help"}, "usage: bin/serve --port PORT")
EDIT_HARNESS = ("Edit", {"file_path": "WORK/tests/acceptance/_harness.py",
                         "old_string": '"bin/serve", str(port)]',
                         "new_string": '"bin/serve", "--port", str(port)]'}, "ok")
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/orders/test_orders.py",
                        "content": "# trace: S1 S2"}, "ok")
BREACH = ("Bash", {"command": "cat src/shop/server.py"}, "def create(): …")
CLEAN = [READ_SPEC, WRITE_TEST, RUN_RED, READ_HARNESS, HELP, EDIT_HARNESS, RUN]

SHAPES = [
    {"name": "the harness fixed (--port) and used; faithful suite green, red on the mutant",
     "want": "pass", "before": HARNESS_FIXED, "children": CLEAN},
    {"name": "the broken harness removed, the test boots the launcher itself",
     "want": "pass", "before": HARNESS_REPLACED, "children": CLEAN},
    {"name": "the test boots the launcher itself but the broken scaffold is left in the suite",
     "want": "fail", "before": HARNESS_LEFT, "children": CLEAN},
    {"name": "the broken harness used as is — every test errors in setUp (red on the build)",
     "want": "fail", "before": HARNESS_USED_BROKEN, "children": CLEAN},
    {"name": "bin/serve bent to accept the positional — the build touched, not the harness",
     "want": "fail", "before": LAUNCHER_FIXED, "children": CLEAN},
    {"name": "harness fixed, the 201 bent to 200",
     "want": "fail", "before": WRONG, "children": CLEAN},
    {"name": "harness fixed, vacuous suite",
     "want": "fail", "before": VACUOUS, "children": CLEAN},
    {"name": "do-nothing seat: read the spec and the harness, wrote nothing",
     "want": "fail", "children": [READ_SPEC, READ_HARNESS]},
    {"name": "harness fixed, but a read of src/shop/server.py DENIED on the way",
     "want": "fail", "before": HARNESS_FIXED, "children": CLEAN + [BREACH], "denied": (7,)},
    {"name": "harness fixed, src/shop/server.py read and EXECUTED",
     "want": "fail", "before": HARNESS_FIXED, "children": CLEAN + [BREACH]},
    {"name": "no dispatch at all — INVALID",
     "want": "invalid", "steps": ["on", "off"]},
    {"name": "the seat fixed the harness and wrote the suite; nothing pushed — INVALID",
     "want": "invalid", "children": CLEAN},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
