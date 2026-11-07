#!/usr/bin/env python3
# E11 · A fold may ask once — the second-order question is deferred.
# Fixture: the spec CR's one open thread is Q6, whose `## Open Questions`
# item carries *raised by the fold of Q3* (depth 1). The holder answered (b):
# an offer valid when the line was added stays honoured. The contract's cart
# line carries no timestamp (C1), so the fold cannot say when "added" is —
# it must ask, and what it asks is depth 2.
# source: ledger E11 — "The depth-1 thread (Q6, itself raised by the fold of
#   Q3) is folded and resolved; the question its answer forces … lands in
#   `spec.md`'s `## Open Questions` as `Q7 … · deferred` naming the fold of
#   Q6, with no thread posted; one `**[spec-answers] · deferred**` CR comment
#   names it; labels end `in-spec-review` alone."
# source: commands/spec-answers.md §5.2 — "A fold may ask once": depth read
#   from the item's *raised by the fold of Q<i>* line; depth 1 → `· deferred`,
#   no thread, one `**[spec-answers] · deferred**` CR-COMMENT
# source: commands/spec-answers.md §5.4 — the folded thread gets its ✅ reply
#   and THREAD-RESOLVE
# source: commands/spec-answers.md §7 — first pass: `processing` removed,
#   `in-spec-review` left; deferred items are not threads
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run, invalid

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
j = r.journal()
posted = [e for e in j if e.get("route") == "thread-post-inline" and str(e.get("pr")) == "101"]
deferred_comments = [e for e in j if e.get("write") and e.get("route") == "pr-comment"
                     and str(e.get("pr")) == "101"
                     and (e.get("body") or "").startswith("**[spec-answers] · deferred**")]
Q7 = r"^- \*\*\[(?:product|em|implementer)\] · Q7 · [^\n]*?\*\*"
q7 = re.search(Q7, spec, re.M)
q7_deferred = re.search(Q7[:-4] + r"· deferred\*\*", spec, re.M)
resolved = [e for e in j if e.get("route") == "thread-resolve" and str(e.get("thread")) == "T1"]

if resolved and not q7 and not posted and not deferred_comments:
    # The fold happened (Q6 resolved) and raised nothing: the depth rule was
    # never exercised — not this case's FAIL. A run that never folded is.
    invalid("the fold raised no question — the depth rule was never exercised "
            "(C1 has no timestamp and the fold did not ask)")

c.expect("spec-answers.md §5.4 (the answered thread is folded)",
         "Q6's thread T1 is resolved and a commit beyond the seed touches spec.md",
         bool(resolved) and r.remote_commits_touching("spec/5", "docs/specs/5/spec.md") >= 2)
c.expect("spec-answers.md §5.2 (the resolved-entry shape)",
         "Q6's item carries a **Resolved:** block",
         len(re.findall(r"\*\*Resolved:\*\*", spec)) >= 2)
c.expect("ledger E11 (the second-order question lands in the single collection point)",
         "spec.md's Open Questions gains a Q7 item whose title ends `· deferred`",
         q7_deferred is not None)
c.expect("spec-answers.md §5.2 (depth 1 → the item names the fold it came from)",
         "the Q7 item says it was raised by the fold of Q6",
         re.search(r"fold of Q6", spec) is not None)
c.expect("spec-answers.md §5.2 (post no thread)",
         "no inline thread was posted on the spec CR",
         not posted)
c.expect("spec-answers.md §5.2 (one top-level deferred comment)",
         "one `**[spec-answers] · deferred**` CR comment names Q7",
         len(deferred_comments) == 1 and "Q7" in (deferred_comments[0].get("body") or ""))
c.expect("spec-answers.md §7 (first pass, every thread resolved)",
         "labels end `in-spec-review` alone — a deferred item holds nothing",
         r.status_labels("5") == ["status: in-spec-review"])
c.finish()
