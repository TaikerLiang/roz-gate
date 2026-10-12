#!/usr/bin/env python3
# E8 · A top-level comment on the spec CR is heard as an amendment.
# Fixture: the spec CR has no inline thread; the human said what the spec
# misses as a TOP-LEVEL comment on the CR — no agent question, no [role]
# tag — the issue's second sentence (re-check at checkout).
# source: ledger E8 — "`spec.md` on the remote carries the amendment; a
#   top-level `✅ [product] amended` reply cites the comment; labels end
#   `in-spec-review` alone, no STOP." (spec-answers read THREADS-LIST only,
#   so the top-level comment was never classified — issue #98)
# source: commands/spec-answers.md §2 — THREADS-LIST, REVIEWS-LIST,
#   CR-COMMENTS-LIST on each CR
# source: commands/spec-answers.md §3 — a top-level item is unheard when its
#   latest entry does not start with `**[` or `✅ [`; no path → product's
# source: commands/spec-answers.md §5.4 — a top-level item has no thread:
#   CR-COMMENT the `✅ [<role>] amended — …` line; nothing to resolve
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
c.expect("spec-answers.md §2 (the channel was read)",
         "CR-COMMENTS-LIST was called on the spec CR",
         any(e.get("route") == "cr-comments-list" and str(e.get("target")) == "101"
             for e in r.journal()))
c.expect("spec-answers.md §3 (a top-level item is processed)",
         "a pushed commit beyond the seed touches spec.md",
         r.remote_commits_touching("spec/5", "docs/specs/5/spec.md") >= 2)
c.expect("ledger E8 (the amendment landed in the owning document)",
         "spec.md now covers the re-check at checkout",
         any(w in spec for w in ("結帳", "checkout")))
c.expect("spec-answers.md §5.4", "a top-level reply on the CR opens with ✅ [ and says amended",
         any(e.get("write") and e.get("route") == "pr-comment" and str(e.get("pr")) == "101"
             and (e.get("body") or "").startswith("✅ [") and "amended" in (e.get("body") or "")
             for e in r.journal()))
c.expect("spec-answers.md §9 (labels)", "in-spec-review stays, no STOP",
         r.status_labels("5") == ["status: in-spec-review"])
c.finish()
