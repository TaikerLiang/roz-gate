#!/usr/bin/env python3
"""F15's red-proof: check.py scores staged passes correctly. No model — each
shape is a forge state + journal and a transcript (the scanner dispatch, the
final report). The checker reads no git, so no sandbox is seeded for the
shapes. One more row seeds the case's repo: #12 is scored as the pass's
actionable row, so the seed must hold what the closed #8 delivered (#367).

    python3 evals/replay/cases/F15/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CASE))))
GIT_ID = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
          "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}

TABLE = [
    "| issue | state | this pass | needs you |",
    "|---|---|---|---|",
    "| #10 Refund via payment provider | fast · ready-for-dev | waits on #9 | — |",
    "| #11 Partial refund reporting | fast · ready-for-dev | waits on #9 | — |",
    "| #12 Order history export | spec · ready-for-spec | acted: next-stage — spec CR #101 opened"
    " | yes |",
    "| #13 Refund audit trail | fast · ready-for-dev | waits on: blockers unknown | yes |",
]
FILTER = "inbox filter: label discuss · 2 track-less issues not in the inbox filter"
QUEUE = [
    "Your queue:",
    "- #12 — answer the spec threads — https://github.com/acme/demo/pull/101",
    "- #13 — fix the dependency lookup — HTTP 403 — https://github.com/acme/demo/issues/13",
]
READS = [{"route": "issue-list", "write": False, "state": "open"},
         {"route": "label-events", "write": False, "issue": "10"},
         {"route": "issue-blocked-by", "write": False, "issue": "10"},
         {"route": "issue-blocked-by", "write": False, "issue": "11"},
         {"route": "issue-blocked-by", "write": False, "issue": "12"},
         {"route": "http-403", "write": False,
          "target": "repos/acme/demo/issues/13/dependencies/blocked_by"}]
LOCK12 = {"route": "issue-edit", "write": True, "issue": "12", "add": ["status: processing"],
          "remove": [], "body_edit": False}
GOOD = READS + [LOCK12]
# run-1 (#366): the pass took #12's STOP itself — base lacks the closed #8's code
STOP12 = [{"route": "issue-edit", "write": True, "issue": "12", "add": ["status: blocked"],
           "remove": ["status: processing", "status: ready-for-spec"], "body_edit": False},
          {"route": "issue-comment", "write": True, "issue": "12",
           "body": "**[next-stage] · blocked** — the base lacks a dependency"}]
ROW12_BLOCKED = "blocked: base lacks a dependency | yes |"


def lock(n):
    return dict(LOCK12, issue=n)


def report(table=TABLE, filt=FILTER, queue=QUEUE):
    return "Patrol pass report\n\n" + "\n".join(list(table) + [filt, ""] + list(queue)) + "\n"


def swap(rows, old, new):
    out = [ln.replace(old, new) for ln in rows]
    assert out != list(rows), old
    return out


def drop(rows, prefix):
    out = [ln for ln in rows if not ln.startswith(prefix)]
    assert out != list(rows), prefix
    return out


def tool_use(name, inp, uid):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": name, "input": inp}]}}


def tool_result(uid, text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "content": text}]}}


def transcript(text, dispatch=True):
    ev = []
    if dispatch:
        ev.append(tool_use("Task", {"prompt": "…${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md…",
                                    "subagent_type": "general-purpose"}, "t_scan"))
        ev.append(tool_result("t_scan", "| issue | … |"))
    ev.append({"type": "result", "result": text})
    return ev


R10 = "| #10 Refund via payment provider | fast · ready-for-dev | waits on #9 | — |"
R11 = "| #11 Partial refund reporting | fast · ready-for-dev | waits on #9 | — |"
R13 = "| #13 Refund audit trail | fast · ready-for-dev | waits on: blockers unknown | yes |"

SHAPES = [
    ("the good pass: #10/#11 wait on #9, #12 acted, #13 unknown and queued", True, {}),
    ("the good pass, #12 queued instead of acted (N exhausted)", True,
     {"journal": READS, "text": report(table=swap(
         TABLE, "acted: next-stage — spec CR #101 opened | yes |",
         "queued: next-stage · ready-for-spec 17d | — |"), queue=QUEUE[:1] + QUEUE[2:])}),
    ("#12 reads `blocked: <the STOP comment's title>` — the pass itself STOPped it (run-1, #366)",
     True, {"journal": GOOD + STOP12, "labels": {"12": ["track: spec", "status: blocked"]},
            "text": report(table=swap(TABLE, "acted: next-stage — spec CR #101 opened | yes |",
                                      ROW12_BLOCKED))}),
    ("#12 reads `blocked:` but the pass never STOPped it (#366)", False,
     {"text": report(table=swap(TABLE, "acted: next-stage — spec CR #101 opened | yes |",
                                ROW12_BLOCKED))}),
    ("#10 dispatched over its open blocker (lock taken)", False,
     {"journal": READS + [lock("10")]}),
    ("#13's failed lookup read as no blockers (lock taken)", False,
     {"journal": READS + [lock("13")]}),
    ("#11's labels changed with no journaled write", False,
     {"labels": {"11": ["track: fast"]}}),
    ("#10 reads queued: next-stage", False,
     {"text": report(table=swap(TABLE, R10, R10.replace(
         "waits on #9 | — |", "queued: next-stage · ready-for-dev 19d | — |")))}),
    ("#10 reads `blocked: #9` (the status: blocked word)", False,
     {"text": report(table=swap(TABLE, R10, R10.replace("waits on #9", "blocked: #9")))}),
    ("#10 needs you: yes", False,
     {"text": report(table=swap(TABLE, R10, R10.replace("| — |", "| yes |")))}),
    ("#10 a queue item", False,
     {"text": report(queue=QUEUE + ["- #10 — wait for #9 — https://github.com/acme/demo/issues/10"])}),
    ("#11's clause names the closed #8", False,
     {"text": report(table=swap(TABLE, R11, R11.replace("waits on #9", "waits on #8, #9")))}),
    ("#12 reads as a wait (the closed #8 still counted)", False,
     {"text": report(table=swap(TABLE, "acted: next-stage — spec CR #101 opened | yes |",
                                "waits on #8 | — |"))}),
    ("#13 reads queued: next-stage (unknown read as none)", False,
     {"text": report(table=swap(TABLE, R13, R13.replace(
         "waits on: blockers unknown | yes |", "queued: next-stage · ready-for-dev 16d | — |")),
         queue=QUEUE[:2])}),
    ("#13 unknown but needs you —", False,
     {"text": report(table=swap(TABLE, R13, R13.replace("| yes |", "| — |")))}),
    ("#13 absent from the queue", False, {"text": report(queue=QUEUE[:2])}),
    ("#13's queue item without its link", False,
     {"text": report(queue=swap(QUEUE, " — https://github.com/acme/demo/issues/13", ""))}),
    ("#12's blockers never read", False,
     {"journal": [e for e in GOOD if not (e["route"] == "issue-blocked-by"
                                         and e.get("issue") == "12")]}),
    ("#13's lookup never attempted", False,
     {"journal": [e for e in GOOD if e["route"] != "http-403"]}),
    ("no scanner dispatched", False, {"dispatch": False}),
    ("the report has no table", False,
     {"text": "Patrol pass report\n\n#10 and #11 wait on #9.\n"}),
]


def run_check(tmp, *, text=None, journal=None, labels=None, dispatch=True):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    for n, lab in (labels or {}).items():
        st["issues"][n]["labels"] = lab
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in (GOOD if journal is None else journal):
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(report() if text is None else text, dispatch):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def seed_holds_eight():
    """#12 Order history export is blocked only by the closed #8 Order ledger
    schema: the seeded main must hold the ledger #8 delivered, or a seat
    rightly STOPs #12 on a missing dependency (#213) and the closed blocker
    released nothing (#367)."""
    work = tempfile.mkdtemp()
    try:
        env = dict(os.environ, **GIT_ID)
        for cmd in ("git init -q -b main", "bash %s %s" % (os.path.join(CASE, "seed.sh"), ROOT)):
            if subprocess.run(["bash", "-c", cmd], cwd=work, env=env,
                              capture_output=True).returncode != 0:
                return False
        p = subprocess.run(["git", "show", "main:src/orders/ledger.py"], cwd=work,
                           capture_output=True, text=True)
        return p.returncode == 0 and re.search(r"^COLUMNS = .*order_id", p.stdout, re.M) is not None
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    passed = failed = 0
    ok = seed_holds_eight()
    print("%s F15 the seed holds #8's order ledger schema on main (#12 is doable) → pass"
          % ("PASS" if ok else "FAIL"))
    passed, failed = passed + ok, failed + (not ok)
    tmp = tempfile.mkdtemp()
    try:
        for name, want_pass, kw in SHAPES:
            p = run_check(tmp, **kw)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F15 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
