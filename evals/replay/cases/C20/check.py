#!/usr/bin/env python3
# C20 · (4) launches only after the implementation lands on the spec branch.
# Fixture: #5 in flight at the end of (3) — the implementation CR (PR 102,
# feat/5) open and review-clean (its `**[reviewer] · code-review**` record
# current, zero threads), no qa/5. Path B2 of next-stage lands feat/5 on
# spec/5, cuts qa/5 off the new tip and dispatches QA under the marker.
# source: ledger C20 — "`ready-for-dev` launches (3)+(5); next-stage B2 merges
#   the review-clean implementation CR into `<spec-branch>`, pushes, then cuts
#   `<qa-branch>` off the new tip; the QA dispatch runs between marker-on
#   (`seat=qa`) and marker-off, once; a draft QA CR targets `<spec-branch>`;
#   no gate label is involved; nothing is pushed to `<feat-branch>`." (#140)
# source: commands/next-stage.md B2.1 — the record read; B2.2 — merge, push;
#   B2.3 — qa off the new tip; B2.4 — the QA dispatch procedure; B2.6 — the
#   draft QA CR, ready only with no `[qa]` thread open
# source: references/workflow.md (3)/(4) — the implementation lands, then QA
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())
FEAT_COMMITS = 4   # seed-common, config, spec docs, impl — the seed's feat/5 history


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the remote: feat/5 landed on spec/5, qa/5 cut off that tip, feat/5 untouched ----
c.expect("next-stage.md B2.2 (land the implementation, push)",
         "remote spec/5 contains feat/5's tip",
         lambda: r.remote_is_ancestor("feat/5", "spec/5"))
c.expect("next-stage.md B2.3 (qa off the new tip)",
         "remote qa/5 exists and descends from feat/5 (the merged tip)",
         lambda: r.git("rev-parse", "--verify", "-q", "qa/5")[0] == 0
             and r.remote_is_ancestor("feat/5", "qa/5"))
c.expect("ledger C20 (nothing pushed to the implementation branch)",
         "remote feat/5 still has the seed's %d commits" % FEAT_COMMITS,
         lambda: r.git("rev-list", "--count", "feat/5")[1].strip() == str(FEAT_COMMITS))

# ---- the forge: the record was read, a draft QA CR, labels ------------------------
journal = r.journal()
c.expect("next-stage.md B2.1 (review-clean = the record, current, + zero threads)",
         "the implementation CR's comments were listed (the code-review record read)",
         any(e.get("route") == "cr-comments-list" and str(e.get("target")) == "102"
             for e in journal))
creates = [e for e in journal if e.get("write") and e.get("route") == "pr-create"
           and e.get("head") == "qa/5"]
c.expect("next-stage.md B2.6 (the QA CR opens as a draft, targeting the spec branch)",
         "one draft CR with head qa/5 targets spec/5",
         len(creates) == 1 and creates[0].get("draft") is True
         and any(p.get("headRefName") == "qa/5" and p.get("baseRefName") == "spec/5"
                 for p in r.state().get("prs", {}).values()))
qa_threads = [e for e in journal if e.get("write") and e.get("route") == "thread-post-inline"
              and str(e.get("pr")) == "101"]
readied = [e for e in journal if e.get("write") and e.get("route") == "pr-ready"]
c.expect("next-stage.md B2.6 (CR-READY only with no [qa] thread open)",
         "the QA CR was not readied while a [qa] thread was posted",
         not (qa_threads and readied))
c.expect("next-stage.md B2 (no gate label is involved)",
         "no gate label written",
         not any(e.get("route") == "issue-edit" and any("ready-for" in a for a in e.get("add", []))
                 for e in journal))
c.expect("next-stage.md B2.8 (unlock; in-spec-review stays only when B2.5 applied it)",
         "status labels end empty, or in-spec-review alone",
         r.status_labels("5") in ([], ["status: in-spec-review"]))

# ---- the QA dispatch procedure: marker on (seat=qa) → one dispatch → marker off ----
ordered = []
for ev in events:
    for b in blocks(ev):
        if b.get("type") != "tool_use":
            continue
        inp = b.get("input") or {}
        if b.get("name") == "Bash":
            cmd = inp.get("command", "")
            if "roz-gate/fidelity-dispatch" in cmd and "feat=feat/5" in cmd and ">" in cmd:
                ordered.append("on-qa" if "seat=qa" in cmd else "on")
            elif "rm -f" in cmd and "roz-gate/fidelity-dispatch" in cmd:
                ordered.append("off")
        elif b.get("name") in ("Task", "Agent") \
                and "qa-brief.md" in json.dumps(inp, ensure_ascii=False):
            ordered.append("qa")
c.expect("next-stage.md B2.4 (the marker, seat=qa, the bound ref)",
         "the marker was written with feat=feat/5 and seat=qa", "on-qa" in ordered)
c.expect("next-stage.md B2.4 (one QA dispatch under the brief)",
         "exactly one dispatch carries qa-brief.md", ordered.count("qa") == 1)
c.expect("next-stage.md B2.4 (the procedure's order)",
         "marker on (seat=qa), then the QA dispatch, then marker off — in that order",
         "on-qa" in ordered and ordered.count("qa") == 1
         and any(o.startswith("on") for o in ordered) and "off" in ordered
         and ordered.index("on-qa") < ordered.index("qa")
         < len(ordered) - 1 - ordered[::-1].index("off"))
c.expect("next-stage.md B2.1 (the lock)", "processing released",
         "status: processing" not in r.status_labels("5"))
c.finish()
