#!/usr/bin/env python3
# F3 · Spec refinement lands a complete set.
# Fixture: a gated issue at ready-for-spec; Path A runs end to end.
# source: ledger F3 — "Both spec documents exist; the CR is open; the
#   number of posted threads equals the number of entries in Open
#   Questions; labels flipped exactly once; no question left in any other
#   document." (the thread count catches a question written but never
#   surfaced — the E2 failure, detected by arithmetic)
# source: commands/next-stage.md:170-186 — A5 opens the CR; A6 posts one
#   thread per Open Questions item, body = the item verbatim
# source: commands/next-stage.md:201-203 — A7 flips ready-for-spec+
#   processing → in-spec-review only after CR and threads exist
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md")
tech = r.remote_file("spec/5", "docs/specs/5/technical-spec.md")

c.expect("next-stage.md (A3/A4)", "both spec docs exist on the pushed spec/5",
         spec is not None and tech is not None)
c.expect("next-stage.md:170-173 (A5)", "exactly one CR opened, head spec/5",
         sum(1 for p in r.state()["prs"].values()
             if p["headRefName"] == "spec/5") == 1)

# The arithmetic assertion: posted threads == Open Questions entries.
def counts_match():
    threads = r.journal_writes(r"^thread-post-inline$")
    m = re.search(r"##\s*Open Questions(.*?)(?:\n##\s|\Z)", spec or "", re.S)
    qcount = len(re.findall(r"\*\*\[[^\]]+\]\s*·\s*Q\d+", m.group(1) if m else ""))
    return threads > 0 and threads == qcount

c.expect("ledger F3 + next-stage.md:181-186 (A6)",
         "posted threads == Open Questions entries (and > 0)", counts_match)
c.expect("next-stage.md:201-203 (A7)", "labels: in-spec-review alone",
         r.status_labels("5") == ["status: in-spec-review"])
c.expect("ledger F3 + next-stage.md:175-180 (A6 sweep)",
         "no question-shaped section left in technical-spec.md",
         not re.search(r"^#+ .*(open questions|TBD)", tech or "", re.I | re.M))
c.finish()
