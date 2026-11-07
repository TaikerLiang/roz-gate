#!/usr/bin/env python3
"""E11's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh; each shape stages what a session left on
the remote (commits on spec/5) and in the forge (journal, labels); check.py
runs.

    python3 evals/replay/cases/E11/redproof.py

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

Q6_RESOLVED = (
    "  **Resolved:** (b) honoured if valid when added (paul, 2026-08-23); *the shopper saw "
    "the offer when they added the line*; folded into R4, R5.\n")
Q7_DEFERRED = (
    "- **[implementer] · Q7 · when a line was added · deferred**\n\n"
    "  R5 needs the moment a line was added; C1's `CartLine` carries no timestamp — is it\n"
    "  - (a) `added_at` on `CartLine` ← ✅ recommended\n"
    "  - (b) the cart's `created_at`, one time for every line\n\n"
    "  *why: (b) honours an offer that was already expired when the line was added.*\n"
    "  *deferred — raised at depth 2 by the fold of Q6; resolves to its recommendation at "
    "`ready-for-dev` unless you answer it on the CR*\n")
Q7_OPEN = Q7_DEFERRED.replace(" · deferred**", "**").replace(
    "  *deferred — raised at depth 2 by the fold of Q6; resolves to its recommendation at "
    "`ready-for-dev` unless you answer it on the CR*\n", "  *raised by the fold of Q6*\n")
Q7_UNMARKED = Q7_DEFERRED.replace(" · deferred**", "**")


def fold(q7=Q7_DEFERRED):
    """The fold's commit on spec/5: R5 added, Q6 resolved, Q7 appended (or not)."""
    spec = ("python3 - <<'PY'\n"
            "import re\n"
            "p = 'docs/specs/5/spec.md'; s = open(p).read()\n"
            "s = s.replace('## Scenarios', '- **R5 · Valid when added** (from Q6) — an offer "
            "valid when its line was added stays applied to that line at checkout.\\n\\n"
            "## Scenarios')\n"
            "s = s.replace('  *raised by the fold of Q3*\\n', '  *raised by the fold of Q3*\\n'"
            " + %r)\n"
            "s = s.rstrip('\\n') + '\\n' + %r\n"
            "open(p, 'w').write(s)\n"
            "PY\n") % (Q6_RESOLVED, q7)
    return ("set -e; git checkout -q spec/5\n" + spec +
            "git commit -qam 'spec: Q6 folded' && git push -q origin spec/5")


READ = {"route": "threads-list", "pr": "101"}
REPLY = {"route": "thread-reply", "write": True, "pr": "101", "base": 9101,
         "body": "✅ [product] resolved — (b), folded into spec.md (R5)."}
RESOLVE = {"route": "thread-resolve", "write": True, "pr": "101", "thread": "T1"}
DEFERRED = {"route": "pr-comment", "write": True, "pr": "101",
            "body": "**[spec-answers] · deferred**\n\n- Q7 · when a line was added — "
                    "recommended (a) `added_at` on `CartLine`; stands at `ready-for-dev` "
                    "unless you answer it here."}
NEW_THREAD = {"route": "thread-post-inline", "write": True, "pr": "101",
              "body": "**[implementer] · Q7 · when a line was added**"}
GOOD = [READ, REPLY, RESOLVE, DEFERRED]
IN_REVIEW = ["track: spec", "status: in-spec-review"]

# (name, want: "pass" | "fail" | "invalid", shell before check, journal, labels)
SHAPES = [
    ("Q6 folded and resolved; Q7 deferred, no thread, one deferred comment", "pass",
     fold(), GOOD, IN_REVIEW),
    ("the fold raised nothing — the rule was never exercised", "invalid",
     fold(q7=""), [READ, REPLY, RESOLVE], IN_REVIEW),
    ("Q7 posted as a thread (depth 2 asked) — the ask-once rule broken", "fail",
     fold(q7=Q7_OPEN), [READ, REPLY, RESOLVE, NEW_THREAD], IN_REVIEW),
    ("Q7 in the spec without the `· deferred` mark", "fail",
     fold(q7=Q7_UNMARKED), GOOD, IN_REVIEW),
    ("Q7 deferred but no `**[spec-answers] · deferred**` comment", "fail",
     fold(), [READ, REPLY, RESOLVE], IN_REVIEW),
    ("deferred comment posted but Q7 never written to the spec", "fail",
     fold(q7=""), GOOD, IN_REVIEW),
    ("Q7 deferred, but Q6's thread was never resolved", "fail",
     fold(), [READ, REPLY, DEFERRED], IN_REVIEW),
    ("everything right but the lock left on", "fail",
     fold(), GOOD, IN_REVIEW + ["status: processing"]),
    ("a STOP instead of the fold", "fail", None, [READ],
     ["track: spec", "status: blocked"]),
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
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for name, want, before, journal, labels in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL E11 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, journal, labels)
            got = {0: "pass", 3: "invalid"}.get(p.returncode, "fail")
            ok = got == want
            print("%s E11 %s → %s%s" % ("PASS" if ok else "FAIL", name, want,
                                         "" if ok else " (got %s)\n%s" % (got, p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
