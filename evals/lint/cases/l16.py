"""L16 · the integrate precondition codes have one table              (#134)
`references/roz-check.md` and `hooks/state_check.py` both list the rules
`bin/roz-check integrate` applies, and each rule stands for a sentence of
`commands/integrate.md` § 1. Three copies of one rule set drift, so:
- the codes and prerequisites in the document equal the module's, in order;
- the four rule statuses and three verdicts in the document are the module's;
- every rule's § 1 sentence (the module's anchor) is still a literal of
  `commands/integrate.md`, whitespace aside — a change to § 1's wording
  without a look at the rule fails here.
"""

import os
import re
import sys

from lib.lintkit import R, c, read

META = {
    "id": "L16",
    "title": "the integrate precondition codes have one table",
    "tier": "lint (#134)",
    "ledger": "The rule codes and prerequisites of `references/roz-check.md` § integrate equal "
              "`hooks/state_check.py`'s, in order; its statuses and verdicts are the module's; "
              "and every rule's anchor is still a sentence of `commands/integrate.md` § 1 — a "
              "precondition reworded in the prose and not in the rule fails.",
}

DOC = "references/roz-check.md"


def flat(s):
    return " ".join(s.split())


def section(text, heading):
    m = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    return m.group(1) if m else ""


def rows(body):
    out = []
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[-\s|]+\|$", line):
            out.append([x.strip() for x in re.split(r"(?<!\\)\|", line)[1:-1]])
    return out[1:]


_have = os.path.exists(os.path.join(R, DOC))
c.expect("pattern", "L16: %s exists" % DOC, _have)
_text = read(DOC) if _have else ""
try:
    sys.path.insert(0, os.path.join(R, "hooks"))
    import state_check as ck
except ImportError:
    ck = None
finally:
    sys.path.pop(0)
c.expect("pattern", "L16: hooks/state_check.py imports", ck is not None)

if ck is not None:
    want = [(code, req) for code, req, _rule, _src in ck.INTEGRATE]
    got = [(re.sub(r"`", "", r[0]), re.sub(r"`", "", r[2]) if r[2] != "—" else None)
           for r in rows(section(_text, "integrate")) if len(r) == 3]
    c.expect("pattern", "L16: § integrate lists the module's %d rules and prerequisites, in "
             "order (doc only: %s; module only: %s)"
             % (len(want), ", ".join(sorted(str(x) for x in set(got) - set(want))) or "none",
                ", ".join(sorted(str(x) for x in set(want) - set(got))) or "none"), got == want)
    sts = {re.sub(r"`", "", r[0]) for r in rows(section(_text, "A rule's four statuses"))}
    c.expect("pattern", "L16: the document's rule statuses are the module's",
             sts == set(ck.STATUSES))
    c.expect("pattern", "L16: the document names the module's verdicts and schema",
             all("`%s`" % v in _text for v in ck.VERDICTS) and '"%s"' % ck.SCHEMA in _text)
    _sec1 = flat(section(read("commands/integrate.md"), "1. Preconditions (read-only)"))
    for code, _req, _rule, src in ck.INTEGRATE:
        c.expect("pattern", "L16: %s still quotes commands/integrate.md § 1 — %s"
                 % (code, src[:60]), flat(src) in _sec1)
    c.expect("pattern", "L16: § 1 has no `Verify` bullet without a rule",
             _sec1.count("Verify the **") == sum(1 for _c, _r, _f, s in ck.INTEGRATE
                                                 if s.startswith("Verify the **")) + 1)
