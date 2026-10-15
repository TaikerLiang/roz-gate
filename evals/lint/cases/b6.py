"""B6 · `unverified` is a reserved word                       (defect 1.36.1-, #123)
A spec document carries the word only as the evidence tag. ADMC's
technical-spec.md wrapped the prose "(not citing #8's claim unverified)"
so that `unverified` opened a line, and the 1.12.0 tag-position grep read
it as a wrap-split tag — a hit the author called a false positive. Paul's
ruling: the word is reserved, like `import` in a program; prose says "not
yet measured" or "asserted", the checks match the whole word anywhere, so
the word in prose stops the gate like a tag and the remedy is to reword.
"""

from cases.b1 import UNV
from lib.lintkit import fixture, must_match, must_not_match, src

META = {
    "id": 'B6',
    "title":
        '`unverified` is a reserved word — a spec document carries it only as the evidence tag;'
        ' the Path B and promote checks match the whole word anywhere, so the word in prose '
        '(line-initial after a wrap, mid-sentence, capitalised) stops the gate like a tag and '
        'the remedy is to reword; `unverifiable` / `verified` are not hits',
    "tier": 'lint (defect 1.36.1-, #123)',
    "ledger": None,
}

must_match("B6 pattern: ADMC's line-initial prose wrap is a hit", UNV,
           fixture("b6_prose_wrap.md"))
must_match("B6 pattern: the word mid-sentence is a hit", UNV, fixture("b6_prose_midline.md"))
must_match("B6 pattern: a sentence-initial capital is a hit", UNV,
           fixture("b6_prose_capital.md"))
must_not_match("B6 pattern: unverifiable / verified are not hits (word boundary)", UNV,
               fixture("b6_clean.md"))
src("B6 conformance: A3 states the reserved word", "commands/next-stage.md",
    "**`unverified` is a reserved word** in every\n    spec document: it appears only as this tag")
src("B6 conformance: A3 says the whole word anywhere stops the gate", "commands/next-stage.md",
    "the checks match the whole word anywhere")
src("B6 conformance: Path B names reword as the prose remedy", "commands/next-stage.md",
    "the word in prose: reword\nthe sentence")
src("B6 conformance: the promote check names reword as the prose remedy",
    "commands/spec-answers.md", "or reword prose")
src("B6 conformance: the fold rule states the reserved word", "commands/spec-answers.md",
    "`unverified` is a\n     reserved word")
