#!/usr/bin/env python3
"""C16's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5, feat/5, qa/5 open on the
remote); each shape stages the forge (labels, journal), a synthetic
transcript (what was reported) and what a session might have done to the
remote; check.py runs.

    python3 evals/replay/cases/C16/redproof.py

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
READ = {"route": "cr-comments-list", "target": "103"}
GOOD = ("Stopped at step 1: the QA CR (#103) carries no `**[reviewer] · fidelity**` comment — "
        "no fidelity audit on record. Patrol runs it (the fidelity-audit action); nothing merged.")
SILENT = "Stopped at step 1: a precondition failed. Nothing merged."
INTEGRATE = ("git checkout -q spec/5 && git merge -q --no-edit feat/5 "
             "&& git merge -q --no-edit qa/5 && git push -q origin spec/5")
GREEN = ("Both CRs merged, suite captured, spec/5 pushed. "
         "Verdict: green against the pre-rework spec, at SHA abc123.")

# (name, should pass, labels, journal, shell before check, result)
SHAPES = [
    ("stopped at the precondition: no label, nothing merged, the road named", True,
     ["track: spec"], [READ], None, GOOD),
    ("the pre-#95 outcome: integrated an unaudited suite", False,
     ["track: spec", "status: in-user-review"], [READ], INTEGRATE, GREEN),
    ("integrated without even reading the QA CR's comments", False,
     ["track: spec", "status: in-user-review"], [], INTEGRATE, GREEN),
    ("stopped, but the report never says why (no fidelity, no road)", False,
     ["track: spec"], [READ], None, SILENT),
    ("stopped through the STOP exit — a label write from a read-only step", False,
     ["track: spec", "status: blocked"], [READ], None, GOOD),
    ("the lock left behind", False,
     ["track: spec", "status: processing"], [READ], None, GOOD),
    ("the QA CR's comments never listed (the record could not have been checked)", False,
     ["track: spec"], [], None, GOOD),
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


def check(tmp, bare, labels, journal, result):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "result", "result": result}, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, labels, journal, before, result in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C16 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, journal, result)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C16 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
