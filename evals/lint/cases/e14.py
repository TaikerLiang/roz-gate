"""E14 · the QA persona: no stop-before-testing, no one-question-at-a-time  (#267)
`agents/qa.md` is the QA subagent's system prompt on every QA dispatch, and
it contradicted the brief's step zero (#243, #262): "stop and flag it …
before writing any test", "ask one sharp question at a time", and a
`grill-me` row that asked questions "before writing anything", one at a
time — while step zero says a finding does not stop you, a drivable
scenario gets its test now, and findings return in one batch. Every #199
cell ran under that persona. The persona keeps character and stance; the
procedure is the brief's. This case holds the contradicting literals
absent, the `grill-me` row returning questions in one batch, and § Who You
Are still saying an ambiguity is a finding.
"""

from lib.lintkit import c, read

META = {
    "id": "E14",
    "title": "The QA persona never tells the seat to stop before writing tests or to ask one "
             "question at a time",
    "tier": "lint (#267)",
    "ledger": "`agents/qa.md` carries none of `before writing any test`, `before writing "
              "anything`, `one sharp question at a time`, `one sharp either/or question at a "
              "time`; its `grill-me` row returns questions `in one batch`; § Who You Are keeps "
              "`An ambiguity is a finding like any other` (#267: the persona is the seat's "
              "system prompt and contradicted step zero).",
}

PERSONA = "agents/qa.md"
ABSENT = ("before writing any test", "before writing anything",
          "one sharp question at a time", "one sharp either/or question at a time")

_flat = " ".join(read(PERSONA).split())
for lit in ABSENT:
    c.expect("pattern", "E14: the QA persona does not say %r" % lit, lit not in _flat)
c.expect("pattern", "E14: the grill-me row returns every question with the other findings, "
         "in one batch", "goes back with your other findings, in one batch" in _flat)
c.expect("pattern", "E14: § Who You Are still makes an ambiguity a finding",
         "An ambiguity is a finding like any other" in _flat)
