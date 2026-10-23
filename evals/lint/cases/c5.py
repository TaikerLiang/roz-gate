"""C5 · the post-integration re-entry is honest about what it verified (defect 1.11.0-, #97)
A (7) amendment that changed what a rule means was folded, the suite re-run
— green against the PREVIOUS text, which code and suite still implement —
and the cards regenerated from that green: laundering, the thing the
fidelity audit exists for. The re-entry now has two cases; the behaviour
change takes no run as evidence, regenerates nothing, and says so in the
return comment; review-answers closes the loop when the code catches up;
the hand-back rule names the exception. Replay C5 proves the behaviour.
"""

from lib.lintkit import must_not_match, read, src

META = {
    "id": 'C5',
}

src("C5: the re-entry has a no-behaviour case", "commands/spec-answers.md",
    "**The fold changed no behaviour**")
src("C5: the behaviour case takes no run as evidence", "commands/spec-answers.md",
    "**do not run it as evidence, do not regenerate the cards,\n    do not re-stamp `cards-sha`**")
src("C5: the return comment opens with its marker", "commands/spec-answers.md",
    "`**[spec-answers] · amended**`")
src("C5: the return comment says what still implements the previous text",
    "commands/spec-answers.md",
    "*the implementation and\n  the suite still implement the previous text*")
src("C5: the return comment names the three catch-up moves", "commands/spec-answers.md",
    "`implementer` catch-up on `<spec-branch>`")
must_not_match("C5: the retired single-case paragraph is gone",
               r"if the amendment changed behaviour, honour the\n  \*\*hand-back rule\*\*",
               read("commands/spec-answers.md"))
src("C5: review-answers re-derives and re-checks when the code implements an amended rule",
    "commands/review-answers.md", "A code change that **implements an amended rule**")
src("C5: review-answers orders the re-check before the cards", "commands/review-answers.md",
    "and only then does the hand-back run\n  regenerate the cards")
src("C5: the hand-back rule names the exception", "references/workflow.md",
    "One re-application\ncarries no run")
src("C5: the gate kit calls the staleness by design", "references/gate-kit.md",
    "leaves them stale **by design**")
src("C5: on re-entry the fold raises no new thread (#193, ruling (b))",
    "commands/spec-answers.md",
    "**On a post-integration re-entry the fold raises no new thread**")
src("C5: step 7 lists a surfaced question in the return comment (#193)",
    "commands/spec-answers.md",
    "The fold raised no new thread (step 5); a question it\n"
    "  surfaced is listed in the return comment")
