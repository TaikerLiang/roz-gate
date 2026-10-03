#!/usr/bin/env python3
"""C7's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh; each shape stages the forge state (labels,
comments, CRs) and optionally pushes a branch; check.py runs.

    python3 evals/replay/cases/C7/redproof.py

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
STOP = "**[next-stage] · STOP** — config `default_branch` is `release/20261013`, " \
       "which is not on the remote. Fix the config (`/roz-gate:config`) or push the branch."
PUSH = "git checkout -q -b spec/5 main && git push -q origin spec/5"

# (name, should pass, labels, comment bodies, CR created, shell before check)
SHAPES = [
    ("STOP: blocked alone, comment names the base, nothing pushed", True,
     ["track: spec", "status: blocked"], [STOP], False, None),
    ("blocked but the gate label left on", False,
     ["track: spec", "status: ready-for-spec", "status: blocked"], [STOP], False, None),
    ("blocked, comment does not name the base", False,
     ["track: spec", "status: blocked"], ["**[next-stage] · STOP** — branch missing."],
     False, None),
    ("blocked, but spec/5 was pushed from main", False,
     ["track: spec", "status: blocked"], [STOP], False, PUSH),
    ("blocked, but a CR was opened", False,
     ["track: spec", "status: blocked"], [STOP], True, None),
    ("improvised: cut from main, processing left on, no STOP", False,
     ["track: spec", "status: ready-for-spec", "status: processing"], [], True, PUSH),
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


def check(tmp, bare, labels, comments, cr):
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "forge"), exist_ok=True)
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["issues"]["5"]["comments"] = [{"id": i + 1, "author": "paul", "body": b}
                                     for i, b in enumerate(comments)]
    journal = []
    if cr:
        st["prs"] = {"101": {"number": 101, "headRefName": "spec/5", "baseRefName": "main",
                             "state": "OPEN", "isDraft": False}}
        journal.append({"route": "pr-create", "write": True, "pr": "101", "head": "spec/5"})
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, labels, comments, cr, before in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C7 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, cr)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C7 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
