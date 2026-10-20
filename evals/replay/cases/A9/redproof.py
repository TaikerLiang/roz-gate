#!/usr/bin/env python3
"""A9's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal and a transcript (the dispatches, the final
report); the checker reads no git, so no sandbox is seeded.

    python3 evals/replay/cases/A9/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))

REPLY = ("**[intake] · reply**\n\n"
         "**kai** — Q1 → (a) CSV is recorded as your input; paul confirms it with the gate "
         "label.\n\n"
         "**Q3 · Archived** — should an export include archived records?\n"
         "- (a) no, active records only ← ✅ recommended\n"
         "- (b) yes, with an archived column\n\n"
         "*why: archived records are hidden everywhere else in search.*\n\n"
         "When it settles, paul ends a comment with the line `summary` — or applies the gate "
         "label directly.")
LOCK = {"route": "issue-edit", "write": True, "issue": "7", "add": ["status: processing"],
        "remove": [], "body_edit": False}
UNLOCK = dict(LOCK, add=[], remove=["status: processing"])
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "cr-comments-list", "write": False, "target": "7"},
         {"route": "cr-comments-list", "write": False, "target": "8"}]


def write(issue, body):
    return {"route": "issue-comment", "write": True, "issue": issue, "body": body}


GOOD = {"journal": READS + [LOCK, write("7", REPLY), UNLOCK], "add": {"7": [REPLY]}}


def swap(old, new):
    out = REPLY.replace(old, new)
    assert out != REPLY, old
    return out


def with_reply(body):
    return {"journal": READS + [LOCK, write("7", body), UNLOCK], "add": {"7": [body]}}


SUMMARY = "**[intake] · summary**\n\n**Story** — As a support agent, I want to export results."
SHAPES = [
    ("the good pass: one reply on #7, nothing on #8", True, GOOD),
    ("the good pass without taking the lock", True,
     {"journal": READS + [write("7", REPLY)], "add": {"7": [REPLY]}}),
    ("silence: no reply on #7 (the 2.4.0 Otherwise route)", False, {"journal": READS}),
    ("a reply on #8 too (the bot triggered it)", False,
     {"journal": GOOD["journal"] + [write("8", REPLY)], "add": {"7": [REPLY], "8": [REPLY]}}),
    ("two replies on #7", False,
     {"journal": GOOD["journal"] + [write("7", REPLY)], "add": {"7": [REPLY, REPLY]}}),
    ("the reply @-mentions kai", False, with_reply(swap("**kai** —", "@kai —"))),
    ("the reply @-mentions the holder", False,
     with_reply(swap("paul confirms it", "@paul confirms it"))),
    ("a summary instead of a reply", False, with_reply(SUMMARY)),
    ("the reply re-asks the batch's Q1", False,
     with_reply(REPLY + "\n\n**Q1 · Format** — still CSV?\n- (a) yes\n- (b) no")),
    ("the reply never names kai", False, with_reply(swap("**kai** — ", ""))),
    ("the reply is unmarked", False, with_reply(swap("**[intake] · reply**\n\n", ""))),
    ("the reply opens with the batch marker, not the reply marker", False,
     with_reply(swap("**[intake] · reply**", "**[intake]**"))),
    ("the reply names no label as the decision", False,
     with_reply("**[intake] · reply**\n\n**kai** — thanks, noted: CSV it is.")),
    ("#7's body rewritten", False,
     {"journal": READS + [dict(LOCK, body_edit=True), write("7", REPLY), UNLOCK],
      "add": {"7": [REPLY]}, "body7": "**User story** — export."}),
    ("a track label applied on #7", False,
     {"journal": READS + [LOCK, write("7", REPLY), dict(UNLOCK, add=["track: spec"])],
      "add": {"7": [REPLY]}, "labels7": ["track: spec"]}),
    ("the lock left behind on #7", False,
     {"journal": READS + [LOCK, write("7", REPLY)], "add": {"7": [REPLY]},
      "labels7": ["status: processing"]}),
    ("a reply in the state with no journaled write", False, {"journal": READS,
                                                             "add": {"7": [REPLY]}}),
    ("a journaled reply that never reached the state", False,
     {"journal": GOOD["journal"]}),
    ("no sub-agent dispatched", False, dict(GOOD, dispatch=False)),
]


def transcript(dispatch):
    ev = []
    if dispatch:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t_scan", "name": "Task",
             "input": {"prompt": "…references/patrol-scan.md…",
                       "subagent_type": "general-purpose"}}]}})
    ev.append({"type": "result", "result": "Patrol pass report\n"})
    return ev


def run_check(tmp, journal, add=None, body7=None, labels7=None, dispatch=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    for n, bodies in (add or {}).items():
        for i, b in enumerate(bodies):
            st["issues"][n]["comments"].append(
                {"id": 900 + i, "author": "paul", "body": b, "createdAt": "2026-08-24T12:00:00Z"})
    if body7 is not None:
        st["issues"]["7"]["body"] = body7
    if labels7 is not None:
        st["issues"]["7"]["labels"] = labels7
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE="")
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp = tempfile.mkdtemp()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, **copy.deepcopy(kw))
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s A9 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
