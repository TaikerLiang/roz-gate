"""D20 · the QA blindness rule: invariant, allowed, forbidden — apart  (#261)
#199 showed two models failing the same paragraph in different ways: one on
what the rule means, one on what it may touch. The blindness rule in
`references/qa-brief.md` § Inputs therefore carries its semantic invariant
and its operational boundary as separate clauses — **Invariant.**,
**Allowed.**, **Forbidden.** — so a failure can be attributed to one of
them. This case pins the structure only, never the wording (#262 and #263
will reshape the sentences): the three labels exist inside the section, in
that order, and rule E's enforcement sentence (D8's literal) is still
there. The split preserves A0's contract exactly (#261 ruling: no allowed
or forbidden action added, removed or broadened); replay D10–D19 under
`--variant A0` vs A measure the effect.
"""

import re

from lib.lintkit import c, read

META = {
    "id": "D20",
    "title": "The QA blindness rule states its invariant, what is allowed and what is forbidden "
             "as separate clauses",
    "tier": "lint (#261)",
    "ledger": "`references/qa-brief.md` § Inputs — and the blindness rule carries **Invariant.**, "
              "**Allowed.** and **Forbidden.**, in that order, inside the section, and rule E's "
              "enforcement sentence is still there — structure pinned, wording free (#261: a "
              "failure can be attributed to one clause only if the clauses exist apart).",
}

LABELS = ("**Invariant.**", "**Allowed.**", "**Forbidden.**")
ENFORCE = ("guard-blind rule E (the marker's `seat=qa` line) denies every\n"
           "read of `src/` outside `<acceptance_dir>` and the declared port")

_text = read("references/qa-brief.md")
_m = re.search(r"^## Inputs — and the blindness rule\s*$(.*?)(?=^## |\Z)", _text, re.M | re.S)
_sec = _m.group(1) if _m else ""
c.expect("pattern", "D20: the brief has § Inputs — and the blindness rule", bool(_sec))

_at = []
for lab in LABELS:
    n = _sec.count(lab)
    c.expect("pattern", "D20: %s appears exactly once in § Inputs (found %d)" % (lab, n), n == 1)
    _at.append(_sec.find(lab))
c.expect("pattern", "D20: the labels run Invariant → Allowed → Forbidden",
         all(x >= 0 for x in _at) and _at == sorted(_at))
c.expect("pattern", "D20: each label opens its own paragraph",
         all(re.search(r"(^|\n\n)%s " % re.escape(lab), _sec) for lab in LABELS))
c.expect("pattern", "D20: rule E's enforcement sentence is still in § Inputs", ENFORCE in _sec)
