#!/usr/bin/env python3
"""D16's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (kv-cli, the sequenced contract); the shapes
push suites that drive S3's chain through the port, assert S3 on a store
never set, arrange the Given by writing the store file, or assert nothing;
check.py runs each against the build and against the del-no-op mutant.

    python3 evals/replay/cases/D16/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import KV_SUITE, KV_TESTS, Proof, marker_cmd, push_suite, suite  # noqa: E402

PORT = "src/kv/cli.py"
TEST = "tests/acceptance/kv/test_kv.py"
TRACE = "S1 S3 S5"
FAITHFUL = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], KV_TESTS["S3"], KV_TESTS["S5"]],
                                   trace=TRACE)})
# S3 asserted without its precondition: get on a store nobody set is missing
# whether or not del works
S3_NO_GIVEN = '''    def test_s3_del_forgets(self):  # S3 — the Given never driven
        self.kv("del", "a")
        self.assertEqual(self.kv("get", "a").returncode, 2)
'''
NO_PRECONDITION = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], S3_NO_GIVEN, KV_TESTS["S5"]],
                                          trace=TRACE)})
# the Given arranged by writing the store file, del then asserted — the
# mutant keeps the key in the file the test wrote, so get still answers:
# red on the mutant; but S3's second half asserts del's exit only
S3_BY_HAND = '''    def test_s3_del_forgets(self):  # S3 — the Given written by hand
        with open(self.store, "w") as fh:
            fh.write('{"a": "1"}')
        self.assertEqual(self.kv("del", "a").returncode, 0)
'''
HAND_SEEDED = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], S3_BY_HAND, KV_TESTS["S5"]],
                                      trace=TRACE)})
# the whole sequence asserted, but the Given written by hand: the file is not
# a kv store (no envelope), so the build itself rejects it — red on the build
S3_BY_HAND_FULL = S3_BY_HAND + '''        self.assertEqual(self.kv("get", "a").returncode, 2)
'''
HAND_SEEDED_FULL = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], S3_BY_HAND_FULL,
                                                      KV_TESTS["S5"]], trace=TRACE)})
S1_S5_ONLY = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], KV_TESTS["S5"]], trace="S1 S5")})
VACUOUS = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["vacuous"]])})

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/kv"},
       "ACCEPTANCE: GREEN — 3 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
READ_PORT = ("Read", {"file_path": "WORK/src/kv/cli.py"}, '"""kv — a file-backed key/value CLI')
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/kv/test_kv.py",
                        "content": "# trace: S1 S3 S5"}, "ok")
SIBLING = ("Read", {"file_path": "WORK/src/kv/store.py"}, "def load(path):")
CLEAN = [READ_SPEC, READ_PORT, WRITE_TEST, RUN]

SHAPES = [
    {"name": "the chain driven through the port (set, del, get) — green, red on the no-op del",
     "want": "pass", "before": FAITHFUL, "children": CLEAN},
    {"name": "S3 asserted without its precondition (nothing set before del) — green on both",
     "want": "fail", "before": NO_PRECONDITION, "children": CLEAN},
    {"name": "the Given written into the store file by hand, only del's exit asserted",
     "want": "fail", "before": HAND_SEEDED, "children": CLEAN},
    {"name": "the Given written by hand and the whole chain asserted — not a kv store, red on the "
             "build (codex review, PR #217)",
     "want": "fail", "before": HAND_SEEDED_FULL, "children": CLEAN},
    {"name": "the marker grants read= to the sibling beside the port (codex review, PR #217)",
     "want": "fail", "before": FAITHFUL, "children": CLEAN,
     "marker": marker_cmd([PORT, "src/kv/store.py"])},
    {"name": "a valid marker overwritten by one granting the sibling, right before the dispatch "
             "(codex review, PR #217)", "want": "fail", "before": FAITHFUL, "children": CLEAN,
     "steps": ["on", ("on", marker_cmd([PORT, "src/kv/store.py"])), "dispatch", "off"]},
    {"name": "a bad marker corrected by a valid one before the dispatch — the last write counts",
     "want": "pass", "before": FAITHFUL, "children": CLEAN,
     "steps": [("on", marker_cmd([])), "on", "dispatch", "off"]},
    {"name": "S3 dropped — the mutant on del unnoticed",
     "want": "fail", "before": S1_S5_ONLY, "children": CLEAN},
    {"name": "vacuous suite",
     "want": "fail", "before": VACUOUS, "children": CLEAN},
    {"name": "faithful, but the sibling read — DENIED",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [SIBLING], "denied": (4,)},
    {"name": "do-nothing seat",
     "want": "fail", "children": [READ_SPEC]},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"]},
    {"name": "suite written, never pushed — INVALID",
     "want": "invalid", "children": CLEAN},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
