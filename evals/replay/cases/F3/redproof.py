#!/usr/bin/env python3
"""F3's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh, then a spec/5 like the spec round's is
pushed (or not); each shape stages the forge (the CR, its threads, labels,
the journal) and check.py runs.

    python3 evals/replay/cases/F3/redproof.py

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
Q1 = "**[product] · Q1 · Expiry boundary instant**"
Q2 = "**[em] · Q2 · Clock source for `now`**"
SPEC = ("# Spec #5 — Offer expiry enforcement\n\n## Rules\n- **R1 · Expired offers do not "
        "apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then "
        "it is not applied.\n\n## Open Questions\n\n- %s\n  (a) … ← ✅ recommended\n\n- %s\n"
        "  (a) … ← ✅ recommended\n" % (Q1, Q2))
TECH = "# Technical spec #5\n\n## Contract\n- `price(cart, now)` excludes expired offers.\n"
TECH_OQ = TECH + "\n## Open questions\n- Which clock?\n"
DONE = ["track: spec", "status: in-spec-review"]


def thread(i, body):
    return {"id": "T%d" % i, "isResolved": False, "path": "docs/specs/5/spec.md", "line": "12",
            "comments": [{"databaseId": i, "author": "paul", "body": body}]}


def post(i, body):
    return {"route": "thread-post-inline", "write": True, "pr": "101", "body": body,
            "path": "docs/specs/5/spec.md", "comment": i}


DELETE = {"route": "review-comment-delete", "write": True, "pr": "101", "comment": 1003}
TWO = [thread(1001, Q1), thread(1002, Q2)]
TWO_POSTED = [post(1001, Q1), post(1002, Q2)]
PROBE = "probe — checking the inline anchor"

# (name, should pass, spec branch: "docs" | "tech-oq" | None, threads at the end,
#  journal, labels, CRs on spec/5)
SHAPES = [
    ("both docs pushed, one CR, two threads for two Open Questions", True,
     "docs", TWO, TWO_POSTED, DONE, 1),
    ("a probe thread posted and deleted: 3 posts − 1 delete = 2 live threads (#330, F3/run-2)",
     True, "docs", TWO, TWO_POSTED + [post(1003, PROBE), DELETE], DONE, 1),
    ("a third thread still open beside the two questions", False,
     "docs", TWO + [thread(1003, PROBE)], TWO_POSTED + [post(1003, PROBE)], DONE, 1),
    ("a question written but never surfaced (the E2 failure)", False,
     "docs", TWO[:1], TWO_POSTED[:1], DONE, 1),
    ("both questions surfaced, then one thread deleted", False,
     "docs", TWO[:1], TWO_POSTED + [dict(DELETE, comment=1002)], DONE, 1),
    ("no threads at all", False, "docs", [], [], DONE, 1),
    ("labels: ready-for-spec left beside in-spec-review", False,
     "docs", TWO, TWO_POSTED, DONE + ["status: ready-for-spec"], 1),
    ("technical-spec.md keeps an open-questions section", False,
     "tech-oq", TWO, TWO_POSTED, DONE, 1),
    ("two CRs opened from spec/5", False, "docs", TWO, TWO_POSTED, DONE, 2),
    ("spec/5 never pushed", False, None, TWO, TWO_POSTED, DONE, 1),
]


def sh(cmd, cwd):
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=dict(os.environ, **GIT_ID),
                          capture_output=True, text=True)


def sandbox(branch):
    tmp = tempfile.mkdtemp()
    work, bare = os.path.join(tmp, "work"), os.path.join(tmp, "origin.git")
    os.makedirs(work)
    steps = [("git init -q --bare %s" % bare, tmp),
             ("git init -q -b main", work),
             ("bash %s %s" % (os.path.join(CASE, "seed.sh"), ROOT), work),
             ("git remote add origin %s && git push -q origin --all" % bare, work)]
    if branch:
        steps.append(("git checkout -qb spec/5 && mkdir -p docs/specs/5 && "
                      "printf '%%s' %s > docs/specs/5/spec.md && "
                      "printf '%%s' %s > docs/specs/5/technical-spec.md && git add -A && "
                      "git commit -qm 'spec docs #5' && git push -q origin spec/5"
                      % (shquote(SPEC), shquote(TECH_OQ if branch == "tech-oq" else TECH)),
                      work))
    for cmd, cwd in steps:
        p = sh(cmd, cwd)
        if p.returncode != 0:
            raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stderr))
    return tmp, bare


def shquote(text):
    return "'" + text.replace("'", "'\"'\"'") + "'"


def check(tmp, bare, threads, journal, labels, crs):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = list(labels)
    st["prs"] = {str(101 + i): {"number": 101 + i, "title": "Spec #5", "state": "OPEN",
                                "headRefName": "spec/5", "baseRefName": "main",
                                "threads": threads if i == 0 else [], "comments": []}
                 for i in range(crs)}
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "result", "result": "next-stage: #5 in spec review."}) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    boxes = {}
    try:
        for name, want_pass, branch, threads, journal, labels, crs in SHAPES:
            if branch not in boxes:
                boxes[branch] = sandbox(branch)
            tmp, bare = boxes[branch]
            p = check(tmp, bare, threads, journal, labels, crs)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F3 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        for tmp, _ in boxes.values():
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
