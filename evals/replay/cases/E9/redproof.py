#!/usr/bin/env python3
"""E9's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (the as-built contract contradicting R5,
merged into spec/5; no qa/5); each shape stages what a Path B2 run left on
the remote (the Q appended to spec.md, a qa/5) and in the forge (the [qa]
thread, labels, the QA CR); check.py runs. Since #411 the declaring role's
thread with no QA dispatch is the second accepted road (B2.4).

    python3 evals/replay/cases/E9/redproof.py

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
APPEND_Q = ("git checkout -q spec/5 && printf -- '- **[qa] · Q3 · Deadline boundary**\\n\\n"
            "  Does an offer expiring exactly at now apply (R5) or not (as-built C2)?\\n'"
            " >> docs/specs/5/spec.md && git commit -qam 'spec: Q3 (qa)'"
            " && git push -q origin spec/5")
CUT_QA = ("git checkout -q spec/5 && git checkout -qb qa/5 && mkdir -p tests/acceptance/offers "
          "&& printf '# trace: S1\\n' > tests/acceptance/offers/test_expiry.py && git add -A "
          "&& git commit -qm 'qa suite #5 (S2 waits on Q3)' && git push -q origin qa/5")
GOOD_SHELL = APPEND_Q + " && " + CUT_QA
BODY = ("**[qa] · Q3 · Deadline boundary**\n\nR5 · The deadline is inclusive says an offer "
        "expiring exactly at `now` still applies; the as-built C2 excludes it "
        "(`expires_at <= now`). Which "
        "holds?\n\n- (a) R5 — amend C2 back to `<`, the implementation follows ← ✅ recommended\n"
        "- (b) C2 — amend R5 and S2\n\n*S2 waits on this; the suite tests the other scenarios.*")
THREAD = {"route": "thread-post-inline", "write": True, "pr": "101", "body": BODY,
          "path": "docs/specs/5/spec.md", "line": 18}
PROSE = {**THREAD, "body": BODY.replace("- (a) R5", "(a) R5").replace("\n- (b) C2", " (b) C2")}
REVIEWER = {**THREAD, "body": BODY.replace("**[qa]", "**[reviewer]")}
ON_QA_CR = {**THREAD, "pr": "104"}
LABEL = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: in-spec-review"]}
CREATE = {"route": "pr-create", "write": True, "pr": "104", "head": "qa/5", "draft": True}
READY = {"route": "pr-ready", "write": True, "pr": "104"}
ISR = ["track: spec", "status: in-spec-review"]
# #411 — the three runs of the 2026-11-19 sweep (184a0f9), their Q1 threads verbatim. r1 and r3
# dispatched QA; in r2 the main agent read the declared deviation and raised it itself.
R1 = {**THREAD, "body": (
    "**[qa] · Q1 · Boundary contradicts R5**\n\nShould an offer whose `expires_at` equals `now` "
    "apply, as R5 and S2 state, or be excluded, as deviation C2 states?\n\n- (a) Revert C2: keep "
    "the inclusive boundary (`expires_at < now` is excluded) ← ✅ recommended\n- (b) Amend R5 and "
    "S2 to exclusive via a spec-CR thread, and fold C2 in\n\n*C2 is a contradiction of R5 and S2. "
    "Observed: `price` returns 100 (list) at `expires_at == now`, where S2 requires the offer to "
    "apply. The test for S2 is red on this clause.*")}
R3 = {**THREAD, "line": 19, "body": (
    "**[qa] · Q1 · Boundary contradicts R5**\nShould an offer whose `expires_at` equals `now` be "
    "applied or excluded?\n- (a) Applied: inclusive per R5 and S2; C2 is reverted to match. ← ✅ "
    "recommended\n- (b) Excluded: `expires_at <= now` as C2 states; R5 and S2 are amended to "
    "match.\n\n*C2 contradicts R5 (\"The deadline is inclusive\") and S2 (\"Then the offer is "
    "applied\"). C2's stated reason, that the approved text was silent on the boundary, is false: "
    "R5 states it explicitly.*")}
R2_BODY = (
    "**[implementer] · Q1 · expiry boundary**\n\nShould an offer whose `expires_at` equals `now` "
    "still apply, as R5 says, or be excluded, as the as-built C2 says?\n\n- (a) R5 stands: the "
    "deadline is inclusive; the code changes to match S2 ← ✅ recommended\n- (b) C2 stands: the "
    "deadline is exclusive; R5 and S2 are amended to match\n\n*R5 comes from the approved Q2 "
    "decision and S2 depends on it; CR #102 declares C2 as a boundary the approved text was silent "
    "on, but R5 states it explicitly.*")
R2 = {**THREAD, "body": R2_BODY}
R2_PROSE = {**R2, "body": R2_BODY.replace("\n- (a) R5", "\n(a) R5").replace("\n- (b) C2",
                                                                            " (b) C2")}
SILENT_R5 = ("git checkout -q spec/5 && printf -- '\nR5 (amended): the deadline is exclusive.\n'"
             " >> docs/specs/5/spec.md && git commit -qam 'spec: R5 follows C2'"
             " && git push -q origin spec/5")

# (name, should pass, shell before check, journal, labels at the end)
SHAPES = [
    ("B2.5 as written: Q appended, [qa] thread with bullets on the spec CR, in-spec-review, "
     "draft QA CR", True, GOOD_SHELL, [THREAD, LABEL, CREATE], ISR),
    ("the finding written as prose options (rule F)", False, GOOD_SHELL, [PROSE, LABEL, CREATE],
     ISR),
    ("the finding posted on the QA CR instead of the spec CR", False, GOOD_SHELL,
     [ON_QA_CR, LABEL, CREATE], ISR),
    ("the finding tagged [reviewer], not [qa]", False, GOOD_SHELL, [REVIEWER, LABEL, CREATE],
     ISR),
    ("no thread at all — the finding stayed in QA's report", False, GOOD_SHELL, [LABEL, CREATE],
     ISR),
    ("the label not applied (no backward transition)", False, GOOD_SHELL, [THREAD, CREATE],
     ["track: spec"]),
    ("the QA CR readied while the [qa] thread is open", False, GOOD_SHELL,
     [THREAD, LABEL, CREATE, READY], ISR),
    ("spec.md's Open Questions never gained the item", False, CUT_QA, [THREAD, LABEL, CREATE],
     ISR),
    ("a STOP instead of the thread", False, GOOD_SHELL, [THREAD],
     ["track: spec", "status: blocked"]),
    ("the lock left behind", False, GOOD_SHELL, [THREAD, LABEL, CREATE],
     ISR + ["status: processing"]),
    ("#411 run-1's own thread: QA raised it, draft QA CR", True, GOOD_SHELL, [R1, LABEL, CREATE],
     ISR),
    ("#411 run-3's own thread: QA raised it, draft QA CR", True, GOOD_SHELL, [R3, LABEL, CREATE],
     ISR),
    ("#411 run-2's own thread: the main agent raised the declared deviation as [implementer], "
     "QA never dispatched (B2.4)", True, APPEND_Q, [R2, LABEL], ISR),
    ("#411 the main agent raised it, then dispatched QA anyway — a QA CR exists", False,
     GOOD_SHELL, [R2, LABEL, CREATE], ISR),
    ("#411 the main agent raised it and a QA CR was readied", False, GOOD_SHELL,
     [R2, LABEL, CREATE, READY], ISR),
    ("#411 the main agent's thread with prose options (rule F)", False, APPEND_Q,
     [R2_PROSE, LABEL], ISR),
    ("#411 the main agent's thread on the implementation CR, not the spec CR", False, APPEND_Q,
     [{**R2, "pr": "102"}, LABEL], ISR),
    ("#411 a role that declared nothing ([reviewer]) raises it, no QA CR", False, APPEND_Q,
     [{**R2, "body": R2_BODY.replace("**[implementer]", "**[reviewer]")}, LABEL], ISR),
    ("#411 the R silently edited to follow the deviation — no thread", False, SILENT_R5, [LABEL],
     ISR),
]


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


def check(tmp, bare, journal, labels):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = list(labels)
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "result", "result": "next-stage: #5 Path B2 — one [qa] "
                                                        "finding posted; in-spec-review."}) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want_pass, before, journal, labels in SHAPES:
        tmp, work, bare = sandbox()
        try:
            setup = sh(before, work)
            if setup.returncode != 0:
                print("FAIL E9 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                failed += 1
                continue
            p = check(tmp, bare, journal, labels)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s E9 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
