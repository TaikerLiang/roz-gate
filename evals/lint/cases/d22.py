"""D22 · a Given with no control point is a finding, never arranged by hand  (#197)
A seat that guesses a setup path hides the contract defect it walked past.
The facts QA needs to drive a scenario each have one home, written down in
`references/workflow.md` § Principles as one table — the config block, the
Glossary, the `**Test port**` line, §5, the project's own docs — and the QA
brief names a Given with no control point a *port gap*: a finding. Replay
D22 measures the run (a hole in §5), D23 its pair (the hole filled); this
case holds the statements.
"""

import re

from lib.lintkit import c, read, src

META = {
    "id": "D22",
}

HOMES = ("the config block: `test`, `acceptance_dir`, `acceptance_test`",
         "`spec.md` § Glossary",
         "the `**Test port**` line",
         "`technical-spec.md` §5",
         "the project's own docs")

src("D22: the QA brief names a Given with no control point a port gap", "references/qa-brief.md",
    "a **port gap**: a Given clause with no seed/setup control point")
src("D22: the QA brief — a Given with none is a finding, never a workaround",
    "references/qa-brief.md", "a Given with none is a finding (above), never a\n  workaround")
src("D22: workflow carries the shared-fact table", "references/workflow.md",
    "**Where a shared fact lives** (#197)")

_text = read("references/workflow.md")
_at = _text.find("**Where a shared fact lives**")
_m = re.search(r"\n\n((?:  \|[^\n]*\n)+)", _text[_at:]) if _at >= 0 else None
_rows = [ln.strip() for ln in (_m.group(1).splitlines() if _m else [])][2:]  # header, rule
c.expect("pattern", "D22: the shared-fact table has five rows (found %d)" % len(_rows),
         len(_rows) == 5)
for _home in HOMES:
    c.expect("pattern", "D22: a shared-fact row's home is %s" % _home,
             any(r.endswith("| %s |" % _home) for r in _rows))
