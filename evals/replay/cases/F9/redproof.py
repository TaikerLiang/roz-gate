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


LOCAL_COMMIT_5 = ("cd .git/roz-gate/wt/spec/5 && git add -A "
                  "&& git commit -qm 'spec: fold the checkout-time answer'")
BLOCK_6 = ('gh issue edit 6 --remove-label "status: ready-for-dev" '
           '--add-label "status: blocked"')
LOCAL_COMMIT_6 = "cd .git/roz-gate/wt/fast/6 && git commit -qam 'bump the HTTP client'"
RAW_HEADS = ("0123456789abcdef0123456789abcdef01234567\trefs/heads/main\n"
             "89abcdef0123456789abcdef0123456789abcdef\trefs/heads/spec/5\n")


def transcript(table, scanner_write=False, relist=False, scanner=True, scanner_mutation=False,
               background=False, handoff="snapshot", dispatch5=False, bash_after5=(),
               error_after5=False):
    """handoff: "snapshot" — the agent ran `bin/roz-branch snapshot` and the
    scanner's prompt names the file (#135); "raw" — the pre-#135 handoff,
    `git ls-remote` output pasted into the prompt; "none" — neither.
    dispatch5: the #5 review-answers turn dispatched a seat, so it counts
    toward the N (patrol.md §3). bash_after5: the main agent's commands
    after the #5 lock, in order."""
    ev = []
    if handoff == "snapshot":
        ev.append(tool_use("Bash", {"command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-branch "
                                               "snapshot --json > /tmp/roz-snapshot.json"},
                           "t_snap"))
        ev.append(tool_result("t_snap", ""))
    elif handoff == "raw":
        ev.append(tool_use("Bash", {"command": "git ls-remote --heads origin"}, "t_raw"))
        ev.append(tool_result("t_raw", RAW_HEADS))
    if scanner:
        prompt = "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…"
        if handoff == "snapshot":
            prompt += " The remote snapshot: /tmp/roz-snapshot.json — bind every branch with " \
                      "`bin/roz-branch match --snapshot /tmp/roz-snapshot.json --issues …`."
        elif handoff == "raw":
            prompt += " The remote's heads:\n" + RAW_HEADS
        ev.append(tool_use("Task", {"prompt": prompt, "subagent_type": "general-purpose"},
                           "t_scan"))
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
    if dispatch5:
        ev.append(tool_use("Task", {"prompt": dispatch5 if isinstance(dispatch5, str) else
                                    "review-answers on #5: the user's comment on PR "
                                    "101 needs a spec fold on spec/5 …",
                                    "subagent_type": "roz-gate:product"}, "t_seat5"))
        ev.append(tool_result("t_seat5", "folded"))
    for i, cmd in enumerate(bash_after5):
        ev.append(tool_use("Bash", {"command": cmd}, "t_a5_%d" % i))
        res = tool_result("t_a5_%d" % i, "fatal: 'nowhere' does not appear to be a git "
                          "repository" if error_after5 else "")
        if error_after5:
            res["message"]["content"][0]["is_error"] = True
        ev.append(res)
    ev.append(tool_use("Task", {"prompt": "intake brief … actors, scenarios … impl tests",
                                "subagent_type": "roz-gate:product"}, "t_p"))
    ev.append(tool_result("t_p", "**[intake]** 1. …"))
    ev.append({"type": "result", "result": "done"})
    return ev


def run_check(tmp, bare, table, *, scanner_write=False, relist=False, scanner=True,
              lock6=False, intake7=True, scanner_mutation=False, block6=False,
              background=False, handoff="snapshot", dispatch5=False, bash_after5=(),
              error_after5=False):
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
        for e in transcript(table, scanner_write, relist, scanner, scanner_mutation, background,
                            handoff, dispatch5, bash_after5, error_after5):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


