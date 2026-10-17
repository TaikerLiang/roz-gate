"""C22 · the implementation review has a record; review-clean = record + zero threads (#140, 2.0.0)
#95 taught it on the QA side: "zero open fidelity threads" was true of an
audit that found nothing and of an audit that never ran. The 2.0 landing of
the implementation on the spec branch keys on review-clean, so the same
hole opens there unless review-clean is positive evidence: the
`**[reviewer] · code-review**` record with `reviewed-sha` equal to the CR
head, plus zero threads. Defined once in workflow.md (5), read by B2.1,
integrate §1, the scanner, tip; patrol's code-review action runs the review
that never ran. Replay C22/C23 measure the two behaviours.
"""

from lib.lintkit import must_not_match, read, src

META = {
    "id": 'C22',
}

_MARK = "**[reviewer] · code-review**"
src("C22: workflow (5) defines review-clean once", "references/workflow.md",
    "**Review-clean**\nmeans exactly three things, defined here and read everywhere else")
src("C22: workflow (5) names the record", "references/workflow.md",
    "`%s` carrying `reviewed-sha: <CR head SHA>`" % _MARK)
src("C22: workflow (5) — zero threads alone is not review-clean", "references/workflow.md",
    "Zero threads alone is not review-clean")
src("C22: B5 posts the record last, even with zero findings", "commands/next-stage.md",
    "**The record — posted last, even with zero findings**")
src("C22: B5 names the marker", "commands/next-stage.md",
    "CR-COMMENT opening with `%s`" % _MARK)
src("C22: B2.1 requires the record with the head sha", "commands/next-stage.md",
    "CR-COMMENTS-LIST carries a `%s`\n  comment whose `reviewed-sha:` equals the CR's head" % _MARK)
src("C22: B2.1 never merges on zero threads alone", "commands/next-stage.md",
    "never merge on\n  zero threads alone")
src("C22: C6 posts the same record on the fast CR", "commands/next-stage.md",
    "**and the\n  same record**: one top-level `%s` comment" % _MARK)
src("C22: integrate §1 requires the record, open or merged", "commands/integrate.md",
    "CR-COMMENTS-LIST\n  carries a `%s` comment whose `reviewed-sha:` is\n  the CR's head" % _MARK)
src("C22: integrate's stop names patrol as the road", "commands/integrate.md",
    "**No record, or a\n  stale one → stop: no code review on record — patrol runs it")
src("C22: the scanner reads the record and the head", "references/patrol-scan.md",
    "review-clean is the `%s` comment present with its `reviewed-sha:` equal to the CR head"
    % _MARK)
src("C22: the scanner routes a missing or stale record to code-review", "references/patrol-scan.md",
    "**no record or a stale one** (`reviewed-sha` ≠ head) → actionable → **code-review**")
src("C22: the fast row needs the record before the hand-off", "references/patrol-scan.md",
    "review-clean (record current, zero threads) → verdict `hand-off: in-user-review`")
src("C22: the verdict vocabulary carries code-review", "references/patrol-scan.md",
    "`actionable: code-review`")
must_not_match("C22: the old integrate clause — zero threads alone — is gone from the scan row",
               r"Implementation CR exists with \*\*zero open review threads\*\* AND",
               read("references/patrol-scan.md"))
src("C22: patrol has the code-review action", "commands/patrol.md",
    "### The code-review action — the review that never ran (or never re-checked)")
src("C22: the action posts the record last with the head", "commands/patrol.md",
    "`%s` record with `reviewed-sha: <head>` and the\n   counts" % _MARK)
src("C22: address-review re-stamps the record on the last resolve", "commands/patrol.md",
    "COMMENT-EDITs the CR's\n   `%s` record so its `reviewed-sha:` is the head" % _MARK)
src("C22: patrol ranks code-review after fidelity-audit", "commands/patrol.md",
    "fidelity-audit > code-review >")
src("C22: tip reads the record", "commands/tip.md",
    "CR-COMMENTS-LIST for a `%s` comment and whether\n  its `reviewed-sha:` is the branch's head"
    % _MARK)
src("C22: README's (5) row names the record", "README.md",
    "plus the `%s` record (`reviewed-sha`); review-clean = record current + zero threads" % _MARK)
src("C22: the index's (5) card names the record", "docs/index.html",
    "one <code>**[reviewer] · code-review**</code> comment with <code>reviewed-sha</code>")
