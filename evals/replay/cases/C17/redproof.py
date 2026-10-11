#!/usr/bin/env python3
"""C17's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5, feat/5, qa/5 open on the
remote); each shape stages the forge (labels, journal, the QA CR's
comments), a synthetic transcript (the scanner's table, the marker writes,
the dispatch) and what a session might have done to the remote; check.py
runs.

    python3 evals/replay/cases/C17/redproof.py

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
MARK = "**[reviewer] · fidelity**"
SUMMARY = MARK + " — 1/1 faithful. S1's test asserts the exclusion the scenario states."
UNMARKED = "Fidelity: 1/1 faithful. S1's test asserts the exclusion the scenario states."
ROW_AUDIT = ("| #5 | spec | — | paul | #102 open, #103 open | 0 | actionable: fidelity-audit "
             "| QA CR #103 has no `**[reviewer] · fidelity**` comment |")
ROW_INTEGRATE = ("| #5 | spec | — | paul | #102 open, #103 open | 0 | actionable: integrate "
                 "| both thread-clean, #103 ready |")
TABLE = ("| issue | track | status | holder | cr | unheard | verdict | evidence |\n"
         "|---|---|---|---|---|---|---|---|\n%s\ninbox filter: none")
GITDIR = "$(git rev-parse --git-common-dir)/roz-gate"
MARKER_ON = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\n\' > "%s/fidelity-dispatch"'
             % (GITDIR, GITDIR))
MARKER_OFF = 'rm -f "%s/fidelity-dispatch"' % GITDIR
INTEGRATE = ("git checkout -q spec/5 && git merge -q --no-edit feat/5 "
             "&& git merge -q --no-edit qa/5 && git push -q origin spec/5")


def transcript(row, marker_on, dispatch, marker_off):
    ev = [{"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "s1", "name": "Task",
               "input": {"prompt": "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"}}]}},
          {"type": "user", "message": {"content": [
              {"type": "tool_result", "tool_use_id": "s1", "content": TABLE % row}]}}]
    n = 1
    if marker_on:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
             "input": {"command": MARKER_ON}}]}})
        n += 1
    if dispatch:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "d1", "name": "Task",
             "input": {"subagent_type": "roz-gate:reviewer",
                       "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/"
                                 "fidelity-brief.md …"}}]}})
    if marker_off:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
             "input": {"command": MARKER_OFF}}]}})
    ev.append({"type": "result", "result": "patrol: #5 fidelity-audit run; the record is posted."})
    return ev


def comment_write(body):
    return {"route": "pr-comment", "write": True, "pr": "103", "body": body, "via": "api"}


# (name, should pass, labels, qa-cr comments, journal, scanner row, marker on, dispatch,
#  marker off, shell before check)
SHAPES = [
    ("the audit run alone: row fidelity-audit, marker on/off, reviewer dispatched, record "
     "posted", True, ["track: spec"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT,
     True, True, True, None),
    ("the pre-#95 route: the row says integrate and the pass integrates", False,
     ["track: spec", "status: in-user-review"], [], [], ROW_INTEGRATE, False, False, False,
     INTEGRATE),
    ("audited, then integrated in the same pass", False,
     ["track: spec", "status: in-user-review"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT,
     True, True, True, INTEGRATE),
    ("the summary posted without the marker prefix", False,
     ["track: spec"], [UNMARKED], [comment_write(UNMARKED)], ROW_AUDIT, True, True, True, None),
    ("no summary posted at all", False,
     ["track: spec"], [], [], ROW_AUDIT, True, True, True, None),
    ("the marker never written (an unguarded dispatch)", False,
     ["track: spec"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT, False, True, True, None),
    ("the marker left behind", False,
     ["track: spec"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT, True, True, False, None),
    ("no reviewer dispatch under the brief", False,
     ["track: spec"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT, True, False, True, None),
    ("the lock left behind", False,
     ["track: spec", "status: processing"], [SUMMARY], [comment_write(SUMMARY)], ROW_AUDIT,
     True, True, True, None),
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


def check(tmp, bare, labels, comments, journal, row, marker_on, dispatch, marker_off):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["prs"]["103"]["comments"] = [{"id": 801 + i, "author": "paul", "body": b,
                                     "created_at": "2026-08-24T12:00:00Z"}
                                    for i, b in enumerate(comments)]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(row, marker_on, dispatch, marker_off):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for (name, want_pass, labels, comments, journal, row, marker_on, dispatch, marker_off,
         before) in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C17 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, journal, row, marker_on, dispatch, marker_off)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C17 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
