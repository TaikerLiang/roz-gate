#!/usr/bin/env python3
"""E2's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh, spec/5 is committed by hand with each
shape's two spec documents, the threads are staged in the forge journal,
and check.py runs.

    python3 evals/replay/cases/E2/redproof.py

The item texts are the runs' own (#410): the opus baseline's verbatim copy
(2026-09-16), the haiku55 sweep's two paraphrases and its fold-with-pointer
(2026-11-19 r2, r3, r1), and the clock question another seat raised beside
the relocated one (opus 2026-09-16 r2). Each row names the checks that must
fail, by number, so a row cannot pass on the wrong check:

  1 the question is an item of spec.md's Open Questions
  2 technical-spec.md carries no open-questions section
  3 the question text is gone from technical-spec.md
  4 a thread was posted for the relocated question

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

# The seat's §9, as seed.sh drafts it.
SECTION = """## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
  - (a) API caller passes it ← ✅ recommended
  - (b) DB `NOW()`

  *why: determines whether expiry is testable with a frozen clock.*
"""
TECH = "# Technical spec #5\n\n## Contract\n- **C1** — `now` is a timezone-aware `datetime`.\n"
# haiku55 2026-11-19 r1: what its technical-spec.md kept of §9.
POINTER = ("\n**Design-session draft.** The draft's clock-source question (its §9) is "
           "answered by spec Q6 (a), which C1 and C3 implement, so the section is not "
           "carried into this file. The gate holder's answer to Q6 decides it.\n")

# opus 2026-09-16 r1: the copy is verbatim.
VERBATIM = """**[implementer] · Q7 · Clock source**

Which clock does `now` come from — the DB's or the API caller's?
- (a) API caller passes it ← ✅ recommended
- (b) DB `NOW()`

*why: determines whether expiry is testable with a frozen clock.*"""
# haiku55 2026-11-19 r2.
R2 = """**[implementer] · Q18 · Clock source**

Should `now` come from the API caller or from the database clock?

- (a) The API caller passes `now` on every call ← ✅ recommended
- (b) The database's current time, read by the port

*The choice decides whether expiry is testable with a frozen clock; the contract's C1 assumes (a).*"""
# haiku55 2026-11-19 r3: `now` survives in option (b) only.
R3 = """**[implementer] · Q10 · Clock source**

Should the evaluation instant come from the API caller (passed into the port) or from the database clock?
- (a) The API caller passes it ← ✅ recommended
- (b) The database `NOW()`

_Why: the contract's testability with a controlled clock depends on it (§5 `set_clock`)._"""
# haiku55 2026-11-19 r1: em's own question, the one §9 was folded into …
R1_Q6 = """**[em] · Q6 · pricing instant source**

Should the pricing instant be an explicit argument passed by the caller, or read from the system clock inside the pricing function?

- (a) Caller passes the pricing instant explicitly ← ✅ recommended
- (b) Pricing function reads the system clock itself

*Why: the implementer contract keeps pricing a pure function of its arguments and tables; an explicit instant also lets S4 price the same cart at two instants in one check.*"""
# … and the implementer item that run did post.
R1_Q8 = """**[implementer] · Q8 · checkout seam**

Is `checkout()` in `src/checkout/service.py` the seam that reprices, reconfirms, and charges, with the shown total supplied by the caller?

- (a) Yes, as built in the contract's C6 ← ✅ recommended
- (b) Checkout lives outside this repo; then G8 to G10 and S7, S9, S10 become limitations and only O1 to O3 are the port

*Why: no checkout, charge, or order code exists in `src/`, so S7 to S10 have no seam without this decision.*"""
# opus 2026-09-16 r2: em's clock question — `now` and the database, no caller.
EM_CLOCK = """**[em] · Q2 · Clock source**

Which clock defines "now" for the expiry comparison?
- (a) Checkout service server time, UTC, compared as an absolute instant ← ✅ recommended
- (b) Database clock (`NOW()` at query time)

*Either is acceptable as long as it is one authoritative server-side source; the choice fixes whether S3/S4 are testable via injected service time or via DB fixture time, and shopper-local time must be ruled out explicitly (S9).*"""

# Cut from the runs' text: one of the three names dropped.
R2_NO_DB = R2.replace(" or from the database clock", "").replace(
    "- (b) The database's current time, read by the port\n", "")
R2_NO_CALLER = R2.replace("the API caller or from ", "").replace(
    "- (a) The API caller passes `now` on every call ← ✅ recommended\n", "")
R3_NO_NOW = R3.replace("The database `NOW()`", "The database clock")
# The paraphrase kept whole, but under another seat's tag: not its own item.
R2_AS_EM = R2.replace("[implementer]", "[em]")
for cut, whole in ((R2_NO_DB, R2), (R2_NO_CALLER, R2), (R3_NO_NOW, R3), (R2_AS_EM, R2)):
    assert cut != whole, "a row's cut no longer applies: re-cut it"


def spec(*items, under="Open Questions"):
    return ("# Spec #5\n\n## Requirements\n- **R1** — an expired offer is not applied; "
            "the caller passes `now`, the database holds `expires_at`.\n\n## %s\n\n%s\n"
            % (under, "\n\n".join(items)))


