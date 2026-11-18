#!/usr/bin/env python3
# E15 · A demotion answer is checked against the contract.
# Fixture: C32's rules and contract before signing; two threads, both
# answered "demote it" — T1/Q1 on R2's premise (about 2M rows; G2's p95
# budget and S2 rest on it), T2/Q2 on R1's premise (named debt for #7).
# source: ledger E15 — "Q2's premise carries `(assumed-empirical:` and no
#   `unverified`, its thread resolved; Q1's premise still carries
#   `(unverified)`; G2's and S2's lines are byte-identical to the seed; one new
#   `## Open Questions` item *raised by the fold of Q1* names R2, G2, S2 or AC-2
#   and its thread is posted; the report does not say ready for approval and the
#   issue stays `in-spec-review`."
# source: commands/spec-answers.md §5.2 — "A demotion a guarantee needs is not
#   folded … leaves the premise `(unverified)` and that clause byte-identical;
#   the fold asks once (below)"; depth 0 → `Q<k>` with *raised by the fold of
#   Q<j>*, its thread posted in step 6
# source: commands/spec-answers.md §5.2 — "keep `<id>` and measure, or correct
#   `<id>`": the id is the premise's rule (R2) or a clause resting on it (G2,
#   S2, AC-2); run-1 asked "keep R2's 2M-row premise and measure … correct R2
#   and S2" (#383)
# source: references/next-stage-path-a.md A3 — `(assumed-empirical:` "Legal
#   only when nothing in a guarantee, scenario or acceptance criterion depends
#   on the claim"
# source: commands/spec-answers.md §7 — a hit is an unresolved blocker; the
#   report does not say "ready for approval"
# Q1's own thread state is not asserted: resolving it with the raised question
# and leaving it open both keep the gate. That the raised question's thread
# came after the push is not observable in the journal; the item being on the
# remote spec branch is.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

G2 = "- G2 · p95 ≤ 1 s for `price(cart, now)` at production scale (R2, S2)."
S2 = ("- S2 — Given 2M offers in the table, When a cart is priced, Then the price returns "
      "within 1 s at p95.")
ITEM = re.compile(r"^- \*\*\[(?:product|em|implementer)\] · Q(\d+) · ", re.M)
UNV = re.compile(r"(?i)\bunverified\b")


def block(text, start, end):
    """The text from the line opening with `start` up to the next `end`, whitespace-flat."""
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return " ".join(text[i:j if j >= 0 else len(text)].split())


def items(spec):
    """{k: item text} for every `## Open Questions` item."""
    marks = list(ITEM.finditer(spec))
    return {int(m.group(1)): spec[m.start():marks[n + 1].start() if n + 1 < len(marks)
                                  else len(spec)]
            for n, m in enumerate(marks)}


def says_ready(text):
    """A "ready for … approval" with no negation in the few words before it."""
    for m in re.finditer(r"ready for (?:the user's |your )?approval", text, re.I):
        if not re.search(r"\b(?:not|never|cannot)\b|n't\b",    # "cannot": run-1, #366
                         text[max(0, m.start() - 30):m.start()], re.I):
            return True
    return False


r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
tech = r.remote_file("spec/5", "docs/specs/5/technical-spec.md") or ""
j = r.journal()
r1 = block(spec, "- **R1 ·", "- **R2 ·")
r2 = block(spec, "- **R2 ·", "## Scenarios")
raised = {k: t for k, t in items(spec).items() if k >= 3 and "fold of Q1" in t}
posted = [e.get("body") or "" for e in j
          if e.get("route") == "thread-post-inline" and str(e.get("pr")) == "101"]
resolved = {str(e.get("thread")) for e in j if e.get("route") == "thread-resolve"}
report = r.result_text()

c.expect("A3 (a demotion nothing depends on is legal)",
         "Q2's premise (R1) carries `(assumed-empirical:` and no `unverified`",
         "(assumed-empirical:" in r1 and not UNV.search(r1))
c.expect("spec-answers.md §5.4 (the folded thread)", "Q2's thread T2 is resolved",
         "T2" in resolved)
c.expect("spec-answers.md §5.2 (not folded — the premise keeps its tag)",
         "Q1's premise (R2) still carries `(unverified)` and no `(assumed-empirical:`",
         "(unverified)" in r2 and "(assumed-empirical:" not in r2)
c.expect("spec-answers.md §5.2 (that clause byte-identical)",
         "G2's line in technical-spec.md is byte-identical to the seed",
         G2 in tech.splitlines())
c.expect("spec-answers.md §5.2 (that clause byte-identical)",
         "S2's line in spec.md is byte-identical to the seed",
         S2 in spec.splitlines())
c.expect("spec-answers.md §5.2 (the fold asks once)",
         "exactly one new Open Questions item says it was raised by the fold of Q1",
         len(raised) == 1)
c.expect("spec-answers.md §5.2 (keep `<id>` and measure, or correct `<id>`)",
         "the raised item names R2, G2, S2 or AC-2",
         any(re.search(r"\b(?:R2|G2|S2|AC-2)\b", t) for t in raised.values()))
c.expect("spec-answers.md §5.2 (depth 0 → its thread is posted in step 6)",
         "an inline thread on the spec CR names the raised item",
         any(re.search(r"\bQ%d\b" % k, b) for k in raised for b in posted))
c.expect("spec-answers.md §7 (a hit is an unresolved blocker)",
         "the report does not say ready for approval",
         not says_ready(report))
c.expect("spec-answers.md §7 (first pass)", "labels end `in-spec-review` alone",
         r.status_labels("5") == ["status: in-spec-review"])
c.finish()
