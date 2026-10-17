"""E9 · QA's contract review reaches the holder as [qa] spec-CR threads  (#140 ruling 3, 2.0.0)
QA starts after the implementation lands and reads the contract as built
first; a contradiction with a spec rule, an untestable clause, a Given with
no control point is a question for the holder — posted by the main agent as
a `[qa]` thread on the spec CR through the (2a) machinery, never interpreted
into a test, never left in QA's report where no gate reads it. Replay E9
measures the run; this case holds the statements.
"""

from lib.lintkit import src

META = {
    "id": 'E9',
}

src("E9: the QA brief's step zero is the contract review", "references/qa-brief.md",
    "## Step zero — the contract review")
src("E9: the brief gives the finding the question shape", "references/qa-brief.md",
    "`**[qa] · Q<k> · <2–3-word\nlabel>**`")
src("E9: the brief — QA does not stop on a finding", "references/qa-brief.md",
    "You\ndo not stop on a finding")
src("E9: B2.5 appends the item to spec.md's Open Questions", "commands/next-stage.md",
    "append each item to `spec.md`'s `## Open Questions`")
src("E9: B2.5 posts the threads on the spec CR", "commands/next-stage.md",
    "THREAD-POST-INLINE each item verbatim on the spec CR")
src("E9: B2.5 applies the backward transition", "commands/next-stage.md",
    "LABEL-ADD\n`status: in-spec-review`: the backward transition")
src("E9: B2.6 — ready only with no [qa] thread open", "commands/next-stage.md",
    "CR-READY only\n  if `qa` reported its suite complete **and** B2.5 posted no thread")
src("E9: spec-answers resumes qa after a [qa] finding", "commands/spec-answers.md",
    "QA's `[qa]` contract-review findings")
src("E9: spec-answers readies only with no [qa] thread open", "commands/spec-answers.md",
    "**and no `[qa]` thread is still open**")
src("E9: workflow's qa row names the contract review", "references/workflow.md",
    "a **contract review** of `spec.md` + the as-built `technical-spec.md` first")
src("E9: workflow (4) routes the findings", "references/workflow.md",
    "the main agent posts them as `[qa]` threads on\n  the spec CR and applies `in-spec-review`")
src("E9: tip names the [qa] thread", "commands/tip.md",
    "or a `[qa]` thread on the spec CR is yours to answer")
src("E9: the onboarding stop shape names it", "docs/onboarding.html",
    "or its contract review found something — a <code>[qa]</code> thread on the spec CR")
