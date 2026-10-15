#!/usr/bin/env python3
"""F11's red-proof: check.py scores staged reports correctly. No model, no
sandbox — the checker reads the pass's final text, so each shape is a
transcript whose result event carries one report, over the case's state.

    python3 evals/replay/cases/F11/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))

TABLE = [
    "| issue | state | this pass | needs you |",
    "|---|---|---|---|",
    "| #5 Offer expiry enforcement | spec · in-user-review "
    "| acted: review-answers — answered the checkout-time question | yes |",
    "| #6 Bump the HTTP client to 3.2 | fast · ready-for-dev | queued: next-stage | — |",
    "| #7 Gift cards | inbox | acted: intake — questions batch posted | yes |",
    "| #8 Grace period on expired offers | spec · in-spec-review "
    "| waits on you: Q1 on #102 | yes |",
    "| #9 Bundle offers | spec · blocked | blocked: next-stage — base branch missing | yes |",
    "| #10 Retry the webhook delivery | fast · blocked "
    "| blocked: next-stage — suite red on main | yes |",
]
FILTER = "inbox filter: discuss / none · 1 track-less issue not in the inbox filter"
QUEUE = [
    "Your queue:",
    "- #5 — review & merge — https://github.com/x/y/pull/101",
    "- #7 — answer the intake questions — https://github.com/x/y/issues/7#issuecomment-1",
    "- #8 — answer Q1 — https://github.com/x/y/pull/102",
    "- #9 — decide the STOP — https://github.com/x/y/issues/9#issuecomment-901",
    "- #10 — decide the STOP — https://github.com/x/y/issues/10#issuecomment-902",
]
DETAILS = ["## Details", "- #5: answered from spec.md R1; no seat dispatched."]


def report(table=TABLE, filt=FILTER, queue=QUEUE, details=DETAILS):
    parts = list(table) + ([filt] if filt else []) + [""] + list(queue)
    if details:
        parts += [""] + list(details)
    return "Patrol pass report\n\n" + "\n".join(parts) + "\n"


def swap(rows, old, new):
    out = [ln.replace(old, new) for ln in rows]
    assert out != list(rows), old
    return out


# The pasted shape of #124: key/value blocks, "same as previous pass", a
# queue without links, the flip-flop only under Details.
PASTED = "\n".join([
    "Patrol pass report", "",
    "  issue: #5 — Offer expiry enforcement",
    "  state: track: spec, in-user-review",
    "  action this pass / waits on: Acted: ran review-answers end to end.",
    "  issue: #6, #7, #8, #9, #10",
    "  state: unchanged",
    "  action this pass / waits on: same as previous pass",
    FILTER, "",
    "Your queue:",
    "  - #8 — answer Q1.",
    "  - #9/#10 — still blocked, unchanged.", "",
    "## Details",
    "- #9/#10 read back as plain blocked this scan (last pass: illegal state) — unexplained.",
])

SHAPES = [
    ("the good report", True, report()),
    ("the good report, Details omitted (empty)", True, report(details=())),
    ("the pasted shape: key/value blocks, no table", False, PASTED),
    ("#6's row leans on the previous pass", False,
     report(table=swap(TABLE, "queued: next-stage", "unchanged — same as previous pass"))),
    ("#9's queue item has no link", False,
     report(queue=swap(QUEUE, " — https://github.com/x/y/issues/9#issuecomment-901", ""))),
    ("#9 marked —, dropped from the queue, noted only under Details", False,
     report(table=swap(TABLE, "blocked: next-stage — base branch missing | yes |",
                       "blocked: next-stage — base branch missing | — |"),
            queue=[ln for ln in QUEUE if not ln.startswith("- #9")],
            details=DETAILS + ["- #9: blocked, nothing to do until the base exists."])),
    ("#10 missing from the table", False,
     report(table=[ln for ln in TABLE if not ln.startswith("| #10")],
            queue=[ln for ln in QUEUE if not ln.startswith("- #10")])),
    ("#5's `this pass` is a paragraph, not a clause", False,
     report(table=swap(TABLE, "answered the checkout-time question",
                       "answered the checkout-time question from spec.md R1, no seat "
                       "dispatched, the implementer fixed the duplicated-split nit "
                       "(commit a052316e) and the reviewer resolved all four threads"))),
    ("the filter line is missing", False, report(filt=None)),
    ("#9 marked yes but absent from the queue", False,
     report(queue=[ln for ln in QUEUE if not ln.startswith("- #9")])),
    ("the filtered-out #11 listed as a row", False,
     report(table=TABLE + ["| #11 Dark mode | inbox | — | — |"])),
    ("a queue line that is not an item", False,
     report(queue=QUEUE + ["- nothing further needed for #6"])),
    ("Details cites the last pass", False,
     report(details=DETAILS + ["- #9/#10 read as blocked; last pass said illegal state."])),
    ("a loop-level item: the workflow stamp is stale", True,
     report(queue=QUEUE + ["- loop — re-run /roz-gate:init — workflow stamp v3, plugin v4"])),
    ("#5 answered but marked —, dropped from the queue", False,
     report(table=swap(TABLE, "answered the checkout-time question | yes |",
                       "answered the checkout-time question | — |"),
            queue=[ln for ln in QUEUE if not ln.startswith("- #5")])),
    ("#7's batch posted but marked —, dropped from the queue", False,
     report(table=swap(TABLE, "questions batch posted | yes |", "questions batch posted | — |"),
            queue=[ln for ln in QUEUE if not ln.startswith("- #7")])),
    ("the pass never reached #5 or #7 — both — is right", True,
     report(table=swap(swap(TABLE,
                            "acted: review-answers — answered the checkout-time question | yes |",
                            "queued: review-answers | — |"),
                       "acted: intake — questions batch posted | yes |", "queued: intake | — |"),
            queue=[ln for ln in QUEUE if not ln.startswith(("- #5", "- #7"))]),
     {"acted5": False, "asked7": False}),
    ("a `this pass` cell outside the vocabulary", False,
     report(table=swap(TABLE, "queued: next-stage", "nothing happened today"))),
    ("#6 listed twice", False,
     report(table=TABLE + [TABLE[3]])),
    ("a row for an issue the scanner never listed (#12)", False,
     report(table=TABLE + ["| #12 Ghost | spec · in flight | in progress | — |"])),
]


def run_check(tmp, text, acted5=True, asked7=True):
    """The pass answered #5 (its lock in the journal) and posted #7's batch
    (the comment in the state) unless a shape says otherwise."""
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    if asked7:
        st["issues"]["7"]["comments"] = [{"id": 1, "author": "paul",
                                          "body": "**[intake]** 1. Expiry? (a) …"}]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        if acted5:
            f.write(json.dumps({"route": "issue-edit", "write": True, "issue": "5",
                                "add": ["status: processing"]}) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "result", "result": text}, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=tmp)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp = tempfile.mkdtemp()
    try:
        for name, want_pass, text, *kw in SHAPES:
            p = run_check(tmp, text, **(kw[0] if kw else {}))
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F11 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
