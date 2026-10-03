#!/usr/bin/env python3
# A7 · A merged CR closes the issue out.
# Fixture: #5 track: fast + in-user-review, PR 102 (fast/5) MERGED, issue
# still OPEN with both labels — #41's GitLab symptom. #6 track: spec +
# in-user-review, PR 103 (spec/6) MERGED, issue already CLOSED by the forge
# with its labels still on — the GitHub default-branch shape (codex, PR #51).
# source: ledger A7 — "Issue closed; every `track:`/`status:` label gone;
#   exactly one shipped comment naming the CR; exactly one close; nothing
#   written to the CR." (an OPEN CR at in-user-review is F1/A4/A5's
#   fixture — zero label writes there) (GitLab and any CR against a release
#   branch leave the issue open wearing `in-user-review` after the merge
#   — the loop's last step never happened — issue #41)
# source: commands/patrol.md — the in-user-review row: CR-FIND with the
#   all-states form; merged → close-out
# source: commands/patrol.md — The close-out action: LABEL-REMOVE every
#   track:/status: label; one `**[patrol] · shipped**` comment; ISSUE-CLOSE
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
iss = r.state()["issues"]["5"]
shipped = [b for b in r.issue_comment_bodies("5") if b.startswith("**[patrol] · shipped**")]
c.expect("patrol.md (close-out 3)", "issue 5 is closed", iss.get("state") == "closed")
c.expect("patrol.md (close-out 1)", "no track:/status: label remains",
         not any(lab.startswith(("track:", "status:")) for lab in iss.get("labels", [])))
c.expect("patrol.md (close-out 2)", "exactly one shipped comment, naming the CR",
         len(shipped) == 1 and ("102" in shipped[0] or "fast/5" in shipped[0]))
c.expect("ledger A7 (nothing written to the CR)", "zero CR writes",
         r.journal_writes(r"^(pr-|thread-)") == 0)
c.expect("ledger A7 (one close)", "exactly one issue-close write — #5; #6 was already closed",
         r.journal_writes(r"^issue-close$") == 1
         and not any(e.get("route") == "issue-close" and e.get("issue") == "6"
                     for e in r.journal()))
iss6 = r.state()["issues"]["6"]
shipped6 = [b for b in r.issue_comment_bodies("6") if b.startswith("**[patrol] · shipped**")]
c.expect("patrol.md (close-out scan: ISSUE-LIST-CLOSED)",
         "#6, closed by the forge, lost its loop labels",
         not any(lab.startswith(("track:", "status:")) for lab in iss6.get("labels", [])))
c.expect("patrol.md (close-out 1)", "#6 got exactly one shipped comment naming its CR",
         len(shipped6) == 1 and ("103" in shipped6[0] or "spec/6" in shipped6[0]))
c.finish()
