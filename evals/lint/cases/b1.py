"""B1 · a compound tag evades the literal it contains        (defect: 1.12.0-)
Canonical unverified-claim pattern since 1.37.0: the whole word, anywhere,
any case. `unverified` is reserved for the evidence tag (B6), so its own
tag, one merged into another parenthesis and a wrap-split compound are
the same hit — no tag position to compute, nothing a line break can hide.
(1.12.0–1.36.1 matched tag position — start of line, or after ( or , —
and read a wrapped prose line as a tag: #123.)
"""

from lib.lintkit import c, dirs_text, fixture, must_match, must_not_match, src

META = {
    "id": 'B1',
    "title": 'a compound tag evades the literal it contains',
    "tier": 'lint (defect 1.12.0-)',
    "ledger": None,
}

UNV = r"(?i)\bunverified\b"
must_match("B1 pattern: compound (from Q4, unverified) found",
           UNV, fixture("b1_compound.md"))
must_match("B1 pattern: conventional (unverified) found",
           UNV, fixture("b1_plain.md"))
must_match("B1 pattern: wrap-split compound found",
           UNV, fixture("b1_wrapped.md"))
must_not_match("B1 pattern: prose without the word NOT flagged",
               UNV, fixture("b1_negative.md"))
src("B1 conformance: Path B check carries the whole-word grep",
    "commands/next-stage.md", "grep -nwi unverified <specs_dir>/<n>/*.md")
src("B1 conformance: promote check carries the whole-word grep",
    "commands/spec-answers.md", "grep -nwi unverified <specs_dir>/<n>/*.md")
c.expect("pattern", "B1 conformance: no site greps the bare literal or the tag-position form",
         "grep -n '(unverified)'" not in dirs_text("commands", "references")
         and "[(,])[[:space:]]*unverified" not in dirs_text("commands", "references"))
