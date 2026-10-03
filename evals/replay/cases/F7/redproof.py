#!/usr/bin/env python3
"""F7's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh, a branch is cut by hand from each
candidate base, a CR is staged in the forge state, and check.py runs.

    python3 evals/replay/cases/F7/redproof.py

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
CUT = "git checkout -q -b spec/5 %s && mkdir -p docs/specs/5 && echo s > docs/specs/5/spec.md " \
      "&& git add -A && git commit -qm spec && git push -q origin spec/5"

# (name, check.py should pass, branch cut from, CR base or None for no CR)
SHAPES = [
    ("cut from the configured base, CR targets it", True, "release/20261006", "release/20261006"),
    ("cut from main, CR targets the base", False, "main", "release/20261006"),
    ("cut from the older release branch", False, "release/20260926", "release/20261006"),
    ("cut from the base, CR targets main", False, "release/20261006", "main"),
    ("cut from the base, no CR", False, "release/20261006", None),
    ("nothing pushed", False, None, None),
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


def check(tmp, bare, cr_base):
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "forge"), exist_ok=True)
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if cr_base:
        st["prs"] = {"101": {"number": 101, "headRefName": "spec/5", "baseRefName": cr_base,
                             "state": "OPEN", "isDraft": False}}
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, cut_from, cr_base in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if cut_from:
                setup = sh(CUT % cut_from, work)
                if setup.returncode != 0:
                    print("FAIL F7 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, cr_base)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F7 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
