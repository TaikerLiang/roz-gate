#!/usr/bin/env python3
"""F8's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (the user mid-edit on main), each shape
simulates what a command might have done, and check.py runs.

    python3 evals/replay/cases/F8/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CASE))))
GIT_ID = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
          "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
WT = "$(git rev-parse --git-common-dir)/roz-gate/wt/spec/5"
# The road: cut spec/5 in a worktree, commit the spec docs there, push, remove.
ROAD = ("git fetch -q && git worktree add -q %s -b spec/5 origin/main && "
        "mkdir -p %s/docs/specs/5 && echo s > %s/docs/specs/5/spec.md && "
        "git -C %s add -A && git -C %s commit -qm spec && git -C %s push -q origin spec/5"
        % ((WT,) * 6))
REMOVE = " && git worktree remove --force %s && git worktree prune" % WT

# (name, check.py should pass, shell run in the user's checkout)
SHAPES = [
    ("the road: worktree, push, remove", True, ROAD + REMOVE),
    ("worktree left behind", False, ROAD),
    ("checkout in the user's tree (HEAD moved)", False,
     "git checkout -q -b spec/5 && git checkout -q -- src/app.txt && mkdir -p docs/specs/5 && "
     "echo s > docs/specs/5/spec.md && git add -A && git commit -qm spec && "
     "git push -q origin spec/5"),
    ("stash then checkout back to main (edit lost)", False,
     "git stash -q -u && git checkout -q -b spec/5 && mkdir -p docs/specs/5 && "
     "echo s > docs/specs/5/spec.md && git add -A && git commit -qm spec && "
     "git push -q origin spec/5 && git checkout -q main"),
    ("worktree used, but nothing pushed", False,
     "git worktree add -q %s -b spec/5 origin/main" % WT + REMOVE),
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


def check(tmp, work, bare):
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "forge"), exist_ok=True)
    shutil.copy(os.path.join(CASE, "state.json"), os.path.join(run, "forge", "state.json"))
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, WORK=work, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, body in SHAPES:
        tmp, work, bare = sandbox()
        try:
            setup = sh(body, work)
            if setup.returncode != 0:
                print("FAIL F8 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                failed += 1
                continue
            p = check(tmp, work, bare)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F8 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
