#!/usr/bin/env python3
# F11 · A pass reports in the template.
# Fixture: F9's three issues (#5 in-user-review with an unheard top-level
# CR comment, #6 fast + ready-for-dev, #7 inbox in the `discuss` filter with
# no batch yet) plus #8 in-spec-review whose spec-CR thread ends on a
# product question (waits on the human), #9 and #10 blocked under STOP
# comments, and #11 track-less outside the filter (counted, never a row).
# source: ledger F11 — "The report's must-read is the template's table with
#   a row per scanned issue and none for the filtered-out one; no row cites
#   a previous pass; every `this pass` cell is one clause within the cap;
#   every `needs you` row is a queue item with a link and the queue has
#   nothing else; the filter line is present." (the pasted report of #124:
#   key/value blocks, seven issues folded into "same as previous pass", a
#   queue without links, a flip-flop only in Details)
# source: commands/patrol.md §4 — the template header, one row per issue the
#   scanner listed, the cell vocabulary and cap, `needs you`, the filter
#   line, the queue = the `needs you` rows with links, the Details rule
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
CELL_CAP = 12
# The `this pass` vocabulary, verbatim from patrol.md §4: a prefixed clause or
# one of the two bare words.
VOCAB = ("acted:", "queued:", "waits on you:", "blocked:", "locked:", "illegal:",
         "shipped", "in progress")
LISTED = ("5", "6", "7", "8", "9", "10")   # one row each — what the scanner lists
FILTERED = "11"                            # outside the inbox filter: counted, never a row
# A row or queue line that leans on a pass the reader never saw. Details is
# free text, so only the explicit cross-pass phrases are banned there.
BANNED_MUST_READ = re.compile(r"previous pass|last pass|same as|unchanged", re.I)
BANNED_DETAILS = re.compile(r"previous pass|last pass", re.I)

r, c = Run(), Checker()
text = r.result_text()
lines = text.splitlines()


def norm(line):
    return re.sub(r"\s*\|\s*", " | ", line.strip()).strip()


# ---- the table: the template header, then the contiguous `|` lines ----------
hdr_at = next((i for i, ln in enumerate(lines) if norm(ln) == norm(HEADER)), None)
rows = []
if hdr_at is not None:
    for ln in lines[hdr_at + 1:]:
        if not ln.strip().startswith("|"):
            break
        if re.match(r"^\|\s*:?-+", ln.strip()):
            continue
        rows.append([cell.strip() for cell in ln.strip().strip("|").split("|")])
c.expect("patrol.md §4 (the table)", "the report carries the template header",
         hdr_at is not None)
c.expect("patrol.md §4 (the table)", "every row has the template's four cells",
         bool(rows) and all(len(x) == 4 for x in rows))


def row(n):
    for x in rows:
        if len(x) == 4 and re.match(r"^#?%s\b" % n, x[0]):
            return x
    return None


def num(x):
    m = re.match(r"^#?(\d+)", x[0])
    return m.group(1) if m else ""


nums = [num(x) for x in rows if len(x) == 4]
c.expect("patrol.md §4 (one row per issue the scanner listed, nothing else in it)",
         "the rows are #5 #6 #7 #8 #9 #10 — each once, no other issue",
         sorted(nums, key=int) == sorted(LISTED, key=int) and len(nums) == len(set(nums)))
c.expect("patrol-scan.md (the filter) / patrol.md §4",
         "the filtered-out #11 is counted, never a row", row(FILTERED) is None)
c.expect("patrol.md §4 (no row cites another pass)",
         "no row says previous pass / same as / unchanged",
         bool(rows) and not any(BANNED_MUST_READ.search(" | ".join(x)) for x in rows))
c.expect("patrol.md §4 (`this pass`: one clause, at most %d words)" % CELL_CAP,
         "every `this pass` cell is within the cap",
         bool(rows) and all(len(x[2].split()) <= CELL_CAP for x in rows))
c.expect("patrol.md §4 (`this pass`: the fixed vocabulary)",
         "every `this pass` cell is one of the fixed forms",
         bool(rows) and all(x[2] in ("shipped", "in progress")
                            or x[2].startswith(VOCAB[:6]) for x in rows))
c.expect("patrol.md §4 (`needs you`: yes or —)", "every `needs you` cell is yes or —",
         bool(rows) and all(x[3] in ("yes", "—") for x in rows))
c.expect("patrol.md §4 (`needs you` whenever the next move is a human's)",
         "#8 (a thread awaiting the human), #9 and #10 (blocked) are `needs you`",
         all(row(n) is not None and row(n)[3] == "yes" for n in ("8", "9", "10")))
c.expect("patrol.md §4 (`needs you`)", "#6 (queued machine work) is not",
         row("6") is not None and row("6")[3] == "—")
# The acted rows: a review answered leaves the review to the human; a
# questions batch posted leaves the questions to the holder (§4). Tied to
# what the pass did, so a pass that never got to them is not scored on them.
acted5 = r.route_taken("5")
asked7 = any(b.startswith("**[intake]**") for b in r.issue_comment_bodies("7"))
c.expect("patrol.md §4 (`needs you`: a review to merge)",
         "#5 is `needs you` exactly when the pass answered it",
         row("5") is not None and (row("5")[3] == "yes") == acted5)
c.expect("patrol.md §4 (`needs you`: an intake batch posted this pass)",
         "#7 is `needs you` exactly when its batch was posted",
         row("7") is not None and (row("7")[3] == "yes") == asked7)

# ---- the filter line ---------------------------------------------------------
c.expect("patrol.md §4 (the filter line)", "the filter line counts the one excluded issue",
         any(ln.strip().lower().startswith("inbox filter:") and "1 track-less" in ln
             for ln in lines))

# ---- the queue: `Your queue:` … up to `## Details` or the end -----------------
q_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\W*your queue", ln.strip(), re.I)), None)
d_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\s*#{1,6}\s*details\b", ln, re.I)), len(lines))
queue = [ln.strip() for ln in lines[q_at + 1:d_at] if ln.strip()] if q_at is not None else []
items = [ln for ln in queue if re.match(r"^-\s*#\d+", ln)]
loop_items = [ln for ln in queue if re.match(r"^-\s*loop\s+—", ln)]   # §0's flags
yes_rows = {num(x) for x in rows if len(x) == 4 and x[3] == "yes"}
queued = {re.match(r"^-\s*#(\d+)", ln).group(1) for ln in items}
c.expect("patrol.md §4 (the queue)", "the queue exists", q_at is not None)
c.expect("patrol.md §4 (the queue holds items only)",
         "every queue line is `- #n — …` or `- loop — …`",
         bool(queue) and len(items) + len(loop_items) == len(queue))
c.expect("patrol.md §4 (a queue item without its link is not written)",
         "every queue item carries a link",
         bool(items) and all(re.search(r"https?://\S+", ln) for ln in items))
c.expect("patrol.md §4 (exactly the `needs you` rows)",
         "the queue is exactly the `needs you` rows",
         bool(rows) and bool(items) and queued == yes_rows)
c.expect("patrol.md §4 (no row cites another pass)", "no queue line cites another pass",
         not any(BANNED_MUST_READ.search(ln) for ln in queue))

# ---- Details: trailing, and never the only home of a cross-pass note ---------
details = "\n".join(lines[d_at + 1:]) if d_at < len(lines) else ""
c.expect("patrol.md §4 (Details)", "Details cites no other pass either",
         not BANNED_DETAILS.search(details))
c.finish()
