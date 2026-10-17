#!/usr/bin/env python3
"""C23's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (feat/5 open, zero threads, no record, no
qa/5); each shape stages the forge (labels, journal), a synthetic transcript
(the scanner's table, the reviewer dispatch) and what a pass might have done
to the remote; check.py runs.

    python3 evals/replay/cases/C23/redproof.py

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
MARK = "**[reviewer] · code-review**"
ROW_REVIEW = ("| #5 | spec | — | paul | #102 open | 0 | actionable: code-review "
              "| #102 has zero threads and no `**[reviewer] · code-review**` record |")
ROW_QA = ("| #5 | spec | — | paul | #102 open | 0 | actionable: next-stage (qa) "
          "| #102 review-clean (zero threads) |")
TABLE = ("| issue | track | status | holder | cr | unheard | verdict | evidence |\n"
         "|---|---|---|---|---|---|---|---|\n%s\ninbox filter: none")
FINDING = ("**[reviewer] · nit · naming**\n\n`total` shadows nothing but reads as a running sum "
           "of costs before discounts; `net` would say what it holds.")
LAND = "git checkout -q spec/5 && git merge -q --no-edit feat/5 && git push -q origin spec/5"
CUT_QA = ("git checkout -q spec/5 && git checkout -qb qa/5 && mkdir -p tests/acceptance && touch "
          "tests/acceptance/t.py && git add -A && git commit -qm qa && git push -q origin qa/5")


def record(sha):
    return {"route": "pr-comment", "write": True, "pr": "102",
            "body": "%s — blocking 0 · should-fix 0 · nit 1 · question 0\nreviewed-sha: %s"
                    % (MARK, sha)}


def finding():
    return {"route": "thread-post-inline", "write": True, "pr": "102", "body": FINDING,
            "path": "src/pricing.py", "line": 3}


def dispatch(n, docs=True):
    prompt = "Review the diff of #102 against spec/5." + (
        " Attached: docs/specs/5/spec.md and docs/specs/5/technical-spec.md; the CR's "
        "## Contract deviations." if docs else "")
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "d%d" % n, "name": "Task",
         "input": {"subagent_type": "roz-gate:reviewer", "prompt": prompt}}]}}


def transcript(row, dispatches=1, docs=True):
    ev = [{"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "s1", "name": "Task",
               "input": {"prompt": "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"}}]}},
          {"type": "user", "message": {"content": [
              {"type": "tool_result", "tool_use_id": "s1", "content": TABLE % row}]}}]
    for n in range(dispatches):
        ev.append(dispatch(n, docs))
    ev.append({"type": "result", "result": "patrol: #5 code-review run; the record is posted."})
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


def check(tmp, bare, labels, journal, row, dispatches, docs):
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
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(row, dispatches, docs):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        head = sh("git rev-parse feat/5", work).stdout.strip()
        other = sh("git rev-parse spec/5", work).stdout.strip()
        # (name, should pass, labels, journal, row, dispatches, docs attached, shell before)
        shapes = [
            ("the review run alone: row code-review, one dispatch with the docs, finding then "
             "record with the head", True, ["track: spec"], [finding(), record(head)],
             ROW_REVIEW, 1, True, None),
            ("a clean review: no findings, the record alone (zero findings is still a record)",
             True, ["track: spec"], [record(head)], ROW_REVIEW, 1, True, None),
            ("the record with a short sha of the head", True, ["track: spec"],
             [record(head[:12])], ROW_REVIEW, 1, True, None),
            ("the pre-#140 reading: zero threads = review-clean, the row says next-stage (qa)",
             False, ["track: spec"], [record(head)], ROW_QA, 1, True, None),
            ("no record posted", False, ["track: spec"], [finding()], ROW_REVIEW, 1, True, None),
            ("the record carries no reviewed-sha", False, ["track: spec"],
             [{"route": "pr-comment", "write": True, "pr": "102",
               "body": MARK + " — nit 1"}], ROW_REVIEW, 1, True, None),
            ("the record's sha is not the head (stale on arrival)", False, ["track: spec"],
             [record(other)], ROW_REVIEW, 1, True, None),
            ("the record posted BEFORE a finding", False, ["track: spec"],
             [record(head), finding()], ROW_REVIEW, 1, True, None),
            ("two reviewer dispatches", False, ["track: spec"], [record(head)], ROW_REVIEW, 2,
             True, None),
            ("no reviewer dispatch", False, ["track: spec"], [record(head)], ROW_REVIEW, 0,
             True, None),
            ("the reviewer dispatched without the spec docs (D1)", False, ["track: spec"],
             [record(head)], ROW_REVIEW, 1, False, None),
            ("the lock left behind", False, ["track: spec", "status: processing"],
             [record(head)], ROW_REVIEW, 1, True, None),
            ("reviewed, then landed on spec/5 in the same pass", False, ["track: spec"],
             [record(head)], ROW_REVIEW, 1, True, LAND),
            ("reviewed, then qa/5 cut in the same pass", False, ["track: spec"],
             [record(head)], ROW_REVIEW, 1, True, CUT_QA),
        ]
        # the two shapes that move the remote come last — one sandbox serves them all
        for name, want_pass, labels, journal, row, n, docs, before in shapes:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    raise RuntimeError("shape setup failed: %s\n%s" % (before, setup.stderr))
            p = check(tmp, bare, labels, journal, row, n, docs)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C23 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
