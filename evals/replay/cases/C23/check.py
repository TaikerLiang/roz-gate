#!/usr/bin/env python3
# C23 · Patrol runs the review that never ran.
# Fixture: C22's — the implementation CR (PR 102, feat/5) open, zero threads,
# no `**[reviewer] · code-review**` record; no qa/5. The scanner's row reads
# `actionable: code-review`, never `next-stage (qa)`, and patrol serves it
# with the code-review action: the reviewer's threads, then the record.
# source: ledger C23 — "The scanner's row reads `actionable: code-review`,
#   never `next-stage (qa)`; patrol dispatches `reviewer` once with the spec
#   docs; the implementation CR gains one `**[reviewer] · code-review**`
#   comment carrying `reviewed-sha:` equal to its head, posted after every
#   finding thread; nothing is merged, no `<qa-branch>` is cut, the lock is
#   released." (the mirror of C17)
# source: references/patrol-scan.md — the in-flight row's code-review clause
# source: commands/patrol.md § The code-review action
# source: commands/next-stage.md B5 — the record, posted last, even with zero findings
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())
MARK = "**[reviewer] · code-review**"


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the scanner dispatch and its table (C17's reading) ----------------------
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
         "#5's row: actionable: code-review, never next-stage (qa)",
         "code-review" in row(5) and "next-stage" not in row(5))

# ---- one reviewer dispatch, with the spec docs ---------------------------------------
reviews = [b for b in r.tool_uses(("Task", "Agent"))
           if "reviewer" in json.dumps(b.get("input", {}), ensure_ascii=False)
           and "fidelity-brief.md" not in json.dumps(b.get("input", {}), ensure_ascii=False)
           and "patrol-scan.md" not in json.dumps(b.get("input", {}), ensure_ascii=False)]
c.expect("patrol.md § code-review 3 (one review)",
         "exactly one reviewer dispatch", len(reviews) == 1)
c.expect("patrol.md § code-review 3 (the claim attached — D1)",
         "the dispatch names spec.md and technical-spec.md",
         len(reviews) == 1 and all(
             s in json.dumps(reviews[0].get("input", {}), ensure_ascii=False)
             for s in ("spec.md", "technical-spec.md")))

# ---- the record: one marked comment on the implementation CR, last, with the head ----
journal = r.journal()
records = [(i, e) for i, e in enumerate(journal)
           if e.get("write") and e.get("route") in ("pr-comment", "comment-edit")
           and (e.get("pr") is None or str(e.get("pr")) == "102")
           and (e.get("body") or "").startswith(MARK)]
findings = [i for i, e in enumerate(journal)
            if e.get("write") and e.get("route") == "thread-post-inline"
            and str(e.get("pr")) == "102"]
head = r.git("rev-parse", "feat/5")[1].strip()


def record_sha_ok():
    if len(records) != 1:
        return False
    m = re.search(r"reviewed-sha:\s*`?([0-9a-f]{7,40})`?", records[0][1].get("body") or "")
    return bool(m) and head.startswith(m.group(1))


c.expect("next-stage.md B5 (the record, even with zero findings)",
         "the implementation CR (#102) gained exactly one comment opening with the marker",
         len(records) == 1)
c.expect("next-stage.md B5 (reviewed-sha is the head)",
         "the record's reviewed-sha is feat/5's remote head", record_sha_ok)
c.expect("next-stage.md B5 (the record is the last write)",
         "the record was posted after every finding thread on #102",
         len(records) == 1 and all(i < records[0][0] for i in findings))

# ---- nothing else: no merge, no qa branch, lock released -----------------------------
c.expect("patrol.md § code-review (nothing else — no B2)",
         "feat/5 not merged into remote spec/5; no qa/5",
         lambda: not r.remote_is_ancestor("feat/5", "spec/5")
             and r.git("rev-parse", "--verify", "-q", "qa/5")[0] != 0)
c.expect("patrol.md § code-review 4 (the lock)", "status labels cleared at the end",
         r.status_labels("5") == [])
c.finish()
