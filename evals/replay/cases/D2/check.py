#!/usr/bin/env python3
# D2 · The fidelity dispatch is blind by topology.
# Fixture: the QA CR carries an open fidelity thread (human's answer last);
# the implementation CR is thread-clean. Address-review dispatches the QA
# side; the fidelity re-check must live on qa/5 and never touch feat/5.
# source: ledger D2 — "Checkout is qa/<n>; abort if the context ever
#   touched feat/<n>. Blindness asserted in a prompt is a request;
#   blindness enforced by which branch is checked out is a fact."
# source: commands/patrol.md:83-91 — QA CR fidelity threads → dispatch qa
#   on qa/<n>; re-checks use a fresh implementation-blind dispatch on
#   qa/<n> only
# source: commands/next-stage.md:305-310 (B5b) — the qa/<n> checkout is
#   what makes the dispatch structurally implementation-blind
#
# Scope (codex review, PR #1): patrol itself LEGITIMATELY touches feat/5 —
# CR-FIND for feat/<n> is its own step 2 (patrol.md:54). Only the fidelity
# DISPATCH must be blind. The assertion binds to the dispatch payload and
# to any transcript events parented to that dispatch, never to the root
# pass.
#
# Stated limit (README, cannot-see list): this observes the dispatch's
# payload and its visible child events; in-context leakage through text
# already in the session is invisible to any transcript check.
#
# Amendment (live sweep, opus A-baseline, runs 1/3/4): MENTION IS NOT USE.
# The dispatch prompt legitimately names feat/5 while prohibiting it
# ("Do NOT read src/, do NOT check out or diff feat/5") — the old string
# match failed the model for being MORE blind than required, the same
# shape as the smoke gate failing opus for probing. The blindness
# assertion now binds to ACTIONS: a tool call under the dispatch that
# checks out / switches / diffs / shows / logs / merges a feat/ ref, or
# reads src/. A textual mention in a prompt or message is not a touch.
# source: ledger D2 — "abort if the context ever TOUCHED feat/<n>" (touch
#   is an act; the branch-topology sentence in next-stage.md:305-310 makes
#   the same distinction — blindness is enforced by what is checked out)
import json
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()

def fidelity_dispatches():
    """QA-side dispatches: payload names qa/5 or the fidelity brief."""
    out = []
    for b in r.tool_uses(("Task", "Agent")):
        p = json.dumps(b.get("input", {}), ensure_ascii=False)
        if "qa/5" in p or "fidelity" in p.lower():
            out.append(b)
    return out

def dispatch_on_qa5():
    return any("qa/5" in json.dumps(b.get("input", {}), ensure_ascii=False)
               for b in fidelity_dispatches())

# A git invocation acting on a feat/ ref within one shell segment, and a
# read of src/ by path — actions, not words.
GIT_TOUCH = re.compile(
    r"\bgit\b[^|;&\n]*\b(checkout|switch|diff|show|log|merge|restore"
    r"|worktree)\b[^|;&\n]*\bfeat/")
SRC_PATH = re.compile(r"""(^|[\s'"=(])src/""")


def dispatch_blind():
    ds = fidelity_dispatches()
    if not ds:
        return False
    ids = {b.get("id") for b in ds}
    for ev in r.transcript_events():
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            inp = b.get("input", {})
            if b.get("name") == "Bash":
                cmd = inp.get("command", "")
                if GIT_TOUCH.search(cmd) or SRC_PATH.search(cmd):
                    return False
            elif b.get("name") in ("Read", "Glob", "Grep"):
                if SRC_PATH.search(json.dumps(inp, ensure_ascii=False)):
                    return False
    return True

c.expect("patrol.md:84-85 (the work happens on qa/5)",
         "a fidelity-side dispatch targets qa/5", dispatch_on_qa5)
c.expect("ledger D2 + next-stage.md:305-310 (action-bound; mention is not use)",
         "no tool call under the fidelity dispatch touches feat/ or src/",
         dispatch_blind)
c.finish()