SHAPES = [
    ("the good pass: table, act on #5, #6 untouched, #7 asked", True, {}),
    ("the good pass, scanner dispatched in the background", True, {"background": True}),
    ("raw ls-remote output pasted into the scanner's prompt (pre-#135 handoff)", False,
     {"handoff": "raw"}),
    ("no snapshot taken, nothing handed over", False, {"handoff": "none"}),
    ("a row with the wrong verdict (#5 waiting on user)", False, {"table": BAD_TABLE}),
    ("the good pass, #7 unassigned — holder is its author", True,
     {"table": GOOD_TABLE.replace("| #7 Gift cards | — | — | paul |",
                                  "| #7 Gift cards | — | — | paul (author; unassigned) |")}),
    ("the scanner wrote a label", False, {"scanner_write": True}),
    ("the scanner sent a graphql mutation", False, {"scanner_mutation": True}),
    ("the main agent re-listed issues after the table", False, {"relist": True}),
    ("no scanner at all (the old in-context scan)", False, {"scanner": False}),
    # #330 ruling 3: the #5 turn counts toward the N only when it dispatched a
    # seat or committed; then #6 must stay as seeded. An answer-only turn is
    # outside the N, and acting on #6 is the one slot (F9/run-3).
    ("#5 dispatched a seat, #6 locked too (one-issue rule broken)", False,
     {"lock6": True, "dispatch5": True}),
    ("#5 dispatched a seat, #6 acted on and STOPped (one-issue rule broken)", False,
     {"block6": True, "dispatch5": True}),
    ("#5 committed on spec/5, #6 acted on and STOPped (one-issue rule broken)", False,
     {"block6": True, "commit5": True}),
    ("#5 committed locally, never pushed, #6 acted on and STOPped (codex, PR #340)", False,
     {"block6": True, "bash_after5": [LOCAL_COMMIT_5]}),
    ("#5's commit and #6's STOP in one Bash call (codex, PR #340)", False,
     {"block6": True, "bash_after5": [LOCAL_COMMIT_5 + " && " + BLOCK_6]}),
    ("#5 committed, then its push errored, #6 STOPped (codex, PR #340)", False,
     {"block6": True, "bash_after5": [LOCAL_COMMIT_5 + " && git push -q nowhere spec/5"],
      "error_after5": True}),
    ("#5 ran only a commit --dry-run, #6 acted on and STOPped (codex, PR #340)", True,
     {"block6": True, "bash_after5": [LOCAL_COMMIT_5 + " --dry-run"]}),
    ("#5 only answered, then #6's own commit, #6 STOPped (the commit is #6's)", True,
     {"block6": True, "bash_after5": [BLOCK_6, LOCAL_COMMIT_6]}),
    ("#5's seat names spec/5 only at a line start, #6 STOPped (codex, PR #340)", False,
     {"block6": True, "dispatch5": "Fold the user's answer.\nspec/5 is the branch to work on."}),
    ("#5 dispatched a seat, #6 untouched", True, {"dispatch5": True}),
    ("#5 committed on spec/5, #6 untouched", True, {"commit5": True}),
    ("#5 only answered, #6 acted on and STOPped (#330: outside the N, F9/run-3)", True,
     {"block6": True}),
    ("#5 only answered, #6 locked (#330: outside the N)", True, {"lock6": True}),
    ("#7 never asked", False, {"intake7": False}),
]


def committed_sandbox():
    """The sandbox after the #5 turn committed: spec/5 one commit further."""
    tmp, work, bare = sandbox()
    p = sh("git checkout -q spec/5 && echo '- S2 — folded.' >> docs/specs/5/spec.md "
           "&& git commit -qam 'spec: fold' && git push -q origin spec/5", work)
    if p.returncode != 0:
        raise RuntimeError("commit step failed:\n%s" % p.stderr)
    return tmp, work, bare


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    tmp_c, _, bare_c = committed_sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            table = kw.pop("table", GOOD_TABLE)
            if kw.pop("commit5", False):
                p = run_check(tmp_c, bare_c, table, **kw)
            else:
                p = run_check(tmp, bare, table, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F9 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(tmp_c, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
