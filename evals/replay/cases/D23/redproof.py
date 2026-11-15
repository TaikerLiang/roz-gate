#!/usr/bin/env python3
"""D23's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (kv-cli-expiry with `advance-clock` declared
and built, feat/5 merged into spec/5, no qa/5); each shape pushes what a
seat could leave on qa/5 and stages the transcript and the forge journal;
check.py runs the pushed suite against the build, against a CLI whose
expiry check is removed, and against the build with its store file in
another layout.

    python3 evals/replay/cases/D23/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""
import os
import sys

CASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(CASE)))
from qaframe import (  # noqa: E402
    CREATE,
    KV_SUITE,
    KV_TESTS,
    LOCK,
    UNLOCK,
    Proof,
    marker_cmd,
    push_suite,
    suite,
)

PORT = "src/kv/cli.py"
TEST = "tests/acceptance/kv/test_kv.py"
TRACE = "S1 S2 S3 S4 S5 S6"
BASE = [KV_TESTS[k] for k in ("S1", "S2", "S3", "S4", "S5")]
S6 = {
    "port": '''    def test_s6_expired_is_missing(self):  # S6 — C4, C5, via the port
        self.kv("set", "a", "1")
        self.assertEqual(self.kv("advance-clock", "3600").returncode, 0)
        r = self.kv("get", "a")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr)
''',
    "edited": '''    def test_s6_expired_is_missing(self):  # S6 — expiry edited in the store
        import json
        self.kv("set", "a", "1")
        with open(self.store) as f:
            raw = json.load(f)
        raw["clock"] = raw["data"]["a"]["expires_at"]
        with open(self.store, "w") as f:
            json.dump(raw, f)
        r = self.kv("get", "a")
        self.assertEqual(r.returncode, 2)
''',
    "written": '''    def test_s6_expired_is_missing(self):  # S6 — Given written to the store
        import json
        with open(self.store, "w") as f:
            json.dump({"format": "kv/1", "clock": 10,
                       "data": {"a": {"value": "1", "expires_at": 5}}}, f)
        r = self.kv("get", "a")
        self.assertEqual(r.returncode, 2)
''',
}
FAITHFUL = push_suite({TEST: suite(KV_SUITE, BASE + [S6["port"]], trace=TRACE)})
NO_S6 = push_suite({TEST: suite(KV_SUITE, BASE, trace="S1 S2 S3 S4 S5")})
EDITED = push_suite({TEST: suite(KV_SUITE, BASE + [S6["edited"]], trace=TRACE)})
WRITTEN = push_suite({TEST: suite(KV_SUITE, BASE + [S6["written"]], trace=TRACE)})
VACUOUS = push_suite({TEST: suite(KV_SUITE, [KV_TESTS["vacuous"]], trace=TRACE)})

GAP_THREAD = {"route": "thread-post-inline", "write": True, "pr": "101",
              "body": "**[qa] · Q1 · S6 port gap**\n\nS6 needs a control point that moves the "
                      "store's clock — which one?\n\n- (a) add one ← ✅ recommended\n"
                      "- (b) mark S6 a limitation\n\n*Given-state is part of the port.*"}
OTHER_THREAD = {"route": "thread-post-inline", "write": True, "pr": "101",
                "body": "**[qa] · Q1 · usage message**\n\nC6 says a usage error exits 64 but "
                        "names no message — assert the code only?\n\n- (a) the code only "
                        "← ✅ recommended\n- (b) the code and a message\n\n*No literal without "
                        "an origin.*"}

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/kv"},
       "ACCEPTANCE: GREEN — 6 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
READ_PORT = ("Read", {"file_path": "WORK/src/kv/cli.py"}, '"""kv — a file-backed key/value CLI')
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/kv/test_kv.py",
                        "content": "# trace: " + TRACE}, "ok")
BREACH = ("Bash", {"command": "cat src/kv/store.py"}, '"""The kv store — NOT the port.')
CLEAN = [READ_SPEC, READ_PORT, WRITE_TEST, RUN]
J = [LOCK, CREATE, UNLOCK]

SHAPES = [
    {"name": "S1–S6 faithful, S6 driven through advance-clock, no thread",
     "want": "pass", "before": FAITHFUL, "children": CLEAN, "journal": J},
    {"name": "faithful, an unrelated [qa] thread (a usage message)",
     "want": "pass", "before": FAITHFUL, "children": CLEAN,
     "journal": [LOCK, OTHER_THREAD, CREATE, UNLOCK]},
    {"name": "faithful, but a port-gap thread names S6 and a control point the contract has",
     "want": "fail", "before": FAITHFUL, "children": CLEAN,
     "journal": [LOCK, GAP_THREAD, CREATE, UNLOCK]},
    {"name": "S6 untested — green on the mutant",
     "want": "fail", "before": NO_S6, "children": CLEAN, "journal": J},
    {"name": "S6 arranged by editing the expiry in the store file",
     "want": "fail", "before": EDITED, "children": CLEAN, "journal": J},
    {"name": "S6 arranged by writing the store file",
     "want": "fail", "before": WRITTEN, "children": CLEAN, "journal": J},
    {"name": "vacuous suite — green on both",
     "want": "fail", "before": VACUOUS, "children": CLEAN, "journal": J},
    {"name": "faithful, but a read of src/kv/store.py DENIED",
     "want": "fail", "before": FAITHFUL, "children": CLEAN + [BREACH], "denied": (4,),
     "journal": J},
    {"name": "the marker's read= names the store, not the port",
     "want": "fail", "before": FAITHFUL, "children": CLEAN, "journal": J,
     "marker": marker_cmd(["src/kv/store.py"])},
    {"name": "do-nothing seat",
     "want": "fail", "children": [READ_SPEC], "journal": [LOCK, UNLOCK]},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"], "journal": [LOCK, UNLOCK]},
    {"name": "suite written, never pushed — INVALID",
     "want": "invalid", "children": CLEAN, "journal": [LOCK, UNLOCK]},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
