#!/usr/bin/env python3
# C26 · A pass acts on up to N issues and queues the rest with their wait.
# Fixture: the local key `patrol_issues_per_pass: 2`; #6, #8, #9 `track:
# fast` + `status: ready-for-dev` (gate labels by paul, dated); #5
# in-user-review and quiet; #7 a raw inbox idea in the `discuss` filter.
# source: ledger C26 — "N=2 seeded: two of three `ready-for-dev` issues
#   acted on, the third as seeded with `queued: next-stage · ready-for-dev
#   <age>` in the report; F9 (no key) still proves one."
# source: commands/patrol.md §3 — up to N loop issues per pass, in priority
#   order, from the one table, each issue at most once; the exemptions
#   (intake among them) are outside the N.
# source: commands/patrol.md §4 — `queued: <action> · <gate label> <age>`
#   for a gated row the pass did not reach; the age from the scanner's
#   `labeled` event.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

HEADER = "| issue | state | this pass | needs you |"
FAST = ("6", "8", "9")
SEEDED = {"track: fast", "status: ready-for-dev"}
AGE = re.compile(r"queued: next-stage · ready-for-dev \d+\s*[hd]\b")

r, c = Run(), Checker()
journal = r.journal()
state = r.state()
text = r.result_text()
lines = text.splitlines()


def touches(e, n):
    return any(str(e.get(k)) == n for k in ("issue", "pr", "target"))


def acted(n):
    """The pass started next-stage on #n: the lock journaled, or its fast
    branch on the remote, or a CR opened from it."""
    lock = any(e.get("route") == "issue-edit" and str(e.get("issue")) == n
               and any("processing" in a for a in e.get("add", [])) for e in journal)
    branch = r.git("show-ref", "--verify", "-q", "refs/heads/fast/%s" % n)[0] == 0
    cr = any(e.get("route") == "pr-create" and e.get("head") == "fast/%s" % n for e in journal)
    return lock or branch or cr


def untouched(n):
    issue = state["issues"][n]
    return (set(issue["labels"]) == SEEDED and not issue.get("comments")
            and not any(e.get("write") and touches(e, n) for e in journal)
            and r.git("show-ref", "--verify", "-q", "refs/heads/fast/%s" % n)[0] != 0)


# ---- the N: exactly two of the three fast issues started, one as seeded ----
started = [n for n in FAST if acted(n)]
left = [n for n in FAST if untouched(n)]
c.expect("patrol.md §3 (up to N = 2, each issue at most once)",
         "exactly two of #6/#8/#9 were acted on (got %s)"
         % (", ".join("#" + n for n in started) or "none"),
         len(started) == 2)
c.expect("patrol.md §3 (the third is not reached)",
         "the remaining fast issue is as seeded — labels, no comment, no write, no branch",
         len(left) == 1 and left[0] not in started)
c.expect("patrol.md §3 (never two locks on one issue, never a third)",
         "no issue was locked twice and no issue outside #6/#8/#9 was locked",
         all(sum(1 for e in journal if e.get("route") == "issue-edit" and str(e.get("issue")) == n
                 and any("processing" in a for a in e.get("add", []))) <= 1 for n in FAST)
         and not any(e.get("route") == "issue-edit" and str(e.get("issue")) not in FAST
                     and any("processing" in a for a in e.get("add", [])) for e in journal))
c.expect("patrol.md §3 (the whole inbox, outside the N)",
         "#7 got its **[intake]** questions batch",
         any(b.startswith("**[intake]**") for b in r.issue_comment_bodies("7")))
c.expect("patrol.md §3 (#5 waits on you — nothing to act on)",
         "no forge write touched #5",
         not any(e.get("write") and touches(e, "5") for e in journal))
c.expect("patrol.md §1 (the scanner is dispatched)", "a scanner sub-agent ran",
         r.dispatch_count() >= 1)


# ---- the report: the unreached row carries its wait ---------------------------
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
if len(left) == 1:
    x = row(left[0])
    c.expect("patrol.md §4 (`queued: <action> · <gate label> <age>`)",
             "#%s's `this pass` is `queued: next-stage · ready-for-dev <age>`" % left[0],
             x is not None and AGE.search(x[2]) is not None)
    c.expect("patrol.md §4 (a queued row is not `needs you`)",
             "#%s is `needs you: —`" % left[0], x is not None and x[3] == "—")
for n in started:
    x = row(n)
    c.expect("patrol.md §4 (`acted:` for the issues the pass took)",
             "#%s's `this pass` starts with `acted:`" % n,
             x is not None and x[2].startswith("acted:"))
c.finish()
