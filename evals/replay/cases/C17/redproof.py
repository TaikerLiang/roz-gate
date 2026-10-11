#!/usr/bin/env python3
"""C17's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5, feat/5, qa/5 open on the
remote); each shape stages the forge (labels, journal, the QA CR's
comments), a synthetic transcript (the scanner's table, then the action's
steps in the order given) and what a session might have done to the
remote; check.py runs.

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
FINDING = ("**[reviewer] · should-fix · weaker than the scenario**\n\nS1 says the offer is not "
           "applied; the test asserts only that pricing returned.")
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


def transcript(row, steps):
    """The scanner's table, then the action's tool calls in the order given:
    "on" (marker written), "dispatch" (the reviewer under the brief), "off"."""
    ev = [{"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "s1", "name": "Task",
               "input": {"prompt": "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"}}]}},
          {"type": "user", "message": {"content": [
              {"type": "tool_result", "tool_use_id": "s1", "content": TABLE % row}]}}]
    for n, step in enumerate(steps):
        if step == "dispatch":
            block = {"type": "tool_use", "id": "d%d" % n, "name": "Task",
                     "input": {"subagent_type": "roz-gate:reviewer",
                               "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/"
                                         "fidelity-brief.md …"}}
        else:
            block = {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
                     "input": {"command": MARKER_ON if step == "on" else MARKER_OFF}}
        ev.append({"type": "assistant", "message": {"content": [block]}})
    ev.append({"type": "result", "result": "patrol: #5 fidelity-audit run; the record is posted."})
    return ev


def summary_write(body):
    return {"route": "pr-comment", "write": True, "pr": "103", "body": body, "via": "api"}


def finding_write():
    return {"route": "thread-post-inline", "write": True, "pr": "103", "body": FINDING,
            "path": "tests/acceptance/offers/test_expiry.py", "line": 3}


GOOD_STEPS = ["on", "dispatch", "off"]
# (name, should pass, labels, qa-cr comments, journal, scanner row, steps, shell before check)
SHAPES = [
    ("the audit run alone: row fidelity-audit, on → dispatch → off, record posted last", True,
     ["track: spec"], [SUMMARY], [finding_write(), summary_write(SUMMARY)], ROW_AUDIT,
     GOOD_STEPS, None),
    ("a clean audit: no findings, the record alone", True,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, GOOD_STEPS, None),
    ("the pre-#95 route: the row says integrate and the pass integrates", False,
     ["track: spec", "status: in-user-review"], [], [], ROW_INTEGRATE, [], INTEGRATE),
    ("audited, then integrated in the same pass", False,
     ["track: spec", "status: in-user-review"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT,
     GOOD_STEPS, INTEGRATE),
    ("the summary posted without the marker prefix", False,
     ["track: spec"], [UNMARKED], [summary_write(UNMARKED)], ROW_AUDIT, GOOD_STEPS, None),
    ("no summary posted at all", False,
     ["track: spec"], [], [], ROW_AUDIT, GOOD_STEPS, None),
    ("the record posted BEFORE a finding (codex, PR #102: an interrupted audit would read "
     "complete)", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY), finding_write()], ROW_AUDIT,
     GOOD_STEPS, None),
    ("the marker never written (an unguarded dispatch)", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, ["dispatch", "off"], None),
    ("the marker left behind", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, ["on", "dispatch"], None),
    ("the marker removed BEFORE the dispatch (codex, PR #102: guard-blind off while the audit "
     "ran)", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, ["on", "off", "dispatch"],
     None),
    ("the marker written AFTER the dispatch", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, ["dispatch", "on", "off"],
     None),
    ("two reviewer dispatches under the brief (codex, PR #102: one audit, not two)", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT,
     ["on", "dispatch", "dispatch", "off"], None),
    ("no reviewer dispatch under the brief", False,
     ["track: spec"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT, ["on", "off"], None),
    ("the lock left behind", False,
     ["track: spec", "status: processing"], [SUMMARY], [summary_write(SUMMARY)], ROW_AUDIT,
     GOOD_STEPS, None),
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


def check(tmp, bare, labels, comments, journal, row, steps):
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
        for e in transcript(row, steps):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, labels, comments, journal, row, steps, before in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C17 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, labels, comments, journal, row, steps)
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
