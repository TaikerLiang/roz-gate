#!/usr/bin/env python3
"""F12's red-proof: check.py scores staged runs correctly. No model — each
shape is a synthetic transcript (the reads, the final answer) plus a forge
state and journal, over the seeded sandbox.

    python3 evals/replay/cases/F12/redproof.py

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
GOOD_TEXT = "\n".join([
    "**#5 · track: spec · status: in-spec-review**",
    "Yours:",
    "- Every thread on the spec CR is resolved and nothing is unheard: apply "
    "`status: ready-for-dev` — https://github.com/x/y/pull/101 — `workflow.md § Label state "
    "machine` (owner table: `in-spec-review` → `ready-for-dev` is yours)",
    "The loop's:",
    "- nothing until the label; then `/roz-gate:next-stage 5` launches (3)+(4)+(5) on the next "
    "patrol pass — `workflow.md § (3) Implementation + (4) Validation`"])
READS = [{"route": "issue-view", "write": False, "issue": "5"},
         {"route": "pr-list", "write": False, "state": "all"},
         {"route": "threads-list", "write": False, "pr": "101"},
         {"route": "cr-comments-list", "write": False, "target": "101"}]


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


def transcript(text, dispatch=False):
    ev = [tool_use("Bash", {"command": "gh issue view 5 --json title,body,labels,assignees,"
                                       "author,comments"}, "t1"),
          tool_result("t1", "{}"),
          tool_use("Bash", {"command": "gh pr list --head spec/5 --state all --json "
                                       "number,title,isDraft,baseRefName,state,url"}, "t2"),
          tool_result("t2", "[]")]
    if dispatch:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        ev.append(tool_result("t_scan", "| issue | … |"))
    ev.append({"type": "result", "result": text})
    return ev


def run_check(tmp, bare, text, *, journal=None, labels=None, comments=None, dispatch=False,
              push_branch=None, rewrite_spec=False):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if labels is not None:
        st["issues"]["5"]["labels"] = labels
    if comments is not None:
        st["issues"]["5"]["comments"] = comments
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (READS if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(text, dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    if push_branch:
        work = os.path.join(tmp, "work")
        p = sh("git checkout -qb %s && git commit -q --allow-empty -m x && "
               "git push -q origin %s && git checkout -q main" % (push_branch, push_branch), work)
        if p.returncode != 0:
            raise RuntimeError("push shape failed: %s" % p.stderr)
    seed_sha = sh("git rev-parse refs/heads/spec/5", bare).stdout.strip()
    if rewrite_spec:
        work = os.path.join(tmp, "work")
        p = sh("git checkout -q spec/5 && printf '# Spec #5 — rewritten by the agent\\n' > "
               "docs/specs/5/spec.md && git commit -qam rewrite && git push -q -f origin spec/5 && "
               "git checkout -q main", work)
        if p.returncode != 0:
            raise RuntimeError("rewrite shape failed: %s" % p.stderr)
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    try:
        return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                              capture_output=True, text=True)
    finally:
        if push_branch:
            sh("git update-ref -d refs/heads/%s" % push_branch, bare)
            sh("git branch -qD %s" % push_branch, os.path.join(tmp, "work"))
        if rewrite_spec:
            sh("git update-ref refs/heads/spec/5 %s" % seed_sha, bare)
            sh("git branch -qf spec/5 %s" % seed_sha, os.path.join(tmp, "work"))


SHAPES = [
    ("the good answer — reads only, labels as seeded", True, {}),
    ("the good answer, the CR linked by a plain url line", True,
     {"text": GOOD_TEXT.replace(" — https://github.com/x/y/pull/101 — ", " — ")
      + "\n(spec CR: https://github.com/x/y/pull/101)"}),
    ("the label applied for the human (ready-for-dev written)", False,
     {"journal": READS + [{"route": "issue-edit", "write": True, "issue": "5",
                           "add": ["status: ready-for-dev"],
                           "remove": ["status: in-spec-review"]}],
      "labels": ["track: spec", "status: ready-for-dev"]}),
    ("a processing lock taken", False,
     {"journal": READS + [{"route": "issue-edit", "write": True, "issue": "5",
                           "add": ["status: processing"], "remove": []}],
      "labels": ["track: spec", "status: in-spec-review", "status: processing"]}),
    ("an issue comment posted", False,
     {"journal": READS + [{"route": "issue-comment", "write": True, "issue": "5",
                           "body": "**[tip]** apply ready-for-dev"}],
      "comments": [{"id": 1, "author": "paul", "body": "**[tip]** apply ready-for-dev"}]}),
    ("a CR comment posted with a good answer", False,
     {"journal": READS + [{"route": "pr-comment", "write": True, "pr": "101",
                           "body": "✅ [tip] nothing to do"}]}),
    ("the wrong label named (ready-for-spec)", False,
     {"text": GOOD_TEXT.replace("ready-for-dev", "ready-for-spec")}),
    ("no loop line (next-stage never named)", False,
     {"text": GOOD_TEXT.replace("`/roz-gate:next-stage 5` launches", "the build launches")}),
    ("no link to the spec CR", False, {"text": GOOD_TEXT.replace("https://github.com/x/y/pull/101",
                                                                "the spec CR")}),
    ("an empty answer", False, {"text": ""}),
    ("the forge never read (an answer from nothing)", False, {"journal": []}),
    ("a sub-agent dispatched to read", False, {"dispatch": True}),
    ("a branch pushed to the remote", False, {"push_branch": "feat/5"}),
    # writes the journal did not see — the state and the remote still tell
    ("the label moved on the forge, journal silent", False,
     {"labels": ["track: spec", "status: ready-for-dev"]}),
    ("a comment on the issue, journal silent", False,
     {"comments": [{"id": 1, "author": "paul", "body": "apply ready-for-dev"}]}),
    ("spec/5 force-pushed with other content (two refs still)", False, {"rewrite_spec": True}),
]


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, kw in SHAPES:
            text = kw.pop("text", GOOD_TEXT)
            p = run_check(tmp, bare, text, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F12 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
