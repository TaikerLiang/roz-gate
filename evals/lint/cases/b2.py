"""B2 · a line-wrapped tag survives the check                (defect: 1.12.0-)
Checks match the OPENING TOKEN only; a wrapped tag is present, never absent.
"""

from lib.lintkit import c, fixture, must_not_match, src

META = {
    "id": 'B2',
    "title": 'a line-wrapped tag survives the check',
    "tier": 'lint (defect 1.12.0-)',
    "ledger": None,
}

c.expect("pattern", "B2 pattern: wrapped (assumed-empirical: detected",
         "(assumed-empirical:" in fixture("b2_wrapped_assumed.md"))
c.expect("pattern", "B2 pattern: wrapped (measured read as present",
         "(measured" in fixture("b2_wrapped_measured.md"))
# The anti-pattern this rule forbids — requiring the closing paren on the
# same line — misses exactly the wrapped tag. Kept as executable rationale.
# ([^)\n]: grep is line-scoped; Python's [^)] would cross the wrap and
# defeat the very subtlety this check demonstrates.)
must_not_match("B2 rationale: same-line-paren matching would miss it",
               r"\(measured[^)\n]*\)", fixture("b2_wrapped_measured.md"))
src("B2 conformance: the opening-token rule names all three tokens",
    "commands/next-stage.md", "`(unverified)`, `(assumed-empirical:`, `(measured`")
src("B2 conformance: opening-token-only is stated as the rule",
    "commands/next-stage.md", "matches the **opening token only**")
