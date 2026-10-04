#!/usr/bin/env python3
"""E6's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh; each shape stages what a session left on
the remote (commits on spec/5) and in the forge (journal, labels); check.py
runs.

    python3 evals/replay/cases/E6/redproof.py

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
FOLD_SPEC = ("git checkout -q spec/5 && printf -- '- **R5 · Re-check at checkout** (from A1) "
             "— an offer that expires while the cart is open is re-checked at checkout.\\n' "
             ">> docs/specs/5/spec.md "
             "&& git commit -qam 'spec: A1 folded' && git push -q origin spec/5")
FOLD_TECH = ("git checkout -q spec/5 && printf -- '- re-check at checkout\\n' "
             ">> docs/specs/5/technical-spec.md "
             "&& git commit -qam 'tech: A1' && git push -q origin spec/5")
REPLY = {"route": "thread-reply", "write": True, "pr": "101", "base": 9020,
         "body": "✅ [product] amended — R5 and S2 added, folded into spec.md."}
RESOLVE = {"route": "thread-resolve", "write": True, "thread": "T7"}

# (name, should pass, shell before check, journal entries, processing left)
SHAPES = [
    ("folded into spec.md, amended reply, resolved", True, FOLD_SPEC, [REPLY, RESOLVE], False),
    ("skipped: nothing pushed, nothing replied", False, None, [], False),
    ("resolved without a fold", False, None, [REPLY, RESOLVE], False),
    ("folded into the wrong document (technical-spec.md)", False, FOLD_TECH,
     [REPLY, RESOLVE], False),
    ("folded and resolved but the reply lacks the ✅ marker", False, FOLD_SPEC,
     [{**REPLY, "body": "amended, folded into spec.md"}, RESOLVE], False),
    ("folded and replied, thread left open", False, FOLD_SPEC, [REPLY], False),
    ("done, but the lock was left on", False, FOLD_SPEC, [REPLY, RESOLVE], True),
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


def check(tmp, bare, journal, processing):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if processing:
        st["issues"]["5"]["labels"].append("status: processing")
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
    for name, want_pass, before, journal, processing in SHAPES:
        tmp, work, bare = sandbox()
        try:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    print("FAIL E6 %s — setup failed\n  %s" % (name, setup.stderr.strip()[-300:]))
                    failed += 1
                    continue
            p = check(tmp, bare, journal, processing)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s E6 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
