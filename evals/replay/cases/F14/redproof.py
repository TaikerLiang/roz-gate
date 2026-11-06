#!/usr/bin/env python3
"""F14's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal, a transcript (the scanner dispatch, the
final report) and the sandbox's bare remote, seeded by the case's own
seed.sh.

    python3 evals/replay/cases/F14/redproof.py

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

TABLE = [
    "| issue | state | this pass | needs you |",
    "|---|---|---|---|",
    "| #5 Offer expiry enforcement | spec · ready-for-dev "
    "| illegal: ready-for-dev on a passed stage (feat/5 merged) | yes |",
]
FILTER = "inbox filter: none · 0 track-less issues not in the inbox filter"
QUEUE = [
    "Your queue:",
    "- #5 — remove `status: ready-for-dev` (the stage it gates has passed); patrol resumes "
    "from the CRs — https://github.com/x/y/issues/5",
]
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "label-events", "write": False, "issue": "5", "explicit": True},
         {"route": "pr-list", "write": False, "state": "all"}]
LOCK = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: processing"],
        "remove": [], "body_edit": False}
STAMP = {"route": "comment-edit", "write": True, "comment": 9501,
         "body": "**Spec gate kit** …\n\napproved at abc1234"}
PR = {"route": "pr-create", "write": True, "head": "feat/5", "base": "spec/5"}
MERGE_QA = {"route": "pr-merge", "write": True, "pr": "103"}
REPAIR = {"route": "issue-edit", "write": True, "issue": "5", "add": [],
          "remove": ["status: ready-for-dev"], "body_edit": False}


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


def transcript(text, dispatch=True, extra=()):
    ev = []
    if dispatch:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        ev.append(tool_result("t_scan", "| issue | … |"))
    for i, seat in enumerate(extra):
        ev.append(tool_use("Agent", {"prompt": "…", "subagent_type": seat}, "t_%d" % i))
        ev.append(tool_result("t_%d" % i, "done"))
    ev.append({"type": "result", "result": text})
    return ev


SHAPES = [
    ("the good pass: #5 illegal, queued with the remedy, nothing written", True, {}),
    ("the lock taken on #5 (next-stage launched)", False,
     {"journal": READS + [LOCK], "labels": ["track: spec", "status: ready-for-dev",
                                             "status: processing"]}),
    ("the kit re-stamped `approved at` (Path B2's first write)", False,
     {"journal": READS + [STAMP]}),
    ("a second implementation CR opened", False,
     {"journal": READS + [PR], "push": "feat/5"}),
    ("the implementer dispatched", False, {"extra": ["implementer"]}),
    ("the QA CR merged (integrate ran over the stale label)", False,
     {"journal": READS + [MERGE_QA]}),
    ("the label repaired by the loop", False,
     {"journal": READS + [REPAIR], "labels": ["track: spec"]}),
    ("the label gone with no journaled write", False, {"labels": ["track: spec"]}),
    ("a new branch on the remote", False, {"push": "feat/5-2"}),
    ("#5's row reads queued: next-stage", False,
     {"text": report(table=swap(TABLE, "| illegal: ready-for-dev on a passed stage (feat/5 "
                                "merged) | yes |",
                                "| queued: next-stage · ready-for-dev 12d | — |"),
                     queue=["Your queue:"])}),
    ("#5's row reads acted: integrate", False,
     {"text": report(table=swap(TABLE, "illegal: ready-for-dev on a passed stage (feat/5 merged)",
                                "acted: integrate — green"))}),
    ("the illegal clause without the label", False,
     {"text": report(table=swap(TABLE, "illegal: ready-for-dev on a passed stage (feat/5 merged)",
                                "illegal: stage mismatch"))}),
    ("#5 illegal but needs you —", False,
     {"text": report(table=swap(TABLE, "merged) | yes |", "merged) | — |"))}),
    ("#5 absent from the queue", False, {"text": report(queue=["Your queue:"])}),
    ("the queue item without its link", False,
     {"text": report(queue=swap(QUEUE, " — https://github.com/x/y/issues/5", ""))}),
    ("the queue item says reapply, not remove", False,
     {"text": report(queue=swap(QUEUE, "- #5 — remove `status: ready-for-dev`",
                                "- #5 — reapply `status: ready-for-dev`"))}),
    ("the label events of #5 never read", False,
     {"journal": [e for e in READS if e.get("route") != "label-events"]}),
    ("no scanner dispatched", False, {"dispatch": False}),
    ("the report has no table", False,
     {"text": "Patrol pass report\n\n#5: ready-for-dev is stale — remove it.\n"}),
]


def run_check(tmp, bare, *, text=None, journal=None, labels=None, push=None, dispatch=True,
              extra=()):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if labels is not None:
        st["issues"]["5"]["labels"] = labels
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (READS if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(report() if text is None else text, dispatch, extra):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    work = os.path.join(tmp, "work")
    if push:
        p = sh("git checkout -q -B %s origin/feat/5 && git commit -q --allow-empty -m x && "
               "git push -q origin %s && git checkout -q main" % (push, push), work)
        if p.returncode != 0:
            raise RuntimeError("push shape failed: %s" % p.stderr)
    try:
        env = dict(os.environ, RUN_DIR=run, BARE=bare)
        return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                              capture_output=True, text=True)
    finally:
        if push == "feat/5":
            sh("git push -q -f origin $(git rev-parse spec/5):refs/heads/feat/5 && "
               "git branch -q -f feat/5 spec/5", work)
        elif push:
            sh("git push -q origin --delete %s && git branch -q -D %s" % (push, push), work)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, bare, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F14 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
