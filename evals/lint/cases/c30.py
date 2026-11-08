"""C30 · an unreached actionable row is queued — integrate needs no label   (#207)
ConsoleAPI #27: the implementation merged, the QA CR audited and
thread-clean, and the holder wanted integration to proceed. Nothing in
the patrol report said patrol had it — `queued:` was defined for gated
rows alone (#204), so an unreached `actionable: integrate` row had no
clause — and the holder reached for the only lever they knew, a second
`ready-for-dev`, which the loop can only read as an illegal state (#209).
Since #207 every `actionable:` row the pass did not reach is
`queued: <action>` — `queued: integrate` included — and every surface that
states who moves (6) says there is no label for it: integrate is patrol's
own move from the CRs' state. The replay half (evals/replay/cases/C30)
seeds two integrate-ready issues at N=1.
"""

from lib.lintkit import c, dirs_text, read, section, src

META = {
    "id": "C30",   # the row lives in evals/replay/cases/C30/case.json (lint + replay)
}

_pm = read("commands/patrol.md")
_rep = " ".join(section(_pm, r"^## 4\. Report", r"^## 5\. ").split())

c.expect("pattern", "C30: patrol §4 — every unreached actionable row is queued, never in progress",
         "**Every** `actionable:` row the pass did not reach — the N exhausted above it — "
         "is `queued: <action>`, never `in progress`" in _rep)
c.expect("pattern", "C30: patrol §4 — the (6) row's clause is the literal `queued: integrate`",
         "An in-flight row has no tail — `queued: integrate`" in _rep)
c.expect("pattern", "C30: patrol §4 — an in-flight queued row has no tail (no label event to read)",
         "there is no label event to read an age from" in _rep)
c.expect("pattern", "C30: patrol §4 — there is no label for (6); the road is the row's action",
         "there is no label for (6)" in _rep
         and "then `integrate`, each patrol's own move from the CRs' state" in _rep)
src("C30: workflow's owner table has the (6) row — integrate, no gate label",
    "references/workflow.md",
    "| QA CR audited and thread-clean → the (6) verdict run | `integrate` (patrol's "
    "`integrate` row) — no gate label: there is no \"go integrate\" signal; a pass that does "
    "not reach it reports `queued: integrate` (#207) |")
c.expect("pattern", "C30: workflow's invocation policy — what a pass does not reach is queued",
         "what it does not reach is `queued: <action>` in its report"
         in " ".join(read("references/workflow.md").split()))
c.expect("pattern", "C30: README's patrol paragraph says it",
         "shows as `queued: <action>` in the report, `queued: integrate` included: there is no "
         "label for (6)" in " ".join(read("README.md").split()))
src("C30: tip's in-flight (4) row — your move is nothing, there is no label for (6)",
    "commands/tip.md",
    "the QA CR open (in flight, (4)) | nothing — there is no label for (6) — unless")
c.expect("pattern", "C30: no surface names a `status: integrate` label (option (b) was not taken)",
         "`status: integrate`" not in dirs_text("commands", "references", "templates", "docs")
         and "`status: integrate`" not in read("README.md"))
