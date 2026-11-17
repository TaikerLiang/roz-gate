"""B10 · the evidence remedy is a per-hit review                         (#256)
Path B's reserved-word STOP named the remedy by the hit's form — a tag:
measure or demote; prose: reword — never by what the claim does to the
contract. On an external project's #35 (reported as #255) the STOP
recommended demoting all four hits, including the premise a p95 budget
rested on, and F5 was green: any comment with "measure" or
"assumed-empirical" passed. The ruling: one table row per hit
(`hit` · `clause` · `kind` · `unknown` · `if false` · `action`), the
action one of four, `accept a bounded risk` only when nothing depends on
the claim (A3's condition), and a fold never applies a demotion a
guarantee needs. This case holds the table, the four actions and the
condition in Path B, the promote check's pointer to it, the fold rule, and
A3's sentence — and the old two-remedy wording absent.
#364: "is not folded … the fold asks once (below)" sent seats to a depth
rule written for a fold that happened, and E15 asked the follow-up as a
reply in Q1's thread. The rule now says where it goes: a new `Q<k>` raised
by the fold of Q<j>, its own thread at depth 0, never a reply in Q<j>'s.
"""

from lib.lintkit import c, read

META = {
    "id": "B10",
    "title": "The reserved-word STOP reviews each hit against the contract",
    "tier": "lint (#256)",
    "ledger": "`references/next-stage-path-b.md` § Reserved-word check carries the six columns "
              "(`hit`, `clause`, `kind`, `unknown`, `if false`, `action`), the four actions "
              "(`correct the spec`, `measure`, `accept a bounded risk`, `reword`) and the "
              "condition on `accept a bounded risk`; the promote check points at that table; "
              "spec-answers' fold rules carry *A demotion a guarantee needs is not folded*, its "
              "question a new `Q<k>` *raised by the fold of Q<j>* with its own thread at depth 0, "
              "never a reply in Q<j>'s thread (#364); A3 "
              "makes `(assumed-empirical:` legal only when nothing depends on the claim (#256: "
              "the STOP recommended demoting all four hits, a p95 premise among them).",
}

PATH_B = "references/next-stage-path-b.md"
SPEC_ANSWERS = "commands/spec-answers.md"
A3 = "references/next-stage-path-a.md"


def flat(text):
    return " ".join(text.split())


_b = read(PATH_B)
_start, _end = _b.find("**Reserved-word check"), _b.find("**Test-port check")
_section = flat(_b[_start:_end]) if 0 <= _start < _end else ""
c.expect("pattern", "B10: Path B has a § Reserved-word check before § Test-port check",
         bool(_section))
# each column is anchored on its definition, so a column name used elsewhere
# in the paragraph (`if false` in the condition) cannot stand in for it
for col in ("hit", "clause", "kind", "unknown", "if false"):
    c.expect("pattern", "B10: the per-hit table defines the column `%s`" % col,
             "`%s` (" % col in _section)
c.expect("pattern", "B10: the per-hit table defines the column `action`, one of four",
         "`action`, exactly one of" in _section)
for act in ("correct the spec", "measure", "accept a bounded risk", "reword"):
    c.expect("pattern", "B10: the table's actions include `%s`" % act, "`%s`" % act in _section)
c.expect("pattern", "B10: `accept a bounded risk` only when `if false` is none (A3)",
         "`accept a bounded risk` (demote to `(assumed-empirical: <named risk>)`, only when "
         "`if false` is none — A3)" in _section)
c.expect("pattern", "B10: the action comes last, after the review columns",
         "filled left to right so the action comes last" in _section)
c.expect("pattern", "B10: never one action for every hit; the holder rules each row",
         "never one action for all; the gate holder rules every row" in _section)
c.expect("pattern", "B10: the old form-keyed remedy (a tag: measure … or demote) is gone",
         "a tag: measure" not in _section and "or demote to" not in _section)

_s = flat(read(SPEC_ANSWERS))
c.expect("pattern", "B10: the promote check points at Path B's table by path",
         "one row per hit in Path B's table, `references/next-stage-path-b.md` § "
         "Reserved-word check" in _s)
c.expect("pattern", "B10: the promote check's old remedy parenthesis is gone",
         "(measure, demote to" not in _s)
c.expect("pattern", "B10: the fold rules carry the not-folded rule",
         "**A demotion a guarantee needs is not folded**" in _s)
c.expect("pattern", "B10: the refused demotion keeps the tag and the clause byte-identical",
         "leaves the premise `(unverified)` and that clause byte-identical" in _s)
c.expect("pattern", "B10: the refused demotion asks once — measure or correct",
         "keep `<id>` and measure, or correct `<id>`" in _s)
c.expect("pattern", "B10: the refused demotion's question is a new item raised by the fold (#364)",
         "the fold asks once — keep `<id>` and measure, or correct `<id>` — as a new `Q<k>` "
         "*raised by the fold of Q<j>* (depth rule below; depth 0: its own thread)" in _s)
c.expect("pattern", "B10: the refused demotion's question is never a reply in Q<j>'s thread (#364)",
         "never as a reply in Q<j>'s thread" in _s)

c.expect("pattern", "B10: A3 makes the demotion legal only when nothing depends on the claim",
         "Legal only when nothing in a guarantee, scenario or acceptance criterion depends on "
         "the claim" in flat(read(A3)))
