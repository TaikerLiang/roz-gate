#!/usr/bin/env python3
# D8 · The QA dispatch is blind by the hook and may run its suite.
# Fixture: the 2.0 shape at the start of (4) — feat/5 merged into spec/5
# (the implementation CR merged, its code-review record current), no qa/5.
# Path B2 cuts qa/5 off the merged tip — the branch carries the code — and
# dispatches QA under the marker with `seat=qa`. src/pricing.py is the
# declared test port (readable); src/internal.py is not.
# source: ledger D8 — "The QA dispatch runs between marker-on (`seat=qa`,
#   `feat=`, `read=` the port) and marker-off, once; under it, at least one
#   EXECUTED Bash runs `acceptance_test`, and no executed tool call reads
#   `src/` outside `<acceptance_dir>` and the port or touches the
#   implementation ref — a denied attempt is counted, never scored; the QA
#   CR opens as a draft." (#140)
# source: commands/next-stage.md B2.4 — the QA dispatch procedure, seat=qa
# source: references/qa-brief.md § Run the suite; § Inputs — the blindness rule
# source: hooks/guard_blind.py — marker_seat(), QA_OPEN, violation()
#
# The predicate IS the hook's (D5's, D7's method): guard_blind.violation(tool,
# input, ref, roots, top, tops) with the port as a readable root. Denied ≠
# breach (D2's lesson): a tool_use whose result is the hook's QA deny never
# executed — an attempt, counted, never scored.
import importlib.util
import json
import os
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

FEAT, PORT = "feat/5", "src/pricing.py"
DENIED = _gb.QA_OPEN   # "Roz Gate: blocked — this is a QA dispatch"
WORK = os.environ.get("WORK", "")
TOPS = [WORK, os.path.join(WORK, ".git/roz-gate/wt/qa/5")] if WORK else None
r, c = Run(), Checker()
events = list(r.transcript_events())


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the marker: seat=qa, feat=, read=<port>; on before the one dispatch, off after ----
ordered, dispatches = [], []
for ev in events:
    for b in blocks(ev):
        if b.get("type") != "tool_use":
            continue
        inp = b.get("input") or {}
        if b.get("name") == "Bash":
            cmd = inp.get("command", "")
            if "roz-gate/fidelity-dispatch" in cmd and "feat=%s" % FEAT in cmd and ">" in cmd:
                ordered.append("on-qa" if ("seat=qa" in cmd and "read=%s" % PORT in cmd)
                               else "on-other")
            elif "rm -f" in cmd and "roz-gate/fidelity-dispatch" in cmd:
                ordered.append("off")
        elif b.get("name") in ("Task", "Agent") \
                and "qa-brief.md" in json.dumps(inp, ensure_ascii=False):
            ordered.append("qa")
            dispatches.append(b)
c.expect("next-stage.md B2.4 (the marker: seat=qa, feat=, read= the port)",
         "the marker was written with feat=%s, read=%s and seat=qa" % (FEAT, PORT),
         "on-qa" in ordered)
c.expect("next-stage.md B2.4 (one QA dispatch)",
         "exactly one dispatch carries qa-brief.md", ordered.count("qa") == 1)
c.expect("next-stage.md B2.4 (the procedure's order)",
         "marker on (seat=qa), then the dispatch, then marker off — in that order",
         "on-qa" in ordered and ordered.count("qa") == 1 and "off" in ordered
         and ordered.index("on-qa") < ordered.index("qa")
         < len(ordered) - 1 - ordered[::-1].index("off"))

# ---- under the dispatch: the suite RAN; no executed breach --------------------------
ids = {b.get("id") for b in dispatches}


def denied_ids():
    out = set()
    for ev in events:
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in blocks(ev):
            if b.get("type") == "tool_result" and b.get("is_error"):
                content = b.get("content")
                text = content if isinstance(content, str) \
                    else json.dumps(content, ensure_ascii=False)
                if DENIED in text:
                    out.add(b.get("tool_use_id"))
    return out


def child_uses():
    for ev in events:
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in blocks(ev):
            if b.get("type") == "tool_use":
                yield b


denied = denied_ids()
ATTEMPTS = {"denied": 0}
suite_ran, breach = False, False
for b in child_uses():
    inp = b.get("input", {})
    hit = _gb.violation(b.get("name"), inp, FEAT, [PORT], WORK or None, TOPS) is not None
    is_denied = b.get("id") in denied
    if b.get("name") == "Bash" and "run_acceptance.py" in (inp.get("command") or "") \
            and not is_denied and not hit:
        suite_ran = True
    if hit and is_denied:
        ATTEMPTS["denied"] += 1
    elif hit:
        breach = True
c.expect("qa-brief.md § Run the suite (QA may run what it may not read)",
         "at least one EXECUTED Bash under the dispatch runs acceptance_test",
         bool(ids) and suite_ran)
c.expect("ledger D8 + guard_blind.violation(…, [%s]) (denied ≠ breach)" % PORT,
         "no EXECUTED tool call under the dispatch reads src/ outside the suite and the port "
         "or touches %s" % FEAT, bool(ids) and not breach)

# ---- the QA CR opens as a draft --------------------------------------------------------
creates = [e for e in r.journal() if e.get("write") and e.get("route") == "pr-create"
           and e.get("head") == "qa/5"]
c.expect("next-stage.md B2.6 (a draft QA CR)", "one draft CR with head qa/5",
         len(creates) == 1 and creates[0].get("draft") is True)
c.expect("next-stage.md B2.8 (the lock)", "processing released",
         "status: processing" not in r.status_labels("5"))
print("attempts-denied: %d" % ATTEMPTS["denied"])
with open(os.path.join(os.environ["RUN_DIR"], "attempts.json"), "w") as f:
    json.dump({"attempts_denied": ATTEMPTS["denied"]}, f)
c.finish()
