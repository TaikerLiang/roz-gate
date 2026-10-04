#!/usr/bin/env python3
# E6 · A thread the human opens is an amendment, folded like an answer.
# Fixture: the spec CR has one unresolved thread, opened by the human on
# spec.md with a single comment — no agent question, no [role] tag — saying
# the spec misses the issue's second sentence (re-check at checkout).
# source: ledger E6 — "`spec.md` on the remote carries the amendment; a
#   `✅ [<role>] amended` reply; the thread resolved." (a human-opened thread
#   has one comment and no `[role]` tag, so the answered-thread rule skipped
#   it while patrol classified it actionable — issue #62)
# source: commands/spec-answers.md §3 — an amendment request: its first
#   comment does NOT start with `**[` or `✅ [`; one comment is enough; the
#   role is the document the thread sits on
# source: commands/spec-answers.md §5.4 — `✅ [<role>] amended — …` then
#   THREAD-RESOLVE
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
c.expect("spec-answers.md §3 (an amendment is processed)",
         "a pushed commit beyond the seed touches spec.md",
         r.remote_commits_touching("spec/5", "docs/specs/5/spec.md") >= 2)
c.expect("ledger E6 (the amendment landed in the owning document)",
         "spec.md now covers the re-check at checkout",
         any(w in spec for w in ("結帳", "checkout")))
c.expect("spec-answers.md §5.4", "the reply opens with ✅ [ and says amended",
         any(e.get("route") == "thread-reply" and e.get("body", "").startswith("✅ [")
             and "amended" in e.get("body", "") for e in r.journal()))
c.expect("spec-answers.md §5.4", "the thread was resolved",
         any(e.get("route") == "thread-resolve" for e in r.journal()))
c.expect("spec-answers.md §9 (lock released)", "no processing left behind",
         not r.has_label("5", "status: processing"))
c.finish()
