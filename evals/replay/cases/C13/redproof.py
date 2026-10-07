#!/usr/bin/env python3
"""C13's red-proof: check.py scores staged runs correctly. No model — each
shape is a synthetic transcript (a scanner dispatch and its table, the main
agent's later calls) plus a forge journal, over the seeded sandbox.

    python3 evals/replay/cases/C13/redproof.py

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
LOCK = 'gh issue edit 5 --add-label "status: processing"'
GOOD_TABLE = "\n".join([
    "| issue | track | status | holder | cr | unheard | verdict | evidence |",
    "|---|---|---|---|---|---|---|---|",
    "| #5 Offer expiry enforcement | spec | — | paul | 101 open | 0 "
    "| actionable: integrate | feat/5 #102 merged, qa/5 #103 merged — both thread-clean |",
    "inbox filter: none · 0 track-less issues not in the inbox filter"])
# The old reading: merged CRs are absent, so the finished build is "in progress".
STALE_TABLE = GOOD_TABLE.replace(
    "| actionable: integrate | feat/5 #102 merged, qa/5 #103 merged — both thread-clean |",
    "| in progress | no feat/5 or qa/5 CR open |")


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


def transcript(table, scanner=True, scanner_write=False, lock=True):
    ev = []
    if scanner:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        # the all-states CR-FIND is a read
        ev.append(tool_use("Bash", {"command": "gh pr list --head feat/5 --state all "
                                               "--json number,state,isDraft,url"},
                           "t_s1", parent="t_scan"))
        ev.append(tool_result("t_s1", '[{"number":102,"state":"MERGED"}]', parent="t_scan"))
        if scanner_write:
            ev.append(tool_use("Bash", {"command": LOCK}, "t_s2", parent="t_scan"))
            ev.append(tool_result("t_s2", "", parent="t_scan"))
        ev.append(tool_result("t_scan", table))
    if lock:
        ev.append(tool_use("Bash", {"command": LOCK}, "t_m1"))
        ev.append(tool_result("t_m1", ""))
    ev.append({"type": "result", "result": "done"})
    return ev


def run_check(tmp, bare, table, *, scanner=True, scanner_write=False, lock=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    journal = []
    if lock:
        st["issues"]["5"]["labels"].append("status: processing")
        journal.append({"route": "issue-edit", "write": True, "issue": "5",
                        "add": ["status: processing"]})
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(table, scanner, scanner_write, lock):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


SHAPES = [
    ("the row reads actionable: integrate and the pass locks #5", True, {}),
    ("the stale reading: merged CRs absent, row says in progress", False,
     {"table": STALE_TABLE}),
    ("the row is right but the pass acted on nothing", False, {"lock": False}),
    ("the scanner wrote the lock itself", False, {"scanner_write": True}),
    ("no scanner at all (the old in-context scan)", False, {"scanner": False}),
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
            print("%s C13 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
