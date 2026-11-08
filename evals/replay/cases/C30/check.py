#!/usr/bin/env python3
# C30 · An unreached actionable row is queued — integrate needs no label.
# Fixture: #5 and #6 wear `track: spec` alone; each has feat/<n> and qa/<n>
# MERGED into spec/<n> with the code-review and fidelity records (C13's
# shape, twice); no local `patrol_issues_per_pass`, so N=1.
# source: ledger C30 — "N=1 seeded with two `actionable: integrate` rows:
#   one is acted on, the other is as seeded — labels, no comment, no write,
#   its `spec/<n>` tip — with `queued: integrate` and `needs you: —` in the
#   report." (ConsoleAPI #27: nothing in the report said patrol had
#   integration queued, so the holder re-applied `ready-for-dev` and made an
#   illegal state — #207, split from #204)
# source: commands/patrol.md §3 — up to N loop issues per pass (default 1),
#   in priority order, from the one table; each issue at most once.
# source: commands/patrol.md §4 — "**Every** `actionable:` row the pass did
#   not reach — the N exhausted above it — is `queued: <action>`, never `in
#   progress`"; "An in-flight row has no tail — `queued: integrate`";
#   "A queued row is `needs you: —`."
# source: references/patrol-scan.md — the in-flight row, both CRs merged
#   with their records → `actionable: integrate`.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
ISSUES = ("5", "6")
PRS = {"5": {"101", "102", "103"}, "6": {"104", "105", "106"}}
SEED_TIP = {n: "integrated #%s (spec + feat + qa merged)" % n for n in ISSUES}
QUEUED = re.compile(r"^queued:\s*integrate$")

r, c = Run(), Checker()
journal = r.journal()
state = r.state()
lines = r.result_text().splitlines()


def locked(n):
    return sum(1 for e in journal if e.get("route") == "issue-edit" and str(e.get("issue")) == n
               and any("processing" in a for a in e.get("add", [])))


def touched(e, n):
    return str(e.get("issue")) == n or str(e.get("pr")) in PRS[n]


def untouched(n):
    """As seeded: the label alone, no comment, no forge write on the issue or
    its CRs, and spec/<n>'s remote tip is still the seed's commit."""
    issue = state["issues"][n]
    _, subject = r.git("log", "-1", "--format=%s", "refs/heads/spec/%s" % n)
    return (issue["labels"] == ["track: spec"] and not issue.get("comments")
            and not any(e.get("write") and touched(e, n) for e in journal)
            and subject.strip() == SEED_TIP[n])


# ---- the N: exactly one of the two integrate rows acted on ---------------------
acted = [n for n in ISSUES if locked(n)]
left = [n for n in ISSUES if n not in acted]
c.expect("patrol.md §3 (N = 1, two actionable rows)",
         "exactly one of #5/#6 was locked (got %s)" % (", ".join("#" + n for n in acted) or "none"),
         len(acted) == 1)
c.expect("patrol.md §3 (the other is not reached)",
         "every unlocked issue is as seeded — label, no comment, no write, spec tip unchanged",
         all(untouched(n) for n in left))
c.expect("patrol.md §3 (each issue at most once)", "no issue was locked twice",
         all(locked(n) <= 1 for n in ISSUES))
c.expect("patrol.md §1 (the scanner is dispatched)", "a scanner sub-agent ran",
         r.dispatch_count() >= 1)


# ---- the report: the unreached row reads `queued: integrate` -----------------
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


c.expect("patrol.md §4 (the table)", "the report has the table", hdr_at is not None)
# The row checks read the table; a report without one fails above, once.
if hdr_at is not None and len(acted) == 1:
    x = row(left[0])
    c.expect("patrol.md §4 (`queued: integrate`, no tail)",
             "#%s's `this pass` is exactly `queued: integrate`" % left[0],
             x is not None and QUEUED.match(x[2]) is not None)
    c.expect("patrol.md §4 (a queued row is not `needs you`)",
             "#%s is `needs you: —`" % left[0], x is not None and x[3] == "—")
    x = row(acted[0])
    c.expect("patrol.md §4 (`acted:` for the issue the pass took)",
             "#%s's `this pass` starts with `acted:`" % acted[0],
             x is not None and x[2].startswith("acted:"))
c.finish()
