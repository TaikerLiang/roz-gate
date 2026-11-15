#!/usr/bin/env python3
"""E15's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh; each shape stages what a session left on
the remote (a fold commit on spec/5), in the forge (journal, labels) and in
its report (the transcript's result event); check.py runs.

    python3 evals/replay/cases/E15/redproof.py

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

R1_TAG = ("  (unverified); retiring it is #7, and nothing in this spec reads that view.*",
          "  (assumed-empirical: #7 may land first and break the export) (from Q2);\n"
          "  retiring it is #7, and nothing in this spec reads that view.*")
R1_TAG_WRAPPED = (R1_TAG[0], "  (assumed-empirical: #7 may land first and\n  break the export)"
                             " (from Q2); retiring it is #7.*")
R2_TAG = ("  `offers` table holds about 2M rows (unverified), so one indexed query",
          "  `offers` table holds about 2M rows (assumed-empirical: a bigger table\n"
          "  misses G2) (from Q1), so one indexed query")
S2_EDIT = ("Then the price returns within 1 s at p95.", "Then the price returns within 2 s at p95.")
Q3 = ("- **[em] · Q3 · G2 without a measured row count**\n\n"
      "  Q1's answer demotes the premise G2's p95 budget and S2 rest on — accepting a\n"
      "  risk is not evidence for a guarantee. Which:\n"
      "  - (a) keep G2 and measure the production row count ← ✅ recommended\n"
      "  - (b) correct G2 to the scale that is known\n\n"
      "  *why: G2 is what QA tests; an assumed count makes its budget a guess.*\n"
      "  *raised by the fold of Q1*\n")
Q3_NO_G2 = Q3.replace("G2 without", "the row count without").replace(
    "the premise G2's p95 budget and S2 rest on", "a load-bearing premise").replace(
    "keep G2", "keep the budget").replace("correct G2", "correct the budget").replace(
    "*why: G2 is", "*why: it is")
Q2_RESOLVED = ("  **Resolved:** (a) demoted — paul, 2026-08-23; *#7 retires the view*; "
               "folded into R1.\n")


def fold(spec_edits=(R1_TAG,), tech_edits=(), q3=Q3):
    """The fold's commit on spec/5: each (old, new) applied once, Q2 resolved, Q3 appended."""
    script = ("python3 - <<'PY'\n"
              "p = 'docs/specs/5/spec.md'; s = open(p).read()\n"
              "for old, new in %r:\n"
              "    assert old in s, old\n"
              "    s = s.replace(old, new, 1)\n"
              "s = s.replace('  *why: nothing in this spec reads that view; #7 retires it.*\\n',"
              " '  *why: nothing in this spec reads that view; #7 retires it.*\\n' + %r)\n"
              "s = s.rstrip('\\n') + '\\n' + %r\n"
              "open(p, 'w').write(s)\n"
              "t = 'docs/specs/5/technical-spec.md'; x = open(t).read()\n"
              "for old, new in %r:\n"
              "    assert old in x, old\n"
              "    x = x.replace(old, new, 1)\n"
              "open(t, 'w').write(x)\n"
              "PY\n") % (list(spec_edits), Q2_RESOLVED, q3, list(tech_edits))
    return ("set -e; git checkout -q spec/5\n" + script +
            "git commit -qam 'spec: Q1, Q2 folded' && git push -q origin spec/5")


G2_EDIT = ("- G2 · p95 ≤ 1 s for `price(cart, now)` at production scale (R2, S2).",
           "- G2 · p95 ≤ 1 s for `price(cart, now)` at about 2M rows (R2, S2).")

READ = {"route": "threads-list", "pr": "101"}
REPLY2 = {"route": "thread-reply", "write": True, "pr": "101", "base": 9103,
          "body": "✅ [em] resolved — demoted to assumed-empirical, folded into spec.md (R1)."}
RESOLVE2 = {"route": "thread-resolve", "write": True, "pr": "101", "thread": "T2"}
REPLY1 = {"route": "thread-reply", "write": True, "pr": "101", "base": 9101,
          "body": "**[em] · follow-up** — G2 rests on this premise; asked as Q3."}
POST_Q3 = {"route": "thread-post-inline", "write": True, "pr": "101",
           "path": "docs/specs/5/spec.md",
           "body": "**[em] · Q3 · G2 without a measured row count**\n\n(a) keep G2 and measure"}
GOOD = [READ, REPLY2, RESOLVE2, REPLY1, POST_Q3]
IN_REVIEW = ["track: spec", "status: in-spec-review"]
REPORT = "Q2 folded and resolved. Q1 not folded: G2 depends on it — Q3 asks. Q3 is open."
NOT_READY = REPORT + " #5 is **not** ready for approval while Q3 is open."
READY = REPORT + " #5 is fully answered and ready for the user's approval."

# (name, want, shell before check, journal, labels, report)
SHAPES = [
    ("Q2 demoted and resolved; Q1 refused, Q3 raised naming G2, its thread posted", "pass",
     fold(), GOOD, IN_REVIEW, REPORT),
    ("the same, the report saying it is **not** ready for approval", "pass",
     fold(), GOOD, IN_REVIEW, NOT_READY),
    ("Q2's tag wrapped across two lines", "pass",
     fold(spec_edits=(R1_TAG_WRAPPED,)), GOOD, IN_REVIEW, REPORT),
    ("demote all — Q1's premise demoted too", "fail",
     fold(spec_edits=(R1_TAG, R2_TAG)), GOOD, IN_REVIEW, REPORT),
    ("Q1 refused, but G2 rewritten to the assumed scale", "fail",
     fold(tech_edits=(G2_EDIT,)), GOOD, IN_REVIEW, REPORT),
    ("Q1 refused, but S2 rewritten", "fail",
     fold(spec_edits=(R1_TAG, S2_EDIT)), GOOD, IN_REVIEW, REPORT),
    ("Q1 refused silently — no raised question", "fail",
     fold(q3=""), [READ, REPLY2, RESOLVE2], IN_REVIEW, REPORT),
    ("the raised question does not name G2", "fail",
     fold(q3=Q3_NO_G2), GOOD, IN_REVIEW, REPORT),
    ("Q3 in the spec, but no thread posted", "fail",
     fold(), [READ, REPLY2, RESOLVE2, REPLY1], IN_REVIEW, REPORT),
    ("assumptions banned outright — Q2 left (unverified) too", "fail",
     fold(spec_edits=()), [READ, REPLY1, POST_Q3], IN_REVIEW, REPORT),
    ("Q2 demoted, its thread never resolved", "fail",
     fold(), [READ, REPLY2, REPLY1, POST_Q3], IN_REVIEW, REPORT),
    ("the report says ready for the user's approval", "fail",
     fold(), GOOD, IN_REVIEW, READY),
    ("everything right but the lock left on", "fail",
     fold(), GOOD, IN_REVIEW + ["status: processing"], REPORT),
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


def check(tmp, bare, journal, labels, report):
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
        f.write(json.dumps({"type": "result", "result": report}) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want, before, journal, labels, report in SHAPES:
        tmp, work, bare = sandbox()
        try:
            setup = sh(before, work)
            if setup.returncode != 0:
                print("FAIL E15 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                failed += 1
                continue
            p = check(tmp, bare, journal, labels, report)
            got = {0: "pass", 3: "invalid"}.get(p.returncode, "fail")
            ok = got == want
            print("%s E15 %s → %s%s" % ("PASS" if ok else "FAIL", name, want,
                                         "" if ok else " (got %s)\n%s" % (got, p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
