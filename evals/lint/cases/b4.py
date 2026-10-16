"""B4 · an agent write never opens with a quote block        (defect: 1.11.0-)
Static layer: the write rules must be stated where writes happen. Teeth
since 1.14.0: guard-gate rule C denies the quote-opening marker-carrying
comment itself (proven in hooks/tests/, run by the same
release gate).
"""

from lib.lintkit import src

META = {
    "id": 'B4',
    "title": 'an agent write never opens with a quote block',
    "tier": 'lint (defect 1.11.0-) + hook (guard-gate rule C)',
    "ledger": None,
}

src("B4: question comments must open with the marker",
    "commands/next-stage.md", "MUST start with `**[")
src("B4: the quote-block opening is forbidden in review replies",
    "commands/review-answers.md", "Never open with a quote block")
