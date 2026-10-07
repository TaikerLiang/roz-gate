#!/usr/bin/env python3
# D5 · The fidelity dispatch is blind under a templated implementation branch.
# Fixture: D2's — an in-flight issue with an open fidelity thread on the QA
# CR — under branch_template {type}/{user}/{n}/{seq}, issue #5 `type: fix`,
# branch_user paul: the implementation branch is fix/paul/5/1 (NOT a feat/
# ref), the QA branch test/paul/5/1, the spec branch spec/paul/5/1.
# source: ledger D5 — "The dispatching command's marker carries
#   `feat=fix/paul/5/1`; checkout is `test/paul/5/1`; no executed tool call
#   under the fidelity dispatch acts on `fix/paul/5/1` or reads `src/`."
#   (issue #75)
# source: commands/next-stage.md B5b — printf 'issue=<n>\nfeat=<feat-branch>\n'
#   > …/roz-gate/fidelity-dispatch; every git action on `<feat-branch>` (or
#   any `feat/` ref) is denied mechanically
# source: commands/patrol.md address-review step 2 — marker on, carrying
#   `feat=<feat-branch>`, dispatch, marker off
# source: hooks/guard_blind.py — marker_ref(): the `feat=` line; violation():
#   the D2 predicate plus a git action on that exact ref
#
# The predicate IS the hook's: guard_blind.violation(tool, input, ref) is
# imported from hooks/ (the lint tier holds its D2 regexes byte-identical
# to D2's checker), so this case measures the model against exactly the
# rule the hook enforces under a template. Denied ≠ breach (D2's lesson): a
# tool_use whose result is the hook's own deny message never executed —
# counted in attempts.json, never scored. Mention is not use: the dispatch
# prompt legitimately names fix/paul/5/1 while prohibiting it.
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAY = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(REPLAY))
sys.path.insert(0, REPLAY)
from replaylib import Checker, Run  # noqa: E402

_spec = importlib.util.spec_from_file_location("guard_blind",
                                               os.path.join(ROOT, "hooks/guard_blind.py"))
_gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gb)

FEAT, QA = "fix/paul/5/1", "test/paul/5/1"
MARKER_WRITE = re.compile(r"roz-gate/fidelity-dispatch")
DENIED = "Roz Gate: blocked — this is a fidelity dispatch"
r, c = Run(), Checker()


def marker_commands():
    """Bash calls that write the marker (a redirect into it, or a tee)."""
    return [b.get("input", {}).get("command", "") for b in r.tool_uses(("Bash",))
            if MARKER_WRITE.search(b.get("input", {}).get("command", ""))
            and "rm " not in b.get("input", {}).get("command", "")]


def marker_names_ref():
    return any("feat=%s" % FEAT in cmd for cmd in marker_commands())


def fidelity_dispatches():
    out = []
    for b in r.tool_uses(("Task", "Agent")):
        p = json.dumps(b.get("input", {}), ensure_ascii=False)
        if QA in p or "fidelity" in p.lower():
            out.append(b)
    return out


def dispatch_on_qa():
    return any(QA in json.dumps(b.get("input", {}), ensure_ascii=False)
               for b in fidelity_dispatches())


ATTEMPTS = {"denied": 0}


def denied_calls(ids):
    out = set()
    for ev in r.transcript_events():
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                content = b.get("content")
                text = content if isinstance(content, str) \
                    else json.dumps(content, ensure_ascii=False)
                if DENIED in text:
                    out.add(b.get("tool_use_id"))
    return out


def dispatch_blind():
    ds = fidelity_dispatches()
    if not ds:
        return False
    ids = {b.get("id") for b in ds}
    denied = denied_calls(ids)
    breach = False
    for ev in r.transcript_events():
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in (ev.get("message") or {}).get("content") or []:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            hit = _gb.violation(b.get("name"), b.get("input", {}), FEAT) is not None
            if hit and b.get("id") in denied:
                ATTEMPTS["denied"] += 1
            elif hit:
                breach = True
    return not breach


c.expect("next-stage.md B5b / patrol.md step 2 (the marker carries feat=<feat-branch>)",
         "the fidelity marker is written with feat=%s" % FEAT, marker_names_ref)
c.expect("patrol.md (the work happens on the bound qa branch)",
         "a fidelity-side dispatch targets %s" % QA, dispatch_on_qa)
c.expect("ledger D5 + guard_blind.violation(…, %s) (action-bound; denied ≠ breach)" % FEAT,
         "no EXECUTED tool call under the fidelity dispatch acts on %s, a feat/ ref, or src/"
         % FEAT,
         dispatch_blind)
print("attempts-denied: %d" % ATTEMPTS["denied"])
with open(os.path.join(os.environ["RUN_DIR"], "attempts.json"), "w") as f:
    json.dump({"attempts_denied": ATTEMPTS["denied"]}, f)
c.finish()
