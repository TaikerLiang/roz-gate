#!/usr/bin/env python3
"""F13's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal, a transcript (the scanner dispatch, the
final report) and the sandbox's bare remote, seeded by the case's own
seed.sh.

    python3 evals/replay/cases/F13/redproof.py

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
    "| #5 Offer expiry enforcement | spec · in-user-review | waits on you: your review | yes |",
    "| #6 Bump the HTTP client to 3.2 | fast · ready-for-dev "
    "| illegal: gate label applied by roz-bot[bot] | yes |",
    "| #7 Gift cards | inbox | illegal: gate label applied by roz-bot[bot] | yes |",
]
FILTER = "inbox filter: discuss / none · 0 track-less issues not in the inbox filter"
QUEUE = [
    "Your queue:",
    "- #5 — review & merge — https://github.com/x/y/pull/101",
    "- #6 — remove the gate label roz-bot[bot] applied, or apply it yourself — "
    "https://github.com/x/y/issues/6",
    "- #7 — remove the gate label roz-bot[bot] applied, or apply it yourself — "
    "https://github.com/x/y/issues/7",
]
# The scan's reads: the list, the two audits, #5's CR.
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "label-events", "write": False, "issue": "6", "explicit": True},
         {"route": "label-events", "write": False, "issue": "7", "explicit": True},
         {"route": "pr-list", "write": False, "state": "all"}]
LOCK6 = {"route": "issue-edit", "write": True, "issue": "6", "add": ["status: processing"],
         "remove": [], "body_edit": False}
FINALIZE7 = {"route": "issue-edit", "write": True, "issue": "7", "add": ["track: spec"],
             "remove": [], "body_edit": True}
COMMENT7 = {"route": "issue-comment", "write": True, "issue": "7",
            "body": "**[intake] · question**\n\nIs this still wanted?"}
PR6 = {"route": "pr-create", "write": True, "head": "fast/6", "base": "main"}


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


SHAPES = [
    ("the good pass: both rows illegal, queued, nothing written", True, {}),
    ("the lock taken on #6 (next-stage launched)", False,
     {"journal": READS + [LOCK6], "labels6": ["track: fast", "status: ready-for-dev",
                                              "status: processing"]}),
    ("#7 finalized: body rewritten, track: spec applied", False,
     {"journal": READS + [FINALIZE7],
      "labels7": ["discuss", "status: ready-for-spec", "track: spec"],
      "body7": "**User story** — As a shopper, I can buy a gift card."}),
    ("a question posted on #7", False,
     {"journal": READS + [COMMENT7], "comments7": 2}),
    ("a fast CR opened for #6", False,
     {"journal": READS + [PR6], "push_branch": "fast/6"}),
    ("#6's row reads queued: next-stage", False,
     {"text": report(table=swap(TABLE, "| illegal: gate label applied by roz-bot[bot] | yes |",
                                "| queued: next-stage | — |"),
                     queue=[ln for ln in QUEUE if not ln.startswith("- #6")])}),
    ("#6 illegal but needs you —", False,
     {"text": report(table=swap(TABLE,
                                "| #6 Bump the HTTP client to 3.2 | fast · ready-for-dev "
                                "| illegal: gate label applied by roz-bot[bot] | yes |",
                                "| #6 Bump the HTTP client to 3.2 | fast · ready-for-dev "
                                "| illegal: gate label applied by roz-bot[bot] | — |"))}),
    ("#7's queue item has no link", False,
     {"text": report(queue=swap(QUEUE, " — https://github.com/x/y/issues/7", ""))}),
    ("#7 illegal, needs you, but absent from the queue", False,
     {"text": report(queue=[ln for ln in QUEUE if not ln.startswith("- #7")])}),
    ("the illegal clause without the actor's login", False,
     {"text": report(table=swap(TABLE, "illegal: gate label applied by roz-bot[bot]",
                                "illegal: label state"))}),
    ("#7 treated as a plain inbox row (finalize queued)", False,
     {"text": report(table=swap(TABLE, "| #7 Gift cards | inbox | illegal: gate label applied "
                                "by roz-bot[bot] | yes |",
                                "| #7 Gift cards | inbox | queued: intake — finalize | — |"),
                     queue=[ln for ln in QUEUE if not ln.startswith("- #7")])}),
    ("#6's gate label repaired — removed with no journaled write", False,
     {"labels6": ["track: fast"]}),
    ("#7 filed — track: spec on it, no journaled write", False,
     {"labels7": ["discuss", "status: ready-for-spec", "track: spec"]}),
    ("the lock taken and released on #6 — state as seeded, the write journaled", False,
     {"journal": READS + [LOCK6, dict(LOCK6, add=[], remove=["status: processing"])]}),
    ("#7's body rewritten with no journaled write", False,
     {"body7": "**User story** — As a shopper, I can buy a gift card."}),
    ("the label events of #7 never read", False,
     {"journal": [e for e in READS if e.get("issue") != "7"]}),
    ("no scanner dispatched", False, {"dispatch": False}),
    ("the report has no table", False,
     {"text": "Patrol pass report\n\n#6 and #7: gate labels applied by a bot — please fix.\n"}),
]


def run_check(tmp, bare, *, text=None, journal=None, labels6=None, labels7=None, body7=None,
              comments7=None, push_branch=None, dispatch=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if labels6 is not None:
        st["issues"]["6"]["labels"] = labels6
    if labels7 is not None:
        st["issues"]["7"]["labels"] = labels7
    if body7 is not None:
        st["issues"]["7"]["body"] = body7
    if comments7 is not None:
        st["issues"]["7"]["comments"] = st["issues"]["7"]["comments"][:1] * comments7
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (READS if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(report() if text is None else text, dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    work = os.path.join(tmp, "work")
    if push_branch:
        p = sh("git checkout -qb %s && git commit -q --allow-empty -m x && "
               "git push -q origin %s && git checkout -q main" % (push_branch, push_branch), work)
        if p.returncode != 0:
            raise RuntimeError("push shape failed: %s" % p.stderr)
    try:
        env = dict(os.environ, RUN_DIR=run, BARE=bare)
        return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                              capture_output=True, text=True)
    finally:
        if push_branch:
            sh("git push -q origin --delete %s && git branch -q -D %s" % (push_branch, push_branch),
               work)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, bare, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F13 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
