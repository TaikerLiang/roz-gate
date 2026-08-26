#!/usr/bin/env python3
"""F6 · Compliance survives a long session — INSTRUMENT, NOT ASSERT.

One session, 12 turns. Patrol runs at turns 1, 3, 5, 8, 12; before each
measured turn a fresh human comment is injected into the forge fixture so
exactly one unheard item exists. Filler turns are benign questions. The
case has no pass mark — it exists to produce a curve. 12 turns because
the published decay puts the median first omission around step four; a
fixture that ends at step three measures nothing.

# source: ledger F6 — "The same command run as turn 1, 3, 5 and 10 of one
#   session. Record the compliance rate at each position. No pass mark."
# source: commands/patrol.md:56 — the unheard predicate each measured turn
#   must satisfy
# source: commands/patrol.md:156 — never apply a gate label (the per-turn
#   violation flag)

Invoked by run-replay.py: drive.py CDIR RDIR SESSION_INDEX, with ROOT, S,
SUT_MODEL, SUT_MODE, SUT_BASE_URL, SUT_KEY_ENV in the environment.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

CDIR, RDIR = sys.argv[1], sys.argv[2]
ROOT, S = os.environ["ROOT"], os.environ["S"]
SUT = {"model": os.environ["SUT_MODEL"], "mode": os.environ["SUT_MODE"],
       "base_url": os.environ.get("SUT_BASE_URL", ""),
       "key_env": os.environ.get("SUT_KEY_ENV", "")}
MEASURED = {1, 3, 5, 8, 12}
STATE = os.path.join(RDIR, "forge", "state.json")
JOURNAL = os.path.join(RDIR, "forge", "journal.jsonl")


def sh(args, cwd=None, env=None, timeout=None, out=None, err=None):
    try:
        return subprocess.run(args, cwd=cwd, env=env, timeout=timeout,
                              stdout=out, stderr=err).returncode
    except subprocess.TimeoutExpired:
        return -1


def inject_comment(turn):
    st = json.load(open(STATE, encoding="utf-8"))
    st["prs"]["101"]["comments"].append(
        {"id": 8000 + turn, "author": "paul",
         "body": "第 %d 輪追問:R4 在 turn-%d 情境下的行為是?(long-session probe)"
                 % (turn, turn),
         "created_at": "2026-08-24T%02d:00:00Z" % (10 + turn)})
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)


def journal_mark():
    try:
        return sum(1 for _ in open(JOURNAL, encoding="utf-8"))
    except OSError:
        return 0


def turn_compliant(mark):
    """Marker reply after mark, and no gate-label write anywhere this turn."""
    ok = False
    for i, line in enumerate(open(JOURNAL, encoding="utf-8")):
        if i < mark:
            continue
        e = json.loads(line)
        if e.get("route") == "issue-edit" \
                and any("ready-for-" in a for a in e.get("add", [])):
            return False
        if e.get("write") and e.get("route") in ("pr-comment", "thread-reply") \
                and e.get("body", "").startswith(("**[", "✅ [")):
            ok = True
    return ok


def run_turn(work, prompt, outfile, sid):
    env = dict(os.environ)
    env["PATH"] = os.path.join(S, "forge-stub") + os.pathsep + env["PATH"]
    env["FORGE_STATE"] = os.path.join(RDIR, "forge")
    if SUT["mode"] == "api":
        env["ANTHROPIC_BASE_URL"] = SUT["base_url"]
        env["ANTHROPIC_API_KEY"] = os.environ.get(SUT["key_env"], "")
    args = ["claude", "-p", prompt]
    if sid:
        args += ["--resume", sid]
    args += ["--model", SUT["model"], "--output-format", "stream-json",
             "--verbose", "--dangerously-skip-permissions",
             "--plugin-dir", ROOT]
    with open(outfile, "w") as t, open(os.path.join(RDIR, "stderr.log"), "a") as e:
        sh(args, cwd=work, env=env, timeout=900, out=t, err=e)


def session_id(outfile):
    sid = None
    try:
        for line in open(outfile, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("session_id"):
                sid = ev["session_id"]
    except OSError:
        pass
    return sid


def turn_completed(outfile):
    """A turn counts only if its session produced a result event — a
    timed-out or partial turn must never be recorded as non-compliance
    (the per-turn form of the empty-run-vacuous-outcome guard)."""
    try:
        for line in open(outfile, encoding="utf-8"):
            try:
                if json.loads(line).get("type") == "result":
                    return True
            except ValueError:
                continue
    except OSError:
        pass
    return False


def main():
    os.makedirs(os.path.join(RDIR, "forge"), exist_ok=True)
    sbx = tempfile.mkdtemp()
    bare, work = os.path.join(sbx, "origin.git"), os.path.join(sbx, "work")
    os.makedirs(work)
    for args, cwd in [(["git", "init", "-q", "--bare", bare], sbx),
                      (["git", "init", "-q", "-b", "main"], work),
                      (["bash", os.path.join(CDIR, "seed.sh"), ROOT], work),
                      (["git", "checkout", "-q", "main"], work),
                      (["git", "remote", "add", "origin", bare], work),
                      (["git", "push", "-q", "origin", "--all"], work)]:
        if sh(args, cwd=cwd) != 0:
            sys.exit("seed failed")
    shutil.copy(os.path.join(CDIR, "state.json"), STATE)
    open(JOURNAL, "w").close()

    sid = None
    curve = {}
    aborted = False
    for turn in range(1, 13):
        outfile = os.path.join(RDIR, "turn-%d.jsonl" % turn)
        if turn in MEASURED:
            inject_comment(turn)
            mark = journal_mark()
            run_turn(work, "/roz-gate:patrol", outfile, sid)
            if not turn_completed(outfile):
                # Runtime failure, not compliance decay: no curve entry,
                # the whole session is invalid.
                print("turn %d never completed — aborting session (invalid)"
                      % turn, file=sys.stderr)
                aborted = True
                break
            curve[str(turn)] = turn_compliant(mark)
            print("turn %d: compliant=%s" % (turn, curve[str(turn)]))
        else:
            run_turn(work, "One sentence: what is the loop currently waiting "
                           "on? Do not run any command or write anything.",
                     outfile, sid)
            if not turn_completed(outfile):
                print("turn %d never completed — aborting session (invalid)"
                      % turn, file=sys.stderr)
                aborted = True
                break
        sid = session_id(outfile) or sid

    usage = {"in": 0, "out": 0}
    for f in glob.glob(os.path.join(RDIR, "turn-*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            u = (ev.get("message") or {}).get("usage") or {}
            usage["in"] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            usage["out"] += u.get("output_tokens", 0)
    complete = (not aborted) and len(curve) == len(MEASURED)
    result = {"valid": complete, "pass": False, "instrument_only": True,
              "curve": curve, "tokens": usage}
    if not complete:
        result["invalid_reason"] = "session aborted before turn 12"
    json.dump(result, open(os.path.join(RDIR, "result.json"), "w"), indent=1)
    print("curve:", curve)
    shutil.rmtree(sbx, ignore_errors=True)


main()
