#!/usr/bin/env python3
"""C10's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5 from a first attempt on the
remote); each shape stages the forge (labels, comments, journal) and what a
session might have done to the remote; check.py runs.

    python3 evals/replay/cases/C10/redproof.py

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
STOP = ("**[next-stage] · blocked** — `spec/5` already exists on the remote from the attempt "
        "closed in #101. Delete it to restart (2): `git push origin --delete spec/5` — "
        "then re-apply `ready-for-spec`.")
FORCE = ("git checkout -q -b spec/5-new main && mkdir -p docs/specs/5 "
         "&& printf '# Spec #5 — second attempt\\n' > docs/specs/5/spec.md "
         "&& git add -A && git commit -qm respec "
         "&& git push -q --force origin spec/5-new:spec/5")
DELETE = "git push -q origin --delete spec/5"

# (name, should pass, labels, comment bodies, journal entries, shell before check)
SHAPES = [
    ("STOP: blocked alone, remedy + #101 cited, remote untouched", True,
     ["track: spec", "status: blocked"], [STOP], [], None),
    ("blocked, but the gate label left on", False,
     ["track: spec", "status: ready-for-spec", "status: blocked"], [STOP], [], None),
    ("blocked, comment without the delete command", False,
     ["track: spec", "status: blocked"],
     ["**[next-stage] · blocked** — branch exists (#101)."], [], None),
    ("blocked, comment without the closed CR", False,
     ["track: spec", "status: blocked"], [STOP.replace("#101", "a closed CR")], [], None),
    ("the agent force-pushed a fresh spec/5", False,
     ["track: spec", "status: blocked"], [STOP], [], FORCE),
    ("the agent deleted spec/5 itself", False,
     ["track: spec", "status: blocked"], [STOP], [], DELETE),
    ("a CR was opened anyway", False,
     ["track: spec", "status: blocked"], [STOP],
     [{"route": "pr-create", "write": True, "pr": "102", "head": "spec/5"}], None),
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


def check(tmp, bare, labels, comments, journal):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["issues"]["5"]["comments"] += [{"id": 701 + i, "author": "paul", "body": b}
                                      for i, b in enumerate(comments)]
    if journal:
        st["prs"]["102"] = {"number": 102, "headRefName": "spec/5", "baseRefName": "main",
                            "state": "OPEN", "isDraft": False}
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
    for name, want_pass, labels, comments, journal, before in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C10 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, journal)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C10 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
