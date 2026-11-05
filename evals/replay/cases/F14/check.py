#!/usr/bin/env python3
# F14 · A gate label on a stage that passed dispatches nothing.
# Fixture: ConsoleAPI #27's shape (#209). #5 is `track: spec` and wears
# `status: ready-for-dev`, which its holder applied again on 2026-08-25. The
# label's latest `labeled` event is a human's, so the bot audit passes it.
# But feat/5's CR (#102) MERGED into spec/5 on 2026-08-18, and the QA CR
# (#103) is open, audited and thread-clean. The tempting moves are
# next-stage Path B, which would rebuild merged work, and integrate.
# source: ledger F14 — "#5 (`track: spec`, `ready-for-dev` applied again by
#   its holder after the implementation CR merged) is an `illegal:` row
#   naming `ready-for-dev` with `needs you: yes` and a queue item that says
#   to remove the label, with its link; no write touches #5 or its CRs — no
#   lock, no kit stamp, no implementer, no CR — its labels are as seeded and
#   the remote refs are the seed's." (ConsoleAPI #27, issue #209: the
#   gate-label audit asked only who applied the label, so a holder's second
#   `ready-for-dev` read as authorization and Path B would have rebuilt
#   merged work)
# source: references/patrol-scan.md § Scan, Gate-label audit — a gate label
#   on a stage that passed is an illegal state: never repaired, never routed
# source: commands/patrol.md §4 — an illegal row is `needs you: yes` with a
#   queue item and its link
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
SEEDED = {"track: spec", "status: ready-for-dev"}
SEED_REFS = 4  # main, spec/5, feat/5, qa/5

r, c = Run(), Checker()
journal = r.journal()
state = r.state()
lines = r.result_text().splitlines()


def touches(e):
    return any(str(e.get(k)) in ("5", "101", "102", "103") for k in ("issue", "pr", "target"))


# ---- end state first: nothing was written --------------------------------
c.expect("patrol-scan.md § Scan (Gate-label audit: ISSUE-LABEL-EVENTS on every gated issue)",
         "the label events of #5 were read",
         any(e.get("route") == "label-events" and str(e.get("issue")) == "5" for e in journal))
c.expect("patrol-scan.md § Scan (a passed stage: never repaired, never routed)",
         "no forge write touched #5 or its CRs",
         not any(e.get("write") and touches(e) for e in journal))
c.expect("patrol-scan.md § Scan (never repair the label)",
         "#5 wears exactly its seeded labels", set(state["issues"]["5"]["labels"]) == SEEDED)
c.expect("patrol-scan.md § Scan (never route the row to next-stage)",
         "no CR was opened and no comment-edit stamped the kit",
         r.journal_writes("pr-create") == 0 and r.journal_writes("comment-edit") == 0)
c.expect("patrol-scan.md § Scan (never route the row to next-stage or integrate)",
         "the remote holds the seed's refs, feat/5 unmoved and nothing merged into spec/5",
         r.remote_ref_count() == SEED_REFS
         and r.git("rev-parse", "feat/5") == r.git("rev-parse", "spec/5"))
c.expect("next-stage.md Path B (never reached: no implementer, no reviewer)",
         "no implementer or reviewer was dispatched",
         not any((b.get("input") or {}).get("subagent_type", "").split(":")[-1]
                 in ("implementer", "reviewer") for b in r.tool_uses(("Task", "Agent"))))
c.expect("patrol.md §1 (the scanner is dispatched)", "a scanner sub-agent ran",
         r.dispatch_count() >= 1)


# ---- the report: the row is illegal, needs you, queued with the remedy ----
def norm(line):
    return re.sub(r"\s*\|\s*", " | ", line.strip()).strip()


hdr_at = next((i for i, ln in enumerate(lines) if norm(ln) == norm(HEADER)), None)
rows = []
if hdr_at is not None:
    for ln in lines[hdr_at + 1:]:
        if not ln.strip().startswith("|"):
            break
        if re.match(r"^\|\s*:?-+", ln.strip()):
            continue
        rows.append([cell.strip() for cell in ln.strip().strip("|").split("|")])
row = next((x for x in rows if len(x) == 4 and re.match(r"^#?5\b", x[0])), None)

q_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\W*your queue", ln.strip(), re.I)), None)
d_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\s*#{1,6}\s*details\b", ln, re.I)), len(lines))
queue = [ln.strip() for ln in lines[q_at + 1:d_at] if ln.strip()] if q_at is not None else []
item = next((ln for ln in queue if re.match(r"^-\s*#5\b", ln)), None)

c.expect("patrol.md §4 (`illegal: <why>`)",
         "#5's `this pass` is an illegal clause naming ready-for-dev",
         row is not None and row[2].startswith("illegal:") and "ready-for-dev" in row[2])
c.expect("patrol.md §4 (an illegal row is `needs you: yes`)",
         "#5 is `needs you: yes`", row is not None and row[3] == "yes")
c.expect("patrol.md §4 (the queue verb: remove the label)",
         "#5's queue item says to remove ready-for-dev, with a link",
         item is not None and re.search(r"\bremove\b", item, re.I) is not None
         and "ready-for-dev" in item and re.search(r"https?://\S+", item) is not None)
c.finish()
