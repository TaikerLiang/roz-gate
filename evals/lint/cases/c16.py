"""C16 · a QA CR without a fidelity audit on record never integrates (defect 1.9.0-, #95)
integrate's precondition was "zero open fidelity threads" — satisfied by an
audit that found nothing AND by an audit that never ran (B5b stopped before
the reviewer posted; ADMC #73). The brief's summary comment now opens with
`**[reviewer] · fidelity**` — the record that the audit ran — and the record
is required where the threads were: integrate step 1, the scan's in-flight
row (which routes a QA CR without it to patrol's new fidelity-audit action),
next-stage B5b, workflow (5q). Replay C16/C17 prove the two behaviours.
"""

from lib.lintkit import must_not_match, read, src

META = {
    "id": 'C16',
}

_MARK = "**[reviewer] · fidelity**"
src("C16: the brief's summary comment opens with the marker", "references/fidelity-brief.md",
    "opening with `%s`" % _MARK)
src("C16: the brief calls the comment the record", "references/fidelity-brief.md",
    "That comment is the record that the audit ran")
src("C16: the record is the dispatch's last write (codex review, PR #102)",
    "references/fidelity-brief.md", "**Post it\n  last**: every finding thread first")
src("C16: integrate step 1 requires the record", "commands/integrate.md",
    "Verify the **QA CR carries a `%s` comment**" % _MARK)
src("C16: integrate's stop names patrol as the road", "commands/integrate.md",
    "no fidelity audit on\n  record — patrol runs it")
src("C16: the scan row routes a QA CR without the record to fidelity-audit",
    "references/patrol-scan.md",
    "carries **no** `%s` comment (CR-COMMENTS-LIST on it" % _MARK)
src("C16: the scan row's integrate clause carries the record", "references/patrol-scan.md",
    "carries the `%s` record and has zero open fidelity threads**" % _MARK)
must_not_match("C16: the scan row's integrate clause never stands without the record",
               r"is not a draft, and has zero open fidelity threads\*\* → actionable → "
               r"`/roz-gate:integrate",
               read("references/patrol-scan.md"))
src("C16: patrol ranks fidelity-audit after address-review", "commands/patrol.md",
    "address-review >\nfidelity-audit > `/roz-gate:spec-answers`")
src("C16: patrol has the fidelity-audit action", "commands/patrol.md",
    "### The fidelity-audit action — the audit that never ran")
src("C16: the action is B5b's dispatch procedure, marker with the bound ref", "commands/patrol.md",
    "**The fidelity-dispatch procedure** (next-stage.md B5b, verbatim)")
src("C16: a re-check posts no second record", "commands/patrol.md",
    "A re-check\n   posts no second summary")
src("C16: next-stage B5b names the marker", "commands/next-stage.md",
    "plus one top-level summary comment opening with `%s`" % _MARK)
src("C16: next-stage B6 routes the unrecorded QA CR to patrol", "commands/next-stage.md",
    "record is patrol's `fidelity-audit`")
src("C16: workflow (5q) calls the summary the record", "references/workflow.md",
    "is the record that the audit ran: (6) requires it")
src("C16: the index (5q) card names the record", "docs/index.html",
    "summary is the record that the audit ran")
