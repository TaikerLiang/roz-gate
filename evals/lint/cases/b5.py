"""B5 · the must-read stays on top and within budget           (defect: 1.19.0-)
Issue #42: agent-written documents grew until the human skipped them. Each
producing brief now states a budget — what is must-read, what folds into a
<details> supplement, and a cap on the must-read. The cap is one predicate,
held here and quoted by the briefs; the briefs carry the fold instruction.
"""

from lib.lintkit import c, fixture, src

META = {
    "id": 'B5',
    "title": 'the must-read stays on top and within budget',
    "tier": 'lint (defect 1.19.0-)',
    "ledger": None,
}

SUMMARY_CAP, STOP_CAP, PHONE_WIDTH = 25, 12, 60


def must_read_lines(doc):
    """Rendered lines before the first `<details` — the part a phone shows
    unfolded, at PHONE_WIDTH characters per line, so a long source line
    counts for several (codex review, PR #52). A document with no
    supplement is all must-read."""
    head = doc.split("<details", 1)[0]
    return sum(-(-len(ln.strip()) // PHONE_WIDTH) for ln in head.splitlines() if ln.strip())


c.expect("pattern", "B5 pattern: a summary within the cap counts its must-read only",
         must_read_lines(fixture("b5_within.md")) <= SUMMARY_CAP)
c.expect("pattern", "B5 pattern: a must-read over the cap is over",
         must_read_lines(fixture("b5_over.md")) > SUMMARY_CAP)
c.expect("pattern", "B5 pattern: no supplement at all means the whole document is must-read",
         must_read_lines(fixture("b5_no_supplement.md")) > SUMMARY_CAP)
c.expect("pattern", "B5 pattern: few source lines that wrap on a phone are over the cap",
         must_read_lines(fixture("b5_wrapped.md")) > SUMMARY_CAP)
src("B5 conformance: the intake summary states its cap",
    "references/intake-brief.md",
    "at most %d rendered lines before the first `<details>`" % SUMMARY_CAP)
src("B5 conformance: the intake summary states the phone width the cap is rendered at",
    "references/intake-brief.md", "~%d characters per line" % PHONE_WIDTH)
src("B5 conformance: the intake summary names its supplement block",
    "references/intake-brief.md",
    "<details><summary>Supplement — context and decision trail</summary>")
src("B5 conformance: the questions batch states its per-question budget",
    "references/intake-brief.md", "at most 6 visible lines per question")
src("B5 conformance: the STOP protocol states its cap",
    "references/workflow.md", "at most %d rendered lines before the first `<details>`" % STOP_CAP)
for _f in ("references/workflow.md", "commands/next-stage.md", "commands/integrate.md",
           "commands/spec-answers.md", "commands/patrol.md"):
    src("B5 conformance: %s folds STOP evidence" % _f, _f, "<details><summary>Evidence</summary>")
src("B5 conformance: A3 states the spec documents' must-read sections",
    "commands/next-stage.md",
    "`## Rules`, `## Scenarios`, `## Open Questions`, with **at most 3 lines")
src("B5 conformance: A3 names the spec supplement block",
    "commands/next-stage.md", "`## Supplement` section whose body is one")
src("B5 conformance: B3 folds test-spec narrative",
    "commands/next-stage.md", "`test-spec.md` keeps the **must-read on top**")
src("B5 conformance: the patrol report keeps the table and queue as must-read",
    "commands/patrol.md", "trailing `## Details` heading after")
