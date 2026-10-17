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
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
journal = r.journal()
qa_threads = [e for e in journal if e.get("write") and e.get("route") == "thread-post-inline"
              and str(e.get("pr")) == "101"
              and re.match(r"\s*\*\*\[qa\]", e.get("body") or "")]
c.expect("next-stage.md B2.5 (the finding batch → [qa] threads on the spec CR)",
         "at least one thread on #101 opens with **[qa]", len(qa_threads) >= 1)
c.expect("next-stage.md B2.5 (rule F: options as bullets)",
         "each [qa] thread carries at least two option bullets",
         bool(qa_threads) and all(
             len(re.findall(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\([a-z]\)", e.get("body") or "")) >= 2
             for e in qa_threads))
c.expect("next-stage.md B2.5 (the backward transition)",
         "in-spec-review applied, processing released",
         r.status_labels("5") == ["status: in-spec-review"])
c.expect("next-stage.md B2.5 (the item is appended to spec.md's Open Questions)",
         "a pushed commit beyond the seed touches spec.md on spec/5",
         lambda: r.remote_commits_touching("spec/5", "docs/specs/5/spec.md") >= 2)
creates = [e for e in journal if e.get("write") and e.get("route") == "pr-create"
           and e.get("head") == "qa/5"]
c.expect("next-stage.md B2.6 (the QA CR opens as a draft and stays one)",
         "one draft QA CR, never readied while the [qa] thread is open",
         len(creates) == 1 and creates[0].get("draft") is True
         and not any(e.get("write") and e.get("route") == "pr-ready" for e in journal))
c.expect("next-stage.md B2.5 (no thread on the QA CR or the implementation CR for this)",
         "no [qa] thread posted anywhere but the spec CR",
         not any(e.get("write") and e.get("route") == "thread-post-inline"
                 and str(e.get("pr")) != "101"
                 and re.match(r"\s*\*\*\[qa\]", e.get("body") or "") for e in journal))
c.finish()
