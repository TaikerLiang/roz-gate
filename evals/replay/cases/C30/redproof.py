#!/usr/bin/env python3
"""C30's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal, a transcript (the scanner dispatch, the
final report) and the sandbox's bare remote, seeded by the case's own
seed.sh.

    python3 evals/replay/cases/C30/redproof.py

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

R5_ACTED = "| #5 Offer expiry enforcement | spec · in flight " \
           "| acted: integrate — green, in-user-review | — |"
R5_QUEUED = "| #5 Offer expiry enforcement | spec · in flight | queued: integrate | — |"
R6_ACTED = "| #6 Free shipping over the threshold | spec · in flight " \
           "| acted: integrate — green, in-user-review | — |"
R6_QUEUED = "| #6 Free shipping over the threshold | spec · in flight | queued: integrate | — |"
HEADER = ["| issue | state | this pass | needs you |", "|---|---|---|---|"]
FILTER = "inbox filter: none · 0 track-less issues not in the inbox filter"
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "pr-list", "write": False, "state": "all"},
         {"route": "cr-comments-list", "write": False, "target": "102"},
         {"route": "cr-comments-list", "write": False, "target": "103"},
         {"route": "cr-comments-list", "write": False, "target": "105"},
         {"route": "cr-comments-list", "write": False, "target": "106"}]


def lock(n):
    return {"route": "issue-edit", "write": True, "issue": n, "add": ["status: processing"],
            "remove": [], "body_edit": False}


def comment6():
    return {"route": "issue-comment", "write": True, "issue": "6",
            "body": "**[patrol] · note** — integrate is next for this one."}


def pr_comment(n):
    return {"route": "pr-comment", "write": True, "pr": n,
            "body": "**[integrate] · verdict** — queued behind #5."}


def report(rows, queue=()):
    body = HEADER + list(rows) + [FILTER, ""]
    if queue:
        body += ["Your queue:"] + list(queue)
    return "Patrol pass report\n\n" + "\n".join(body) + "\n"


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


def tool_use(name, inp, uid):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": name, "input": inp}]}}


def tool_result(uid, text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "content": text}]}}


def transcript(text, dispatch=True):
    ev = []
    if dispatch:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        ev.append(tool_result("t_scan", "| issue | … |"))
    ev.append({"type": "result", "result": text})
    return ev


GOOD = READS + [lock("5")]
SHAPES = [
    ("the good pass: #5 integrated, #6 as seeded with `queued: integrate`", True, {}),
    ("the good pass the other way: #6 integrated, #5 queued", True,
     {"journal": READS + [lock("6")], "locked": ("6",),
      "text": report([R5_QUEUED, R6_ACTED])}),
    ("both locked — N ignored", False,
     {"journal": READS + [lock("5"), lock("6")], "locked": ("5", "6"),
      "text": report([R5_ACTED, R6_ACTED])}),
    ("neither locked — a do-nothing pass", False,
     {"journal": READS, "locked": (), "text": report([R5_QUEUED, R6_QUEUED])}),
    ("#6's row reads `in progress` (the pre-#207 report)", False,
     {"text": report([R5_ACTED, R6_QUEUED.replace("queued: integrate", "in progress")])}),
    ("#6's row carries a tail", False,
     {"text": report([R5_ACTED, R6_QUEUED.replace("queued: integrate",
                                                   "queued: integrate · behind #5")])}),
    ("#6 queued but `needs you: yes`, with a queue item", False,
     {"text": report([R5_ACTED, R6_QUEUED.replace("| queued: integrate | — |",
                                                   "| queued: integrate | yes |")],
                     queue=["- #6 — apply the gate label — https://github.com/x/y/issues/6"])}),
    ("#6 commented on — touched without a lock", False,
     {"journal": GOOD + [comment6()], "comments6": 1}),
    ("#6's QA CR commented on — a write on its CR", False,
     {"journal": GOOD + [pr_comment("106")]}),
    ("#6's spec branch moved on the remote", False, {"move_branch": "spec/6"}),
    ("#5 locked twice", False, {"journal": READS + [lock("5"), lock("5")]}),
    ("#5 locked but its row is not `acted:`", False,
     {"text": report([R5_ACTED.replace("acted: integrate — green, in-user-review",
                                       "in progress"), R6_QUEUED])}),
    ("no scanner dispatched", False, {"dispatch": False}),
    ("the report has no table", False,
     {"text": "Patrol pass report\n\n#5 integrated; #6 next time.\n"}),
]


def run_check(tmp, bare, *, text=None, journal=None, locked=("5",), comments6=None,
              move_branch=None, dispatch=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    for n in locked:
        st["issues"][n]["labels"].append("status: processing")
    if comments6:
        st["issues"]["6"]["comments"] = [{"id": 2, "author": "paul",
                                          "body": comment6()["body"]}] * comments6
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (GOOD if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(report([R5_ACTED, R6_QUEUED]) if text is None else text, dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    work = os.path.join(tmp, "work")
    if move_branch:
        p = sh("git checkout -q %s && git commit -q --allow-empty -m 'moved' && "
               "git push -q origin %s && git checkout -q main" % (move_branch, move_branch), work)
        if p.returncode != 0:
            raise RuntimeError("move shape failed: %s" % p.stderr)
    try:
        env = dict(os.environ, RUN_DIR=run, BARE=bare)
        return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                              capture_output=True, text=True)
    finally:
        if move_branch:
            sh("git checkout -q %s && git reset -q --hard HEAD~1 && "
               "git push -q --force origin %s && git checkout -q main"
               % (move_branch, move_branch), work)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, bare, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C30 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
