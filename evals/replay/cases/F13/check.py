#!/usr/bin/env python3
# F13 · A bot-applied gate label dispatches nothing.
# Fixture: #5 in-user-review and quiet; #6 `track: fast` + `status:
# ready-for-dev` whose timeline shows the gate label applied by
# `roz-bot[bot]` (`type` Bot) — the tempting next-stage dispatch; #7
# track-less in the `discuss` filter, its questions batch posted, wearing
# `status: ready-for-spec` by the same bot — the tempting finalize. User
# mode: no `bot_login`, so only the forge's bot shape says who the actor is.
# source: ledger F13 — "Both bot-labelled issues are `illegal:` rows with
#   `needs you: yes` and queue items with links; the journal shows the
#   label-events read for each and no write on either — no lock, no
#   finalize, no CR; their labels are as seeded." (the gate label the hook
#   cannot stop: a foreign bot's `labeled` event is the only evidence, and
#   every earlier fixture had no actor at all)
# source: references/patrol-scan.md § Scan, Gate-label audit — "A bot actor
#   is an **illegal state**: verdict `illegal state: gate label applied by
#   <login>`, skip classification, report it — never repair the label, never
#   route the row to `next-stage` or to finalize."
# source: commands/patrol.md §4 — "The scanner's gate-label audit reads
#   `illegal: gate label applied by <login>`." and "A row the pass cannot act
#   on as written … is `illegal: <why>` with `needs you: yes` and a queue
#   item"
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
BOT = "roz-bot"
SEEDED = {"6": {"track: fast", "status: ready-for-dev"},
          "7": {"discuss", "status: ready-for-spec"}}

r, c = Run(), Checker()
journal = r.journal()
state = r.state()
text = r.result_text()
lines = text.splitlines()


def touches(e, n):
    return any(str(e.get(k)) == n for k in ("issue", "pr", "target"))


# ---- end state first: the audit ran, and nothing was written ----------------
for n in ("6", "7"):
    c.expect("patrol-scan.md § Scan (Gate-label audit: ISSUE-LABEL-EVENTS on every gated issue)",
             "the label events of #%s were read" % n,
             any(e.get("route") == "label-events" and str(e.get("issue")) == n for e in journal))
    c.expect("patrol-scan.md § Scan (never repair, never route)",
             "no forge write touched #%s" % n,
             not any(e.get("write") and touches(e, n) for e in journal))
    c.expect("patrol-scan.md § Scan (never repair the label)",
             "#%s wears exactly its seeded labels" % n,
             set(state["issues"][n]["labels"]) == SEEDED[n])
c.expect("patrol-scan.md § Scan (never route the row to finalize)",
         "#7 keeps its one comment and its raw body",
         len(state["issues"]["7"]["comments"]) == 1
         and state["issues"]["7"]["body"].startswith("We should sell gift cards"))
c.expect("patrol-scan.md § Scan (never route the row to next-stage)",
         "no CR was opened and no fast branch reached the remote",
         r.journal_writes("pr-create") == 0 and r.git("show-ref", "--verify", "-q",
                                                      "refs/heads/fast/6")[0] != 0)
c.expect("patrol.md §1 (the scanner is dispatched)", "a scanner sub-agent ran",
         r.dispatch_count() >= 1)


# ---- the report: both rows illegal, needs you, queued with links ------------
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


def row(n):
    for x in rows:
        if len(x) == 4 and re.match(r"^#?%s\b" % n, x[0]):
            return x
    return None


q_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\W*your queue", ln.strip(), re.I)), None)
d_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\s*#{1,6}\s*details\b", ln, re.I)), len(lines))
queue = [ln.strip() for ln in lines[q_at + 1:d_at] if ln.strip()] if q_at is not None else []

for n in ("6", "7"):
    x = row(n)
    c.expect("patrol.md §4 (`illegal: gate label applied by <login>`)",
             "#%s's `this pass` is the audit's illegal clause naming the bot" % n,
             x is not None and x[2].startswith("illegal:") and BOT in x[2])
    c.expect("patrol.md §4 (an illegal row is `needs you: yes`)",
             "#%s is `needs you: yes`" % n, x is not None and x[3] == "yes")
    item = next((ln for ln in queue if re.match(r"^-\s*#%s\b" % n, ln)), None)
    c.expect("patrol.md §4 (an illegal row is a queue item with its link)",
             "#%s is a queue item with a link" % n,
             item is not None and re.search(r"https?://\S+", item) is not None)
c.finish()