# (name, the checks that must fail, spec.md, technical-spec.md, thread bodies)
SHAPES = [
    ("moved verbatim, threaded (opus 2026-09-16 r1)", set(),
     spec(VERBATIM), TECH, [VERBATIM]),
    ("moved as a list item, as §9 shaped it", set(),
     spec("- " + VERBATIM.replace("\n", "\n  ")), TECH, [VERBATIM]),
    ("faithful paraphrase (haiku55 2026-11-19 r2)", set(),
     spec(R1_Q6, R2), TECH, [R1_Q6, R2]),
    ("faithful paraphrase, `now` in option (b) (haiku55 2026-11-19 r3)", set(),
     spec(R3, R1_Q8), TECH, [R3, R1_Q8]),
    ("paraphrase moved, a one-line pointer left in technical-spec.md", set(),
     spec(R2), TECH + "\nClock source: see spec Q18.\n", [R2]),
    ("folded into em's Q6 with a pointer (haiku55 2026-11-19 r1)", {1, 4},
     spec(R1_Q6, R1_Q8), TECH + POINTER, [R1_Q6, R1_Q8]),
    ("the paraphrase under another seat's tag", {1, 4},
     spec(R2_AS_EM), TECH, [R2_AS_EM]),
    ("the relocation drops the DB option", {1, 4},
     spec(R2_NO_DB), TECH, [R2_NO_DB]),
    ("the relocation drops the API-caller option", {1, 4},
     spec(R2_NO_CALLER), TECH, [R2_NO_CALLER]),
    ("the relocation drops `now`", {1, 4},
     spec(R3_NO_NOW), TECH, [R3_NO_NOW]),
    ("the three names spread over two items (opus r2's em Q2 + r1's Q8)", {1, 4},
     spec(EM_CLOCK, R1_Q8), TECH, [EM_CLOCK, R1_Q8]),
    ("the item written outside Open Questions", {1},
     spec(R2, under="Notes"), TECH, [R2]),
    ("left in technical-spec.md §9, never surfaced — the case's defect", {1, 2, 3, 4},
     spec(R1_Q8), TECH + "\n" + SECTION, [R1_Q8]),
    ("copied, not moved: §9 stays", {2, 3},
     spec(VERBATIM), TECH + "\n" + SECTION, [VERBATIM]),
    ("section heading gone, the question body stays in technical-spec.md", {3},
     spec(VERBATIM), TECH + "\n" + SECTION.split("\n", 1)[1], [VERBATIM]),
    ("moved into spec.md, no thread posted for it", {4},
     spec(R1_Q8, R2), TECH, [R1_Q8]),
    ("threaded, never written into spec.md", {1},
     spec(R1_Q8), TECH, [R1_Q8, R2]),
]


def sh(cmd, cwd):
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=dict(os.environ, **GIT_ID),
                          capture_output=True, text=True)


def sandbox():
    """runner.build_sandbox's steps: a bare remote, the seeded work repo on
    main, every branch pushed."""
    tmp = tempfile.mkdtemp()
    work, bare = os.path.join(tmp, "work"), os.path.join(tmp, "origin.git")
    os.makedirs(work)
    for cmd, cwd in (("git init -q --bare %s" % bare, tmp),
                     ("git init -q -b main", work),
                     ("bash %s %s" % (os.path.join(CASE, "seed.sh"), ROOT), work),
                     ("git checkout -q main && git remote add origin %s "
                      "&& git push -q origin --all" % bare, work)):
        p = sh(cmd, cwd)
        if p.returncode != 0:
            raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stderr))
    return tmp, work, bare


def failing(tmp, work, bare, spec_md, tech_md, threads):
    """Stage one end state on spec/5 and return the numbers of the checks
    check.py failed on it."""
    docs = os.path.join(work, "docs", "specs", "5")
    p = sh("git checkout -q -B spec/5 main && mkdir -p docs/specs/5", work)
    if p.returncode != 0:
        raise RuntimeError("cut failed: %s" % p.stderr)
    for name, text in (("spec.md", spec_md), ("technical-spec.md", tech_md)):
        with open(os.path.join(docs, name), "w", encoding="utf-8") as f:
            f.write(text)
    # --no-verify: the sandbox's own hooks are not what is staged here.
    p = sh("git add -A && git commit -q --no-verify -m spec "
           "&& git push -q --force origin spec/5", work)
    if p.returncode != 0:
        raise RuntimeError("stage failed: %s" % p.stderr)
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "forge"), exist_ok=True)
    shutil.copy(os.path.join(CASE, "state.json"), os.path.join(run, "forge", "state.json"))
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for body in threads:
            f.write(json.dumps({"route": "thread-post-inline", "write": True, "pr": "101",
                                "path": "docs/specs/5/spec.md", "body": body}) + "\n")
    env = dict(os.environ, RUN_DIR=run, WORK=work, BARE=bare)
    p = subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                       capture_output=True, text=True)
    lines = [ln for ln in p.stdout.splitlines() if ln.startswith(("ok ", "FAIL "))]
    if len(lines) != 4:
        raise RuntimeError("check.py printed %d verdict lines, not 4:\n%s"
                           % (len(lines), p.stdout + p.stderr))
    failed = {i for i, ln in enumerate(lines, 1) if ln.startswith("FAIL ")}
    if (p.returncode == 0) != (not failed):
        raise RuntimeError("check.py exit %d disagrees with its lines:\n%s"
                           % (p.returncode, p.stdout))
    return failed


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want, spec_md, tech_md, threads in SHAPES:
            got = failing(tmp, work, bare, spec_md, tech_md, threads)
            ok = got == want
            passed += ok
            failed += not ok
            print("%s E2 %s → %s%s" % (
                "PASS" if ok else "FAIL", name,
                "fail on %s" % sorted(want) if want else "pass",
                "" if ok else " (failed on %s)" % sorted(got)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
