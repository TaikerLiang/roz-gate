#!/usr/bin/env python3
# F9 · A pass acts from the scanner's table.
# Fixture: #5 in-user-review with an unheard top-level CR comment (A4's
# shape), #6 track: fast + ready-for-dev, #7 a raw inbox idea with no
# questions batch yet.
# source: ledger F9 — "The scanner's table has a row per issue with the
#   right verdict; the pass acts on the top actionable row, locks no other
#   loop issue, posts every intake batch; the scanner writes nothing; the
#   main agent lists nothing after the table." (the scan used to live in
#   the main agent's context — #59)
# source: commands/patrol.md §1 — one read-only scanner sub-agent, prompt =
#   references/patrol-scan.md
# source: commands/patrol.md §2 — never re-read the forge to confirm a row
# source: references/patrol-scan.md — the table's verdict vocabulary
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


# ---- the scanner dispatch and its result ------------------------------------
scanner_id, scanner_at = None, None
for i, ev in enumerate(events):
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                and "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False):
            scanner_id, scanner_at = b.get("id"), i
            break
    if scanner_id:
        break
c.expect("patrol.md §1", "exactly one scanner dispatch, prompt names patrol-scan.md",
         scanner_id is not None and sum(
             1 for b in r.tool_uses(("Task", "Agent"))
             if "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False)) == 1)

table, table_at = "", None
for i, ev in enumerate(events):
    for b in blocks(ev):
        if b.get("type") == "tool_result" and b.get("tool_use_id") == scanner_id:
            cont = b.get("content")
            table = cont if isinstance(cont, str) else "".join(
                x.get("text", "") for x in (cont or []) if isinstance(x, dict))
            table_at = i
c.expect("patrol-scan.md (the table)", "the scanner returned a table", "|" in table)


def row(n):
    for line in table.splitlines():
        if re.match(r"^\|\s*#?%s\b" % n, line.strip()):
            return line
    return ""


c.expect("patrol-scan.md (verdict)", "#5's row: actionable: review-answers",
         "review-answers" in row(5))
c.expect("patrol-scan.md (verdict)", "#6's row: actionable: next-stage (ready-for-dev)",
         "next-stage" in row(6))
c.expect("patrol-scan.md (verdict)", "#7's row: intake: questions",
         "intake" in row(7) and "question" in row(7))
c.expect("patrol-scan.md (holder column)", "#7's row names its gate holder (paul)",
         "paul" in row(7))

# ---- the scanner wrote nothing ----------------------------------------------
WRITE = re.compile(r"gh (issue (edit|comment|close|create)"
                   r"|pr (create|comment|review|edit|merge|ready)"
                   r"|api -X (POST|PATCH|PUT|DELETE)|api .*-f )")
scanner_writes = [b for ev in events if ev.get("parent_tool_use_id") == scanner_id
                  for b in blocks(ev) if b.get("type") == "tool_use" and b.get("name") == "Bash"
                  and WRITE.search((b.get("input") or {}).get("command", ""))]
c.expect("patrol-scan.md (You write nothing)", "no forge write under the scanner",
         scanner_id is not None and not scanner_writes)

# ---- the main agent never re-listed after the table -------------------------
LIST = re.compile(r"gh (issue list|pr list|api repos/[^ ]+/(issues|pulls)(\?|\s|$))")
relist = [b for ev in events[table_at + 1:]
          if table_at is not None and not ev.get("parent_tool_use_id")
          for b in blocks(ev) if b.get("type") == "tool_use" and b.get("name") == "Bash"
          and LIST.search((b.get("input") or {}).get("command", ""))]
c.expect("patrol.md §2 (never re-read to confirm a row)",
         "no issue/CR listing by the main agent after the table",
         table_at is not None and not relist)

# ---- the actions: top row acted on, one-issue rule held, intake posted -------
c.expect("patrol.md §3 (closest to done)", "the pass acted on #5 (lock or marker reply)",
         r.route_taken("5"))
c.expect("patrol.md §3 (one loop issue per pass)", "#6 was not locked or advanced",
         not r.has_label("6", "status: processing")
         and r.journal_writes(r"^pr-create$") == 0
         and r.git("rev-parse", "--verify", "-q", "refs/heads/fast/6")[0] != 0)
c.expect("patrol.md §3 (the whole inbox)", "#7 got its **[intake]** questions batch",
         any(b.startswith("**[intake]**") for b in r.issue_comment_bodies("7")))
c.finish()
