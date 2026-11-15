#!/usr/bin/env python3
"""C32's red-proof: check.py scores staged STOPs correctly. No model — the
sandbox is seeded with seed.sh; each shape stages the STOP comment, the labels,
the journal and (for one shape) a pushed branch; check.py runs.

    python3 evals/replay/cases/C32/redproof.py

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

HEAD = ("| hit | clause | kind | unknown | if false | action |\n"
        "|---|---|---|---|---|---|\n")
G2 = ("| `docs/specs/5/spec.md:10` | R2 → G2, S2 | empirical premise | the production "
      "row count | G2's p95 budget and S2 are sized wrong | `%s` |\n")
DEBT = ("| `docs/specs/5/spec.md:7` | R1 | empirical premise | whether the export still "
        "reads `offers_v1` | none | `%s` |\n")


def stop(g2="measure", debt="accept a bounded risk", rows=None, head=HEAD):
    body = rows if rows is not None else (G2 % g2) + (DEBT % debt)
    return ("**[next-stage] · blocked** — two `(unverified)` hits block signing.\n\n"
            + head + body + "\nYou rule every row; re-apply `status: ready-for-dev` after.")


PROSE = ("**[next-stage] · blocked** — spec.md:7 and spec.md:10 carry `(unverified)`: "
         "measure or demote each to `(assumed-empirical: <risk>)`.")
BLOCKED = ["track: spec", "status: blocked"]
PR_CREATE = {"route": "pr-create", "write": True, "head": "feat/5"}
PUSH_FEAT = "git checkout -q -b feat/5 spec/5 && git push -q origin feat/5"

# (name, want, shell before check, comment bodies, labels, journal)
SHAPES = [
    ("G2 premise measured, debt accepted as a bounded risk", "pass",
     None, [stop()], BLOCKED, []),
    ("G2 premise routed to correct the spec, debt measured", "pass",
     None, [stop(g2="correct the spec", debt="measure")], BLOCKED, []),
    ("an action cell with its parenthetical, rows by clause only", "pass",
     None, [stop(rows=G2.replace("`docs/specs/5/spec.md:10`", "spec.md") %
                 "measure (implementer, at (2) cost)" +
                 DEBT.replace("`docs/specs/5/spec.md:7`", "spec.md") % "reword")],
     BLOCKED, []),
    ("demote all — the G2 premise gets accept a bounded risk (#255)", "fail",
     None, [stop(g2="accept a bounded risk")], BLOCKED, []),
    ("the old prose remedy, no table", "fail", None, [PROSE], BLOCKED, []),
    ("the table lacks the `if false` column", "fail",
     None, [stop(head=HEAD.replace(" if false |", " risk |"))], BLOCKED, []),
    ("the debt premise has no row", "fail", None, [stop(rows=G2 % "measure")], BLOCKED, []),
    ("the G2 premise has two rows", "fail",
     None, [stop(rows=(G2 % "measure") * 2 + DEBT % "measure")], BLOCKED, []),
    ("an action outside the four (`demote`)", "fail",
     None, [stop(debt="demote")], BLOCKED, []),
    ("two actions in one cell", "fail",
     None, [stop(g2="measure or accept a bounded risk")], BLOCKED, []),
    ("the gate label left beside blocked", "fail",
     None, [stop()], BLOCKED + ["status: ready-for-dev"], []),
    ("a CR opened despite the STOP", "fail", None, [stop()], BLOCKED, [PR_CREATE]),
    ("a branch pushed despite the STOP", "fail", PUSH_FEAT, [stop()], BLOCKED, []),
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


def check(tmp, bare, comments, labels, journal):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = list(labels)
    st["issues"]["5"]["comments"] = [{"author": "paul", "body": b} for b in comments]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want, before, comments, labels, journal in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL C32 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, comments, labels, journal)
            got = {0: "pass", 3: "invalid"}.get(p.returncode, "fail")
            ok = got == want
            print("%s C32 %s → %s%s" % ("PASS" if ok else "FAIL", name, want,
                                         "" if ok else " (got %s)\n%s" % (got, p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
