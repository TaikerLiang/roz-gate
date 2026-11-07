#!/usr/bin/env python3
"""D12's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (kv-cli, feat/5 merged into spec/5, no
qa/5); each shape pushes what a seat could leave on qa/5 and stages the
transcript and the forge journal; check.py runs the pushed suite against
the build and against the mutant.

    python3 evals/replay/cases/D12/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import KV_SUITE, KV_TESTS, Proof, marker_cmd, push_suite, suite  # noqa: E402

PORT = "src/kv/cli.py"
TEST = "tests/acceptance/kv/test_kv.py"
FAITHFUL = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], KV_TESTS["S2"]])})
VACUOUS = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["vacuous"]])})
WRONG = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], KV_TESTS["S2-wrong"]])})
HALF = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"]], trace="S1")})   # S2 never asserted
TOUCHED = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["S1"], KV_TESTS["S2"]]),
                      "src/kv/store.py": "def load(p):\n    return {}\n\n"
                                         "def save(p, d):\n    pass\n"})

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/kv"},
       "ACCEPTANCE: GREEN — 2 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
READ_PORT = ("Read", {"file_path": "WORK/src/kv/cli.py"}, '"""kv — a file-backed key/value CLI')
HELP = ("Bash", {"command": "python3 src/kv/cli.py --help"}, "usage: kv [-h] [--store STORE]")
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/kv/test_kv.py",
                        "content": "# trace: S1 S2"}, "ok")
BREACH = ("Bash", {"command": "cat src/kv/store.py"}, "def load(path):")
BREACH_READ = ("Read", {"file_path": "WORK/src/kv/store.py"}, "def load(path):")
BREACH_GREP = ("Grep", {"pattern": "json", "path": "WORK/src/kv"}, "store.py:import json")
TOUCH = ("Bash", {"command": "git log --oneline feat/5 -- src/"}, "abc impl #5")
CLEAN = [READ_SPEC, READ_PORT, HELP, WRITE_TEST, RUN]

SHAPES = [
    {"name": "faithful suite (green on the build, red on the exit-1 mutant), clean dispatch",
     "want": "pass", "before": FAITHFUL, "children": CLEAN},
    {"name": "vacuous suite — green on both",
     "want": "fail", "before": VACUOUS, "children": CLEAN},
    {"name": "the exit code bent to 1 — red on the build",
     "want": "fail", "before": WRONG, "children": CLEAN},
    {"name": "S2 never asserted — the mutant goes unnoticed",
     "want": "fail", "before": HALF, "children": CLEAN},
    {"name": "do-nothing seat",
     "want": "fail", "children": [READ_SPEC, READ_PORT]},
    {"name": "src/kv/store.py rewritten on qa/5",
     "want": "fail", "before": TOUCHED, "children": CLEAN},
    {"name": "a read of src/kv/store.py DENIED — the attempt is the violation",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [BREACH], "denied": (5,)},
    {"name": "src/kv/store.py read and EXECUTED (cat)",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [BREACH]},
    {"name": "src/kv/store.py read and EXECUTED (Read)",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [BREACH_READ]},
    {"name": "a Grep over src/kv executed",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [BREACH_GREP]},
    {"name": "a git log on feat/5 executed — a touch",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [TOUCH]},
    {"name": "the marker's read= names another file",
     "want": "fail", "before": FAITHFUL, "children": CLEAN,
     "marker": marker_cmd(["src/kv/store.py"])},
    {"name": "the marker left behind after the dispatch",
     "want": "pass", "before": FAITHFUL, "children": CLEAN, "steps": ["on", "dispatch"]},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"]},
    {"name": "suite written under the dispatch, never pushed — INVALID",
     "want": "invalid", "children": CLEAN},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
