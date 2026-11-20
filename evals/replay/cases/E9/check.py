#!/usr/bin/env python3
# E9 · QA's contract review reaches the holder as `[qa]` spec-CR threads.
# Fixture: the 2.0 shape at the start of (4) — feat/5 merged into spec/5, no
# qa/5 — where the contract AS BUILT (C2, declared in the CR's deviations)
# contradicts spec.md's R5/S2: the spec says an offer expiring exactly at
# `now` still applies; the as-built contract excludes it.
# source: ledger E9 — "QA's finding batch is posted by the main agent as
#   `**[qa] · Q<k> · <label>**` threads on the spec CR (rule F bullets),
#   `in-spec-review` applied, the item appended to `spec.md`'s Open
#   Questions; the QA CR opens and stays a draft; spec-answers' mid-flight
#   re-entry resumes qa." (#140 ruling 3)
# source: commands/next-stage.md B2.5 — QA's findings → threads on the spec CR
# source: references/qa-brief.md § Step zero — the contract review
# source: commands/next-stage.md B2.6 — CR-READY only with no [qa] thread open
# source: references/next-stage-path-b2.md B2.4 — "entry that changes what a rule `R<k>` means
#   is the same stop, raised by you: B2.5's append and thread, role `[<the role that declared
#   it>]`, the label, no dispatch" (#411: either raiser passes; the end state is the rule)
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
journal = r.journal()


def threads(role):
    return [e for e in journal if e.get("write") and e.get("route") == "thread-post-inline"
            and str(e.get("pr")) == "101"
            and re.match(r"\s*\*\*\[%s\]" % role, e.get("body") or "")]


# Two roads to the same end state (#411, ruled 2026-11-20): QA's contract
# review raises it (B2.5), or the main agent reads the declared deviation at
# B2.4 and raises it for the role that declared it — the implementer —
# with QA never dispatched.
qa_threads = threads("qa")
raised = qa_threads or threads("implementer")
c.expect("next-stage.md B2.5 / B2.4 (the question → a thread on the spec CR)",
         "at least one thread on #101 opens with **[qa] — or, QA undispatched, **[implementer]",
         len(raised) >= 1)
c.expect("next-stage.md B2.5 (rule F: options as bullets)",
         "each such thread carries at least two option bullets",
         bool(raised) and all(
             len(re.findall(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\([a-z]\)", e.get("body") or "")) >= 2
             for e in raised))
c.expect("next-stage.md B2.5 (the backward transition)",
         "in-spec-review applied, processing released",
         r.status_labels("5") == ["status: in-spec-review"])
c.expect("next-stage.md B2.5 (the item is appended to spec.md's Open Questions)",
         "a pushed commit beyond the seed touches spec.md on spec/5",
         lambda: r.remote_commits_touching("spec/5", "docs/specs/5/spec.md") >= 2)
creates = [e for e in journal if e.get("write") and e.get("route") == "pr-create"
           and e.get("head") == "qa/5"]
c.expect("next-stage.md B2.6 / B2.4 (the QA CR opens as a draft and stays one; none without QA)",
         "one draft QA CR behind a [qa] thread — none if the main agent raised it — never readied",
         (len(creates) == 1 and creates[0].get("draft") is True if qa_threads else not creates)
         and not any(e.get("write") and e.get("route") == "pr-ready" for e in journal))
c.expect("next-stage.md B2.5 (no thread on the QA CR or the implementation CR for this)",
         "no [qa] thread posted anywhere but the spec CR",
         not any(e.get("write") and e.get("route") == "thread-post-inline"
                 and str(e.get("pr")) != "101"
                 and re.match(r"\s*\*\*\[qa\]", e.get("body") or "") for e in journal))
c.finish()
