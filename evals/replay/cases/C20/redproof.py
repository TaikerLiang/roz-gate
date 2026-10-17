#!/usr/bin/env python3
"""C20's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5, feat/5 open with its record, no
qa/5 on the remote); each shape stages what a Path B2 run might have done to
the remote, the forge (labels, journal, the QA CR) and a synthetic
transcript (the marker, the QA dispatch, in the order given); check.py runs.

    python3 evals/replay/cases/C20/redproof.py

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
GITDIR = "$(git rev-parse --git-common-dir)/roz-gate"
MARKER_ON = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\nread=src/pricing.py\\nseat=qa\\n\''
             ' > "%s/fidelity-dispatch"' % (GITDIR, GITDIR))
MARKER_ON_NOSEAT = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\nread=src/pricing.py\\n\''
                    ' > "%s/fidelity-dispatch"' % (GITDIR, GITDIR))
MARKER_OFF = 'rm -f "%s/fidelity-dispatch"' % GITDIR
QA_TEST = ("mkdir -p tests/acceptance/offers && printf '# trace: S1\\n' "
           "> tests/acceptance/offers/test_expiry.py && git add -A "
           "&& git commit -qm 'qa suite #5'")
LAND = "git checkout -q spec/5 && git merge -q --no-edit feat/5 && git push -q origin spec/5"
GOOD = LAND + " && git checkout -qb qa/5 && " + QA_TEST + " && git push -q origin qa/5"
QA_BEFORE_MERGE = ("git checkout -q spec/5 && git checkout -qb qa/5 && " + QA_TEST
                   + " && git push -q origin qa/5 && " + LAND)
NO_PUSH_SPEC = ("git checkout -q spec/5 && git merge -q --no-edit feat/5 && git checkout -qb qa/5 "
                "&& " + QA_TEST + " && git push -q origin qa/5")
PUSH_FEAT = GOOD + (" && git checkout -q feat/5 && echo x >> src/pricing.py && git commit -qam x "
                    "&& git push -q origin feat/5")
READ102 = {"route": "cr-comments-list", "target": "102"}
LOCK = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: processing"]}
UNLOCK = {"route": "issue-edit", "write": True, "issue": "5", "remove": ["status: processing"]}
GATE = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: ready-for-dev"]}
CREATE = {"route": "pr-create", "write": True, "pr": "104", "head": "qa/5", "draft": True}
READY = {"route": "pr-ready", "write": True, "pr": "104"}
QA_THREAD = {"route": "thread-post-inline", "write": True, "pr": "101",
             "body": "**[qa] · Q3 · Given-state**\n\nHow is an expired offer seeded?\n\n- (a) a "
                     "control point ← ✅ recommended\n- (b) direct insert\n\n*why*"}
QA_PR = {"number": 104, "title": "test: #5 black-box (QA)", "state": "OPEN", "isDraft": True,
         "headRefName": "qa/5", "baseRefName": "spec/5", "threads": [], "reviews": [],
         "comments": []}
GOOD_STEPS = ["on", "qa", "off"]
GOOD_JOURNAL = [READ102, LOCK, CREATE, UNLOCK]
# (name, should pass, shell before check, journal, steps, labels at the end, QA PR in state)
SHAPES = [
    ("B2 as written: record read, feat landed, qa off the tip, marker on→qa→off, draft CR",
     True, GOOD, GOOD_JOURNAL, GOOD_STEPS, ["track: spec"], True),
    ("B2 with a [qa] finding: in-spec-review stays, the CR stays draft", True, GOOD,
     [READ102, LOCK, QA_THREAD, CREATE, UNLOCK], GOOD_STEPS,
     ["track: spec", "status: in-spec-review"], True),
    ("qa/5 cut BEFORE the merge (the parallel shape)", False, QA_BEFORE_MERGE, GOOD_JOURNAL,
     GOOD_STEPS, ["track: spec"], True),
    ("the merge never pushed — spec/5 on the remote lacks feat/5", False, NO_PUSH_SPEC,
     GOOD_JOURNAL, GOOD_STEPS, ["track: spec"], True),
    ("a commit pushed to feat/5", False, PUSH_FEAT, GOOD_JOURNAL, GOOD_STEPS, ["track: spec"],
     True),
    ("the record never read (no cr-comments-list on #102)", False, GOOD, [LOCK, CREATE, UNLOCK],
     GOOD_STEPS, ["track: spec"], True),
    ("a gate label written by the run", False, GOOD, [READ102, LOCK, GATE, CREATE, UNLOCK],
     GOOD_STEPS, ["track: spec"], True),
    ("no QA CR opened", False, GOOD, [READ102, LOCK, UNLOCK], GOOD_STEPS, ["track: spec"], False),
    ("the QA CR readied while a [qa] thread was posted", False, GOOD,
     [READ102, LOCK, QA_THREAD, CREATE, READY, UNLOCK], GOOD_STEPS,
     ["track: spec", "status: in-spec-review"], True),
    ("the marker never written (an unguarded QA dispatch)", False, GOOD, GOOD_JOURNAL,
     ["qa", "off"], ["track: spec"], True),
    ("the marker without seat=qa", False, GOOD, GOOD_JOURNAL, ["on-noseat", "qa", "off"],
     ["track: spec"], True),
    ("the marker removed BEFORE the dispatch", False, GOOD, GOOD_JOURNAL, ["on", "off", "qa"],
     ["track: spec"], True),
    ("two QA dispatches", False, GOOD, GOOD_JOURNAL, ["on", "qa", "qa", "off"],
     ["track: spec"], True),
    ("no QA dispatch at all", False, GOOD, GOOD_JOURNAL, ["on", "off"], ["track: spec"], True),
    ("the lock left behind", False, GOOD, GOOD_JOURNAL, GOOD_STEPS,
     ["track: spec", "status: processing"], True),
]


def transcript(steps):
    ev = []
    for n, step in enumerate(steps):
        if step == "qa":
            block = {"type": "tool_use", "id": "d%d" % n, "name": "Task",
                     "input": {"subagent_type": "roz-gate:qa",
                               "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md …"
                                         " Test port: src/pricing.py"}}
        else:
            cmd = {"on": MARKER_ON, "on-noseat": MARKER_ON_NOSEAT, "off": MARKER_OFF}[step]
            block = {"type": "tool_use", "id": "b%d" % n, "name": "Bash", "input": {"command": cmd}}
        ev.append({"type": "assistant", "message": {"content": [block]}})
    ev.append({"type": "result", "result": "next-stage: #5 Path B2 — implementation landed, "
                                            "QA dispatched, draft QA CR #104."})
    return ev


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


def check(tmp, bare, journal, steps, labels, qa_pr):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    if qa_pr:
        st["prs"]["104"] = QA_PR
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(steps):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, before, journal, steps, labels, qa_pr in SHAPES:
        tmp, work, bare = sandbox()
        try:
            setup = sh(before, work)
            if setup.returncode != 0:
                print("FAIL C20 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                failed += 1
                continue
            p = check(tmp, bare, journal, steps, labels, qa_pr)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C20 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
