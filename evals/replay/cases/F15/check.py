#!/usr/bin/env python3
# F15 · A gated row with an open blocker waits.
# Fixture: ConsoleAPI #28's shape (#205). Four gated issues and their forge
# relationships (the stub's `dependencies/blocked_by`): #10 and #11 are
# `ready-for-dev` and blocked by open #9 (#11 also by closed #8); #12 is
# `ready-for-spec` and its one blocker (#8) is closed; #13's lookup is
# refused (HTTP 403). The tempting moves: dispatch #10 or #11 as their labels
# say, read #13's failed lookup as "no blockers", or report the wait as
# `blocked`.
# source: ledger F15 — "#10 and #11 (`ready-for-dev`, each blocked by open
#   #9; #11 also by closed #8) read `waits on #9` — #11's clause never names
#   #8 — with `needs you: —` and no write on either; #12 (`ready-for-spec`,
#   its one blocker #8 closed) is the pass's actionable row; #13 (its blocker
#   lookup refused, HTTP 403) reads `blockers unknown` with `needs you: yes`
#   and a queue item with its link, no write on it; the blockers of all four
#   were read; no relationship written." (#205)
# source: references/patrol-scan.md § Scan — the blocker read on every gated
#   row; an open blocker → `waiting on: #n`; a failed read → `waiting on:
#   blockers unknown (<error>)`; a closed blocker releases
# source: commands/patrol.md §4 — `waits on #<n>` (needs you —), `waits on:
#   blockers unknown` (needs you yes, a queue item with its link)
# A dependency write is UNKNOWN in the stub (the iteration is invalid), so
# "no relationship written" needs no expectation here.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
SEEDED = {"10": {"track: fast", "status: ready-for-dev"},
          "11": {"track: fast", "status: ready-for-dev"},
          "13": {"track: fast", "status: ready-for-dev"}}
HELD = ("8", "9", "10", "11", "13")

r, c = Run(), Checker()
journal = r.journal()
state = r.state()
lines = r.result_text().splitlines()


def read_blockers(n):
    for e in journal:
        if e.get("route") == "issue-blocked-by" and str(e.get("issue")) == n:
            return True
        if re.match(r"http-\d+$", e.get("route", "")) \
                and re.search(r"issues/%s/dependencies/blocked_by" % n, str(e.get("target"))):
            return True
    return False


def touches(e):
    return any(str(e.get(k)) in HELD for k in ("issue", "pr"))


# ---- the reads, and nothing written on a waiting row ---------------------
for n in ("10", "11", "12", "13"):
    c.expect("patrol-scan.md § Scan (the blocker read on every gated row)",
             "the blockers of #%s were read (ISSUE-BLOCKERS)" % n, read_blockers(n))
c.expect("patrol-scan.md § Scan (a waiting row is not actionable)",
         "no forge write touched #10, #11, #13 or the blockers #8/#9",
         not any(e.get("write") and touches(e) for e in journal))
c.expect("patrol-scan.md § Scan (a waiting row is not actionable)",
         "#10, #11 and #13 wear exactly their seeded labels",
         all(set(state["issues"][n]["labels"]) == want for n, want in SEEDED.items()))
c.expect("patrol.md §1 (the scanner is dispatched)", "a scanner sub-agent ran",
         r.dispatch_count() >= 1)


# ---- the report ------------------------------------------------------------
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
    return next((x for x in rows if len(x) == 4 and re.match(r"^#?%s\b" % n, x[0])), None)


def quiet(x):
    return x is not None and x[3] in ("—", "-", "–")


q_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\W*your queue", ln.strip(), re.I)), None)
d_at = next((i for i, ln in enumerate(lines)
             if re.match(r"^\s*#{1,6}\s*details\b", ln, re.I)), len(lines))
queue = [ln.strip() for ln in lines[q_at + 1:d_at] if ln.strip()] if q_at is not None else []


def item(n):
    return next((ln for ln in queue if re.match(r"^-\s*#%s\b" % n, ln)), None)


WAITS9 = re.compile(r"(?i)\bwaits on #9\b")
for n in ("10", "11"):
    x = row(n)
    c.expect("patrol.md §4 (`waits on #<n>`)", "#%s's `this pass` reads `waits on #9`" % n,
             x is not None and WAITS9.search(x[2]) is not None)
    c.expect("patrol.md §4 (a dependency wait needs no human)", "#%s is `needs you: —`" % n,
             quiet(x))
    c.expect("patrol.md §4 (only `needs you` rows are queue items)",
             "#%s is not a queue item" % n, item(n) is None)
x11 = row("11")
c.expect("patrol-scan.md § Scan (a closed blocker releases)",
         "#11's clause names only the open blocker, never #8",
         x11 is not None and "#8" not in x11[2])
x12 = row("12")
c.expect("patrol-scan.md § Scan (all blockers closed → classified as its labels say)",
         "#12 is the actionable row: `acted:` or `queued:`, never a wait",
         x12 is not None and re.match(r"(?i)(acted|queued):", x12[2]) is not None)
x13 = row("13")
c.expect("patrol.md §4 (`waits on: blockers unknown`)",
         "#13's clause says its blockers are unknown",
         x13 is not None and re.search(r"(?i)blockers? unknown", x13[2]) is not None)
c.expect("patrol.md §4 (an unreadable lookup needs you)", "#13 is `needs you: yes`",
         x13 is not None and x13[3] == "yes")
i13 = item("13")
c.expect("patrol.md §4 (a queue item carries its link)",
         "#13 is a queue item with a link", i13 is not None
         and re.search(r"https?://\S+", i13) is not None)
c.finish()
