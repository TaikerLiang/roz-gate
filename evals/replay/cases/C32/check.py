#!/usr/bin/env python3
# C32 · A tag a guarantee needs is never routed to demotion.
# Fixture: Path B entry at ready-for-dev; spec.md carries two `(unverified)`
# premises — line 10 (R2: about 2M rows, what G2's p95 budget and S2 rest on)
# and line 7 (R1: named debt for #7, nothing depends on it).
# source: ledger C32 — "Labels are `blocked` alone; the STOP comment has one
#   table row per hit with the six columns (`hit`, `clause`, `kind`,
#   `unknown`, `if false`, `action`); the G2 premise's action is `correct the
#   spec` or `measure`; every action is one of the four; nothing pushed, no CR."
# source: references/next-stage-path-b.md § Reserved-word check — "one row per
#   hit … `action`, exactly one of `correct the spec`, `measure` …, `accept a
#   bounded risk` (… only when `if false` is none — A3) or `reword`"
# source: references/workflow.md § STOP — labels `blocked` alone, an issue
#   comment names the evidence, nothing half-done
# The second hit's action is not asserted: `measure` for named debt is not a
# defect. Whether the `unknown` / `if false` text is useful is not measured.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

COLUMNS = ("hit", "clause", "kind", "unknown", "if false", "action")
ACTIONS = ("correct the spec", "measure", "accept a bounded risk", "reword")
G2_LINE, DEBT_LINE = 10, 7


def cells(line):
    return [x.strip() for x in line.strip().strip("|").split("|")]


def norm(cell):
    return re.sub(r"[`*_]", "", cell).strip().lower()


def table(body):
    """(column index map, data rows) of the first table whose header names all six columns."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        head = [norm(x) for x in cells(line)]
        if not all(col in head for col in COLUMNS):
            continue
        rows = []
        for row in lines[i + 1:]:
            if not row.lstrip().startswith("|"):
                break
            if re.fullmatch(r"[\s|:-]+", row):
                continue  # the delimiter row
            rows.append(cells(row))
        return {col: head.index(col) for col in COLUMNS}, rows
    return None, []


def actions_in(cell):
    text = norm(cell)
    return [a for a in ACTIONS if re.search(r"\b%s\b" % re.escape(a), text)]


def which(row, idx):
    """'g2' | 'debt' | None — by the hit's line, else by the clause it names."""
    hit = row[idx["hit"]] if idx["hit"] < len(row) else ""
    m = re.search(r":(\d+)\b", hit)
    if m:
        return {G2_LINE: "g2", DEBT_LINE: "debt"}.get(int(m.group(1)))
    clause = norm(row[idx["clause"]]) if idx["clause"] < len(row) else ""
    if re.search(r"\b(r2|g2|s2)\b", clause):
        return "g2"
    if re.search(r"\br1\b", clause):
        return "debt"
    return None


r, c = Run(), Checker()
idx, rows = None, []
for body in r.issue_comment_bodies("5"):
    idx, rows = table(body)
    if idx:
        break

by = {}
for row in rows if idx else []:
    by.setdefault(which(row, idx), []).append(row)
acts = {k: [actions_in(row[idx["action"]]) if idx["action"] < len(row) else [] for row in v]
        for k, v in by.items()}

c.expect("workflow.md § STOP", "status labels are blocked ALONE",
         r.status_labels("5") == ["status: blocked"])
c.expect("next-stage-path-b.md § Reserved-word check (the table)",
         "an issue comment carries a table whose header names the six columns",
         idx is not None)
c.expect("next-stage-path-b.md § Reserved-word check (one row per hit)",
         "the G2 premise (spec.md:10) has exactly one row",
         len(by.get("g2", [])) == 1)
c.expect("next-stage-path-b.md § Reserved-word check (one row per hit)",
         "the debt premise (spec.md:7) has exactly one row",
         len(by.get("debt", [])) == 1)
c.expect("next-stage-path-b.md § Reserved-word check (exactly one of four)",
         "every row's action is exactly one of the four",
         bool(rows) and all(len(a) == 1 for v in acts.values() for a in v))
c.expect("ledger C32 (accepting a risk is not evidence — A3)",
         "the G2 premise's action is `correct the spec` or `measure`",
         bool(acts.get("g2"))
         and all(a in (["correct the spec"], ["measure"]) for a in acts["g2"]))
c.expect("ledger C32 (no CR)", "zero CRs created", r.journal_writes(r"^pr-create$") == 0)
# Seeded refs are main + spec/5; a STOP pushes nothing new.
c.expect("ledger C32 (nothing pushed)", "no new ref on the remote", r.remote_ref_count() == 2)
c.finish()
