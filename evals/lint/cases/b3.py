"""B3 · the marker convention is identical everywhere        (preventive)
Canonical marker literals: '**[' (agent write opens) and '✅ [' (resolution).
The sentences stating the convention legitimately differ; the LITERALS may
not. Near-miss variants (no space, fullwidth bracket) must not exist.
"""

from lib.lintkit import c, dirs_text, must_not_match, src

META = {
    "id": 'B3',
    "title": 'the marker convention is identical everywhere',
    "tier": 'lint (preventive)',
    "ledger": None,
}

for f in ("commands/next-stage.md", "commands/patrol.md",
          "commands/spec-answers.md", "commands/review-answers.md"):
    src("B3: %s carries the '**[' marker literal" % f, f, "**[")
for f in ("references/patrol-scan.md", "commands/spec-answers.md",
          "commands/review-answers.md"):
    src("B3: %s carries the '✅ [' marker literal" % f, f, "✅ [")
B3_DIRS = ("commands", "references", "agents", "templates")
c.expect("pattern", "B3: no '✅[' (missing space) anywhere",
         "✅[" not in dirs_text(*B3_DIRS))
must_not_match("B3: no fullwidth-bracket marker variant anywhere",
               r"✅ ?【|\*\*【", dirs_text(*B3_DIRS))
