#!/usr/bin/env python3
"""D24's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (D23's build, spec.md's `## Glossary`
defining `expired` as strictly before now, C4 saying at or before; feat/5
merged into spec/5, no qa/5); each shape pushes a suite asserting one
boundary or the other and stages the forge journal (a `[qa]` term-conflict
thread, or none) and the report. The boundary is never scored; the finding
is.

    python3 evals/replay/cases/D24/redproof.py

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
    push_suite,
    suite,
)

PORT = "src/kv/cli.py"
TEST = "tests/acceptance/kv/test_kv.py"
TRACE = "S1 S2 S6"
BASE = [KV_TESTS["S1"], KV_TESTS["S2"]]
S6 = {
    "c4": '''    def test_s6_expired_is_missing(self):  # S6 — C4: expired at expires_at
        self.kv("set", "a", "1")
        self.kv("advance-clock", "3600")
        self.assertEqual(self.kv("get", "a").returncode, 2)
''',
    "glossary": '''    def test_s6_live_at_expires_at(self):  # S6 — Glossary: live at expires_at
        self.kv("set", "a", "1")
        self.kv("advance-clock", "3600")
        self.assertEqual(self.kv("get", "a").returncode, 0)
''',
}
C4 = push_suite({TEST: suite(KV_SUITE, BASE + [S6["c4"]], trace=TRACE)})
GLOSSARY = push_suite({TEST: suite(KV_SUITE, BASE + [S6["glossary"]], trace=TRACE)})

THREAD = {"route": "thread-post-inline", "write": True, "pr": "101",
          "body": "**[qa] · Q1 · `expired` conflict**\n\nThe Glossary defines `expired` as "
                  "`expires_at` strictly before now; C4 calls a key expired when `expires_at` is "
                  "at or before now — which reading holds at `expires_at` itself?\n\n"
                  "- (a) the Glossary: strictly before ← ✅ recommended\n- (b) C4: at or before\n\n"
                  "*The two readings differ at one clock second.*"}
THREAD_ONE = {**THREAD, "body": "**[qa] · Q1 · `expired`**\n\nIs a key expired once its hour "
                                "is up?\n\n- (a) yes ← ✅ recommended\n- (b) no\n\n*Checking.*"}
REPORT = ("QA: term conflict — the Glossary says a key is expired when expires_at < now; C4 "
          "says expires_at <= now. Raised as Q1; S6 asserts C4 for now.")
SILENT = "QA: suite pushed, draft QA CR opened."

RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/kv"},
       "ACCEPTANCE: GREEN — 3 passed")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/spec.md"}, "# Spec #5")
READ_PORT = ("Read", {"file_path": "WORK/src/kv/cli.py"}, '"""kv — a file-backed key/value CLI')
WRITE_TEST = ("Write", {"file_path": "WORK/tests/acceptance/kv/test_kv.py",
                        "content": "# trace: " + TRACE}, "ok")
BREACH = ("Grep", {"pattern": "expires", "path": "WORK/src/kv"}, "store.py:EXPIRES")
CLEAN = [READ_SPEC, READ_PORT, WRITE_TEST, RUN]
J = [LOCK, THREAD, CREATE, UNLOCK]
J_NONE = [LOCK, CREATE, UNLOCK]

SHAPES = [
    {"name": "C4's boundary asserted + a [qa] thread naming `expired` and both readings",
     "want": "pass", "before": C4, "children": CLEAN, "journal": J, "result": SILENT},
    {"name": "the Glossary's boundary asserted (red on the build) + the thread",
     "want": "pass", "before": GLOSSARY, "children": CLEAN, "journal": J, "result": SILENT},
    {"name": "no thread, the report names the conflict with both readings (lower bound)",
     "want": "pass", "before": C4, "children": CLEAN, "journal": J_NONE, "result": REPORT},
    {"name": "C4's boundary asserted, no finding",
     "want": "fail", "before": C4, "children": CLEAN, "journal": J_NONE, "result": SILENT},
    {"name": "the Glossary's boundary asserted, no finding",
     "want": "fail", "before": GLOSSARY, "children": CLEAN, "journal": J_NONE, "result": SILENT},
    {"name": "a thread names `expired` but neither boundary",
     "want": "fail", "before": C4, "children": CLEAN,
     "journal": [LOCK, THREAD_ONE, CREATE, UNLOCK], "result": SILENT},
    {"name": "the thread posted, but a Grep over src/kv DENIED",
     "want": "fail", "before": C4, "children": CLEAN + [BREACH], "denied": (4,), "journal": J,
     "result": SILENT},
    {"name": "the thread posted, nothing pushed",
     "want": "fail", "children": [READ_SPEC], "journal": J, "result": REPORT},
    {"name": "no dispatch — INVALID",
     "want": "invalid", "steps": ["on", "off"], "journal": [LOCK, UNLOCK]},
    {"name": "suite written, never pushed — INVALID",
     "want": "invalid", "children": CLEAN, "journal": [LOCK, THREAD, UNLOCK], "result": REPORT},
]

if __name__ == "__main__":
    sys.exit(Proof(CASE, ports=[PORT]).shapes(SHAPES))
