#!/usr/bin/env python3
# C13 · The in-flight row sees a merged CR.
# Fixture: #5 wears `track: spec` alone; feat/5 and qa/5 are MERGED into
# spec/5 on the forge (the state after a human cleared an integrate STOP).
# source: ledger C13 — "#5 wears `track: spec` alone with `feat/5` and
#   `qa/5` merged into `spec/5`: the scanner's row reads `actionable:
#   integrate`, the pass takes the lock on #5, and no row reads `in
#   progress`." (the open-only lookup read a merged CR as absent, so patrol
#   said "in progress" about a finished build and a STOP cleared by the
#   human was never re-run — issue #77)
# source: references/patrol-scan.md — the in-flight row: CR-FIND in its
#   all-states form; both merged → actionable → /roz-gate:integrate
# source: commands/patrol.md §1 — one read-only scanner sub-agent
# source: commands/patrol.md §3 — the pass acts on the actionable row
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the scanner dispatch and its table (F9's reading) -----------------------
scanner_id = None
for ev in events:
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                and "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False):
            scanner_id = b.get("id")
            break
    if scanner_id:
        break
c.expect("patrol.md §1", "exactly one scanner dispatch, prompt names patrol-scan.md",
         scanner_id is not None and sum(
             1 for b in r.tool_uses(("Task", "Agent"))
             if "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False)) == 1)

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
c.expect("patrol-scan.md (the table)", "the scanner returned a table", "|" in table)


def row(n):
    for line in table.splitlines():
        if re.match(r"^\|\s*#?%s\b" % n, line.strip()):
            return line
    return ""


c.expect("patrol-scan.md (the in-flight row, all-states)",
         "#5's row: actionable: integrate",
         "integrate" in row(5) and "in progress" not in row(5))
c.expect("ledger C13 (a finished build is not 'in progress')",
         "no row reads in progress", "in progress" not in table)

# ---- the pass took the route: the integrate lock on #5 -----------------------
c.expect("patrol.md §3 (act on the actionable row)", "the processing lock was taken on #5",
         any(e.get("route") == "issue-edit" and e.get("issue") == "5"
             and any("processing" in a for a in e.get("add", []))
             for e in r.journal()))

# ---- the scanner wrote nothing (F9's predicate) ------------------------------
WRITE = re.compile(r"gh (issue (edit|comment|close|create)"
                   r"|pr (create|comment|review|edit|merge|ready)"
                   r"|api -X (POST|PATCH|PUT|DELETE)"
                   r"|api graphql[^|;&]*\bmutation\b"
                   r"|api (?!graphql)\S+[^|;&]* -[fF] )")
scanner_writes = [b for ev in events if ev.get("parent_tool_use_id") == scanner_id
                  for b in blocks(ev) if b.get("type") == "tool_use" and b.get("name") == "Bash"
                  and WRITE.search((b.get("input") or {}).get("command", ""))]
c.expect("patrol-scan.md (You write nothing)", "no forge write under the scanner",
         scanner_id is not None and not scanner_writes)
c.finish()
