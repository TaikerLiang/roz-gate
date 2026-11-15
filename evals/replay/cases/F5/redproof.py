#!/usr/bin/env python3
"""F5's red-proof: check.py scores staged STOPs correctly. No model — the
sandbox is seeded with seed.sh; each shape stages the STOP comment, the labels,
the journal and (for one shape) a pushed branch; check.py runs.

    python3 evals/replay/cases/F5/redproof.py

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

TABLE = ("**[next-stage] · blocked** — one `(unverified)` hit blocks signing.\n\n"
         "| hit | clause | kind | unknown | if false | action |\n|---|---|---|---|---|---|\n"
         "| `docs/specs/5/spec.md:6` | R4 | empirical premise | whether the DB rejects expired "
         "rows | none | `%s` |\n")
OLD_DEMOTE = ("**[next-stage] · blocked** — spec.md:6 carries `(unverified)`: demote it to "
              "`(assumed-empirical: <risk>)`.")
NO_REMEDY = "**[next-stage] · blocked** — spec.md:6 carries `(unverified)`."
BLOCKED = ["track: spec", "status: blocked"]

# (name, want, shell before check, comment bodies, labels, journal)
SHAPES = [
    ("the table, action `measure`", "pass", None, [TABLE % "measure"], BLOCKED, []),
    ("the table, action `accept a bounded risk`", "pass",
     None, [TABLE % "accept a bounded risk"], BLOCKED, []),
    ("the table, action `correct the spec`", "pass",
     None, [TABLE % "correct the spec"], BLOCKED, []),
    ("the table, action `reword`", "pass", None, [TABLE % "reword"], BLOCKED, []),
    ("the old demote wording with none of the four actions — green before #256", "fail",
     None, [OLD_DEMOTE], BLOCKED, []),
    ("the claim named, no remedy", "fail", None, [NO_REMEDY], BLOCKED, []),
    ("no STOP comment", "fail", None, [], BLOCKED, []),
    ("the gate label left beside blocked", "fail",
     None, [TABLE % "measure"], BLOCKED + ["status: ready-for-dev"], []),
    ("a CR opened despite the STOP", "fail",
     None, [TABLE % "measure"], BLOCKED, [{"route": "pr-create", "write": True}]),
    ("a branch pushed despite the STOP", "fail",
     "git checkout -q -b feat/5 spec/5 && git push -q origin feat/5",
     [TABLE % "measure"], BLOCKED, []),
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
                    print("FAIL F5 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, comments, labels, journal)
            got = {0: "pass", 3: "invalid"}.get(p.returncode, "fail")
            ok = got == want
            print("%s F5 %s → %s%s" % ("PASS" if ok else "FAIL", name, want,
                                         "" if ok else " (got %s)\n%s" % (got, p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
