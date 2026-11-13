#!/usr/bin/env python3
"""C26's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal (the locks, the CRs opened), the fast
branches the pass pushed, a transcript (the scanner dispatch, the
final report) and the sandbox's bare remote, seeded by the case's own
seed.sh.

    python3 evals/replay/cases/C26/redproof.py

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

R5 = "| #5 Offer expiry enforcement | spec · in-user-review | waits on you: your review | yes |"
R6 = "| #6 Bump the HTTP client to 3.2 | fast · ready-for-dev " \
     "| acted: next-stage — fast CR opened | — |"
R7 = "| #7 Gift cards | inbox | acted: intake — 3 questions posted | yes |"
R8 = "| #8 Add a request-id header to every response | fast · ready-for-dev " \
     "| acted: next-stage — fast CR opened | — |"
R9 = "| #9 Retire the legacy /v0/ping route | fast · ready-for-dev " \
     "| queued: next-stage · ready-for-dev 75d | — |"
TABLE = ["| issue | state | this pass | needs you |", "|---|---|---|---|", R5, R6, R7, R8, R9]
FILTER = "inbox filter: discuss / none · 0 track-less issues not in the inbox filter"
QUEUE = ["Your queue:",
         "- #5 — review & merge — https://github.com/acme/demo/pull/101",
         "- #7 — answer the intake questions — https://github.com/acme/demo/issues/7"]
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "label-events", "write": False, "issue": "6", "explicit": True},
         {"route": "label-events", "write": False, "issue": "8", "explicit": True},
         {"route": "label-events", "write": False, "issue": "9", "explicit": True},
         {"route": "pr-list", "write": False, "state": "all"}]


def lock(n):
    return {"route": "issue-edit", "write": True, "issue": n, "add": ["status: processing"],
            "remove": [], "body_edit": False}


INTAKE7 = {"route": "issue-comment", "write": True, "issue": "7",
           "body": "**[intake]** 1. Expiry? (a) …"}
COMMENT9 = {"route": "issue-comment", "write": True, "issue": "9",
            "body": "**[patrol] · note** — looking at this next."}


def cr(n):
    return {"route": "pr-create", "write": True, "head": "fast/%s" % n, "base": "main",
            "title": "fast: #%s" % n}


GOOD = READS + [lock("6"), cr("6"), lock("8"), cr("8"), INTAKE7]


def report(table=TABLE, filt=FILTER, queue=QUEUE):
    return "Patrol pass report\n\n" + "\n".join(list(table) + [filt, ""] + list(queue)) + "\n"


def swap(rows, old, new):
    out = [ln.replace(old, new) for ln in rows]
    assert out != list(rows), old
    return out


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


# The alternative good pass: the tie among equals broke the other way.
TABLE_69 = [
    TABLE[0], TABLE[1], R5, R6, R7,
    "| #8 Add a request-id header to every response | fast · ready-for-dev "
    "| queued: next-stage · ready-for-dev 75d | — |",
    "| #9 Retire the legacy /v0/ping route | fast · ready-for-dev "
    "| acted: next-stage — fast CR opened | — |"]

SHAPES = [
    ("the good pass: #6 and #8 locked, #9 as seeded with its wait, #7 asked", True, {}),
    ("the good pass the other way: #6 and #9 locked, #8 queued with its wait", True,
     {"journal": READS + [lock("6"), cr("6"), lock("9"), cr("9"), INTAKE7],
      "locked": ("6", "9"), "started": ("6", "9"), "text": report(table=TABLE_69)}),
    # #293 — intake locks #7 while it asks; that is not next-stage starting.
    ("the good pass, #7 locked for its intake batch", True,
     {"journal": GOOD + [lock("7")], "locked": ("6", "8", "7")}),
    ("#6 and #8 locked and nothing started — a lock is not an action", False,
     {"journal": READS + [lock("6"), lock("8"), INTAKE7], "started": ()}),
    ("next-stage started on #7 — a fast branch for an inbox idea", False,
     {"push_branch": "fast/7"}),
    ("three started — N ignored", False,
     {"journal": GOOD + [lock("9"), cr("9")], "locked": ("6", "8", "9"),
      "started": ("6", "8", "9"),
      "text": report(table=swap(TABLE, "queued: next-stage · ready-for-dev 75d",
                                "acted: next-stage — fast CR opened"))}),
    ("one started — N=2 with two more actionable", False,
     {"journal": READS + [lock("6"), cr("6"), INTAKE7], "locked": ("6",), "started": ("6",),
      "text": report(table=swap(TABLE, R8, "| #8 Add a request-id header to every response "
                                           "| fast · ready-for-dev "
                                           "| queued: next-stage · ready-for-dev 75d | — |"))}),
    ("#9's row without its wait", False,
     {"text": report(table=swap(TABLE, "queued: next-stage · ready-for-dev 75d",
                                "queued: next-stage"))}),
    ("#9's row with a wait but no gate label", False,
     {"text": report(table=swap(TABLE, "queued: next-stage · ready-for-dev 75d",
                                "queued: next-stage · 75d"))}),
    ("#9 queued but needs you: yes", False,
     {"text": report(table=swap(TABLE, "| queued: next-stage · ready-for-dev 75d | — |",
                                "| queued: next-stage · ready-for-dev 75d | yes |"))}),
    ("#9 commented on — touched without a lock", False,
     {"journal": GOOD + [COMMENT9], "comments9": 1}),
    ("#9's fast branch on the remote — a third issue started", False, {"push_branch": "fast/9"}),
    ("#6 locked twice", False, {"journal": GOOD + [lock("6")]}),
    ("#5 locked — a wait-on-you row acted on", False,
     {"journal": GOOD + [lock("5")], "locked": ("5", "6", "8")}),
    ("#7 never asked", False,
     {"journal": [e for e in GOOD if e is not INTAKE7], "intake7": False}),
    ("no scanner dispatched", False, {"dispatch": False}),
    ("the report has no table", False,
     {"text": "Patrol pass report\n\n#6 and #8 started; #9 next time.\n"}),
]


def run_check(tmp, bare, *, text=None, journal=None, locked=("6", "8"), started=("6", "8"),
              intake7=True, comments9=None, push_branch=None, dispatch=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    for n in locked:
        st["issues"][n]["labels"].append("status: processing")
    if intake7:
        st["issues"]["7"]["comments"] = [{"id": 1, "author": "paul",
                                          "body": "**[intake]** 1. Expiry? (a) …"}]
    if comments9:
        st["issues"]["9"]["comments"] = [{"id": 2, "author": "paul",
                                          "body": COMMENT9["body"]}] * comments9
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (GOOD if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(report() if text is None else text, dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    work = os.path.join(tmp, "work")
    pushed = ["fast/%s" % n for n in started] + ([push_branch] if push_branch else [])
    for b in pushed:
        p = sh("git checkout -qb %s && git commit -q --allow-empty -m x && "
               "git push -q origin %s && git checkout -q main" % (b, b), work)
        if p.returncode != 0:
            raise RuntimeError("push shape failed: %s" % p.stderr)
    try:
        env = dict(os.environ, RUN_DIR=run, BARE=bare)
        return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                              capture_output=True, text=True)
    finally:
        for b in pushed:
            sh("git push -q origin --delete %s && git branch -q -D %s" % (b, b), work)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, bare, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s C26 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
