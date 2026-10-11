#!/usr/bin/env python3
# C17 · Patrol runs the audit that never ran.
# Fixture: C16's — spec/5, feat/5, qa/5 open and thread-clean, the QA CR
# ready, no top-level comment on it (the fidelity audit never ran). The
# pre-#95 scanner routed this to integrate; the row now reads
# `actionable: fidelity-audit`, and patrol serves it with B5b's
# fidelity-dispatch procedure, run alone.
# source: ledger C17 — "The scanner's row reads `actionable: fidelity-audit`;
#   patrol writes the marker (with `feat=feat/5`), dispatches `reviewer`
#   under the fidelity brief, the QA CR gains one `**[reviewer] · fidelity**`
#   comment and the marker is removed; no integrate step runs (no
#   `in-user-review`, nothing merged); the lock is released."
# source: references/patrol-scan.md — the in-flight row's fidelity-audit clause
# source: commands/patrol.md § The fidelity-audit action
# source: commands/next-stage.md B5b — the fidelity-dispatch procedure
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())
MARK = "**[reviewer] · fidelity**"


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the scanner dispatch and its table (C13's reading) ----------------------
scanner_id = None
for ev in events:
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                and "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False):
            scanner_id = b.get("id")
            break
    if scanner_id:
        break

table = ""
for ev in events:
    for b in blocks(ev):
        if b.get("type") == "tool_result" and b.get("tool_use_id") == scanner_id:
            cont = b.get("content")
            text = cont if isinstance(cont, str) else "".join(
                x.get("text", "") for x in (cont or []) if isinstance(x, dict))
            if "|" in text:
                table = text
    if ev.get("type") == "system" and ev.get("subtype") == "task_notification" \
            and ev.get("tool_use_id") == scanner_id and "|" in (ev.get("summary") or ""):
        table = ev["summary"]


def row(n):
    for line in table.splitlines():
        if re.match(r"^\|\s*#?%s\b" % n, line.strip()):
            return line
    return ""


c.expect("patrol-scan.md (the in-flight row, no record)",
         "#5's row: actionable: fidelity-audit, never integrate",
         "fidelity-audit" in row(5) and "integrate" not in row(5))

# ---- the action: marker on, the blind dispatch, marker off --------------------
bash = [(b.get("input") or {}).get("command", "") for b in r.tool_uses(("Bash",))]
c.expect("patrol.md § fidelity-audit 3 (the marker, with the bound ref)",
         "the marker was written with feat=feat/5",
         any("roz-gate/fidelity-dispatch" in cmd and "feat=feat/5" in cmd
             and ">" in cmd for cmd in bash))
c.expect("patrol.md § fidelity-audit 3 (marker off)",
         "the marker was removed after the dispatch",
         any("rm -f" in cmd and "roz-gate/fidelity-dispatch" in cmd for cmd in bash))
c.expect("patrol.md § fidelity-audit 3 (the reviewer under the brief)",
         "one dispatch carries fidelity-brief.md",
         sum(1 for b in r.tool_uses(("Task", "Agent"))
             if "fidelity-brief.md" in json.dumps(b.get("input", {}), ensure_ascii=False)) >= 1)
c.expect("fidelity-brief.md § Findings (the record)",
         "the QA CR (#103) gained one top-level comment opening with the marker",
         sum(1 for e in r.journal() if e.get("write") and e.get("route") == "pr-comment"
             and str(e.get("pr")) == "103" and (e.get("body") or "").startswith(MARK)) == 1)

# ---- nothing else: no integrate, no commit, lock released ----------------------
c.expect("patrol.md § fidelity-audit (nothing else of B5b, no integrate)",
         "no in-user-review; nothing merged into remote spec/5",
         lambda: not r.has_label("5", "status: in-user-review")
             and not r.remote_is_ancestor("feat/5", "spec/5")
             and not r.remote_is_ancestor("qa/5", "spec/5"))
c.expect("patrol.md § fidelity-audit 4 (the lock)", "status labels cleared at the end",
         r.status_labels("5") == [])
c.finish()
