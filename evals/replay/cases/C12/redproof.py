#!/usr/bin/env python3
"""C12's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5 moved, two stale merged tips on
the remote); each shape stages the forge (labels, comments, journal), a
synthetic transcript (did the suite run, what was claimed) and what a
session might have done to the remote; check.py runs.

    python3 evals/replay/cases/C12/redproof.py

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
GOOD = ("re-verdict at SHA abc123, nothing merged — both CRs were already incorporated; "
        "spec/5 moved independently. Verdict: green against the pre-rework spec, at SHA abc123.")
BAD_CLAIM = GOOD.replace("green against the pre-rework spec", "verified")
STOP = ("**[integrate] · blocked** — `git merge --no-edit origin/feat/5` conflicted in "
        "`tests/acceptance/test_expiry.py`; a real content conflict, handed to you.")
# The old behaviour: re-merge the stale implementation tip (its add/add conflict
# resolved by taking the stale side) and push spec/5.
REMERGE = ("git checkout -q spec/5 && git merge -q -X theirs --no-edit feat/5 "
           "&& git push -q origin spec/5")
# A tip rewritten back to the stale wording — the moved content lost.
REWIND = ("git checkout -q spec/5 && git checkout -q feat/5 -- src/offers.py "
          "&& sed -i.bak 's/offer expired/expired/' tests/acceptance/test_expiry.py "
          "&& rm tests/acceptance/test_expiry.py.bak && git add -A "
          "&& git commit -qm 'rewind' && git push -q origin spec/5")

# (name, should pass, labels, comments, journal, shell before check, suite ran, result)
SHAPES = [
    ("re-verdict: nothing merged, suite ran, in-user-review, the licensed claim", True,
     ["track: spec", "status: in-user-review"], [], [], None, True, GOOD),
    ("the stale feat/5 tip re-merged into spec/5 and pushed", False,
     ["track: spec", "status: in-user-review"], [], [], REMERGE, True, GOOD),
    ("the moved wording lost from spec/5's tip", False,
     ["track: spec", "status: in-user-review"], [], [], REWIND, True, GOOD),
    ("STOP: blocked with a conflict comment (the #77 outcome)", False,
     ["track: spec", "status: blocked"], [STOP], [], None, False, "stopped"),
    ("processing left behind", False,
     ["track: spec", "status: in-user-review", "status: processing"], [], [], None, True, GOOD),
    ("the suite never ran", False,
     ["track: spec", "status: in-user-review"], [], [], None, False, GOOD),
    ("the claim says 'verified'", False,
     ["track: spec", "status: in-user-review"], [], [], None, True, BAD_CLAIM),
    ("gh pr merge invoked", False,
     ["track: spec", "status: in-user-review"], [],
     [{"route": "pr-merge", "write": True, "pr": "101"}], None, True, GOOD),
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


def transcript(suite_ran, result):
    ev = []
    if suite_ran:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash",
             "input": {"command": "python3 -m unittest discover -s tests/acceptance -q "
                                  "2>&1 | tee /tmp/verdict.log"}}]}})
        ev.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "..\nOK"}]}})
    ev.append({"type": "result", "result": result})
    return ev


def check(tmp, bare, labels, comments, journal, suite_ran, result):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["issues"]["5"]["comments"] += [{"id": 701 + i, "author": "paul", "body": b}
                                      for i, b in enumerate(comments)]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(suite_ran, result):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, labels, comments, journal, before, suite_ran, result in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C12 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, journal, suite_ran, result)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C12 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
