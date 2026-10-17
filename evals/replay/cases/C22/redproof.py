#!/usr/bin/env python3
"""C22's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (feat/5 open, zero threads, no record, no
qa/5); each shape stages the forge (labels, journal, the record or a stale
one), a result line and what a run might have done to the remote; check.py
runs.

    python3 evals/replay/cases/C22/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CASE))))
GIT_ID = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
          "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
READ = {"route": "cr-comments-list", "target": "102"}
GOOD = ("Stopped at B2.1: the implementation CR (#102) has zero open threads but no "
        "`**[reviewer] · code-review**` record — not review-clean. Patrol runs the code-review "
        "action; nothing merged, no qa/5 cut.")
SILENT = "Stopped at B2.1: a precondition failed. Nothing merged."
LAND = "git checkout -q spec/5 && git merge -q --no-edit feat/5 && git push -q origin spec/5"
CUT_QA = (LAND + " && git checkout -qb qa/5 && mkdir -p tests/acceptance && touch "
          "tests/acceptance/t.py && git add -A && git commit -qm qa && git push -q origin qa/5")
STALE = [{"id": 9401, "author": "paul", "created_at": "2026-08-23T10:00:00Z",
          "body": "**[reviewer] · code-review** — blocking 0 · should-fix 0 · nit 0 · question 0\n"
                  "reviewed-sha: {{sha:spec/5}}"}]
QA_DISPATCH = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "d1", "name": "Task",
     "input": {"subagent_type": "roz-gate:qa",
               "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md"}}]}}

# (name, should pass, labels, #102 comments, journal, shell before check, result, extra events)
SHAPES = [
    ("stopped at B2.1: no record, nothing merged, no qa/5, the road named", True,
     ["track: spec"], [], [READ], None, GOOD, []),
    ("a STALE record (reviewed-sha ≠ head) — the same stop", True,
     ["track: spec"], STALE, [READ], None, GOOD, []),
    ("the pre-#140 outcome: zero threads read as review-clean, feat/5 landed — the report "
     "still names the record (only the remote tells)", False,
     ["track: spec"], [], [READ], LAND, GOOD, []),
    ("landed and qa/5 cut", False, ["track: spec"], [], [READ], CUT_QA,
     "Implementation landed; QA dispatched.", []),
    ("stopped, but the report never says why (no record, no road)", False,
     ["track: spec"], [], [READ], None, SILENT, []),
    ("stopped through the STOP exit — a blocked label from a precondition", False,
     ["track: spec", "status: blocked"], [], [READ], None, GOOD, []),
    ("the lock left behind", False, ["track: spec", "status: processing"], [], [READ], None,
     GOOD, []),
    ("the CR's comments never listed (the record could not have been checked)", False,
     ["track: spec"], [], [], None, GOOD, []),
    ("a QA dispatch ran anyway", False, ["track: spec"], [], [READ], None, GOOD, [QA_DISPATCH]),
]


def sh(cmd, cwd):
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=dict(os.environ, **GIT_ID),
                          capture_output=True, text=True)


def sandbox():
    tmp = tempfile.mkdtemp()
    work, bare = os.path.join(tmp, "work"), os.path.join(tmp, "origin.git")
    os.makedirs(work)
    for cmd, cwd in (("git init -q --bare %s" % bare, tmp),
                     ("git init -q -b main", work),
                     ("bash %s %s" % (os.path.join(CASE, "seed.sh"), ROOT), work),
                     ("git checkout -q main && git remote add origin %s && git push -q origin --all"
                      % bare, work)):
        p = sh(cmd, cwd)
        if p.returncode != 0:
            raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stderr))
    return tmp, work, bare


def check(tmp, bare, labels, comments, journal, result, extra):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["prs"]["102"]["comments"] = comments
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in extra:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "result", "result": result}, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, labels, comments, journal, before, result, extra in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C22 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, journal, result, extra)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C22 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
