#!/usr/bin/env python3
"""F9's red-proof: check.py scores staged runs correctly. No model — each
shape is a synthetic transcript (a scanner dispatch, its table, the main
agent's later calls) plus a forge state and journal, over the seeded sandbox.

    python3 evals/replay/cases/F9/redproof.py

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
GOOD_TABLE = "\n".join([
    "| issue | track | status | holder | cr | unheard | verdict | evidence |",
    "|---|---|---|---|---|---|---|---|",
    "| #5 Offer expiry enforcement | spec | in-user-review | paul | 101 open "
    "| 1 (…/pull/101#issuecomment-800) | actionable: review-answers "
    "| latest top-level comment is the human's |",
    "| #6 Bump the HTTP client to 3.2 | fast | ready-for-dev | paul | none | 0 "
    "| actionable: next-stage (ready-for-dev) | gate label worn |",
    "| #7 Gift cards | — | — | paul | none | 0 | intake: questions | no **[intake]** batch yet |",
    "inbox filter: none · 0 track-less issues not in the inbox filter"])
BAD_TABLE = GOOD_TABLE.replace("actionable: review-answers", "waiting on user: your answer")


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


def tool_use(name, inp, uid, parent=None):
    ev = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": name, "input": inp}]}}
    if parent:
        ev["parent_tool_use_id"] = parent
    return ev


def tool_result(uid, text, parent=None):
    ev = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "content": text}]}}
    if parent:
        ev["parent_tool_use_id"] = parent
    return ev


def transcript(table, scanner_write=False, relist=False, scanner=True, scanner_mutation=False,
               background=False):
    ev = []
    if scanner:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        ev.append(tool_use("Bash", {"command": "gh issue list --state open "
                                               "--json number,title,labels,assignees,createdAt"},
                           "t_s1", parent="t_scan"))
        ev.append(tool_result("t_s1", "[]", parent="t_scan"))
        # THREADS-LIST is a read with a -f field — the scanner's bread and butter.
        ev.append(tool_use("Bash", {"command": "gh api graphql -f query='query($pr:Int!){ "
                                               "repository{ pullRequest(number:$pr){ reviewThreads"
                                               "{ nodes{ id isResolved path line } } } } }' "
                                               "-F pr=101"},
                           "t_s3", parent="t_scan"))
        ev.append(tool_result("t_s3", "{}", parent="t_scan"))
        if scanner_write:
            ev.append(tool_use("Bash",
                               {"command": 'gh issue edit 6 --add-label "status: processing"'},
                               "t_s2", parent="t_scan"))
            ev.append(tool_result("t_s2", "", parent="t_scan"))
        if scanner_mutation:
            ev.append(tool_use("Bash", {"command": "gh api graphql -f query='mutation { "
                                                   "resolveReviewThread(input:{threadId:\"T1\"}) "
                                                   "{ thread { isResolved } } }'"},
                               "t_s4", parent="t_scan"))
            ev.append(tool_result("t_s4", "{}", parent="t_scan"))
        if background:
            # the launch notice in the tool_result, the table in a later notification
            ev.append(tool_result("t_scan", "Async agent launched successfully. agentId: a1"))
            ev.append({"type": "system", "subtype": "task_notification", "task_id": "a1",
                       "tool_use_id": "t_scan", "status": "completed", "summary": table})
        else:
            ev.append(tool_result("t_scan", table))
    if relist:
        ev.append(tool_use("Bash", {"command": "gh issue list --state open --json number,labels"},
                           "t_m0"))
        ev.append(tool_result("t_m0", "[]"))
    # review-answers finds its own CR — one issue's CR-FIND, allowed after the table.
    ev.append(tool_use("Bash", {"command": "gh pr list --head spec/5 --state all "
                                           "--json number,state,url"}, "t_m_cr"))
    ev.append(tool_result("t_m_cr", "[]"))
    ev.append(tool_use("Bash", {"command": 'gh issue edit 5 --add-label "status: processing"'},
                       "t_m1"))
    ev.append(tool_result("t_m1", ""))
    ev.append(tool_use("Task", {"prompt": "intake brief … actors, scenarios … impl tests",
                                "subagent_type": "roz-gate:product"}, "t_p"))
    ev.append(tool_result("t_p", "**[intake]** 1. …"))
    ev.append({"type": "result", "result": "done"})
    return ev


def run_check(tmp, bare, table, *, scanner_write=False, relist=False, scanner=True,
              lock6=False, intake7=True, scanner_mutation=False, block6=False,
              background=False):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"].append("status: processing")
    if lock6:
        st["issues"]["6"]["labels"].append("status: processing")
    if block6:
        st["issues"]["6"]["labels"] = ["track: fast", "status: blocked"]
        st["issues"]["6"]["comments"] = [{"id": 2, "author": "paul",
                                          "body": "**[patrol] · blocked** — nothing to bump."}]
    if intake7:
        st["issues"]["7"]["comments"] = [{"id": 1, "author": "paul",
                                          "body": "**[intake]** 1. Expiry? (a) …"}]
    journal = [{"route": "issue-edit", "write": True, "issue": "5",
                "add": ["status: processing"]}]
    if intake7:
        journal.append({"route": "issue-comment", "write": True, "issue": "7",
                        "body": "**[intake]** 1. …"})
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(table, scanner_write, relist, scanner, scanner_mutation, background):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


SHAPES = [
    ("the good pass: table, act on #5, #6 untouched, #7 asked", True, {}),
    ("the good pass, scanner dispatched in the background", True, {"background": True}),
    ("a row with the wrong verdict (#5 waiting on user)", False, {"table": BAD_TABLE}),
    ("the good pass, #7 unassigned — holder is its author", True,
     {"table": GOOD_TABLE.replace("| #7 Gift cards | — | — | paul |",
                                  "| #7 Gift cards | — | — | paul (author; unassigned) |")}),
    ("the scanner wrote a label", False, {"scanner_write": True}),
    ("the scanner sent a graphql mutation", False, {"scanner_mutation": True}),
    ("the main agent re-listed issues after the table", False, {"relist": True}),
    ("no scanner at all (the old in-context scan)", False, {"scanner": False}),
    ("#6 locked too (one-issue rule broken)", False, {"lock6": True}),
    ("#6 acted on and STOPped to blocked (one-issue rule broken)", False, {"block6": True}),
    ("#7 never asked", False, {"intake7": False}),
]


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            table = kw.pop("table", GOOD_TABLE)
            p = run_check(tmp, bare, table, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F9 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
