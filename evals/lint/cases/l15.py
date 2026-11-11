"""L15 · the roz-state contract has one field table                    (#239)
`references/roz-state.md` is the observation contract #133 implements and
#134 consumes; `hooks/state_contract.py` is the same contract as code. Two
copies of a field list drift, so this case holds them equal — by reading
the doc's tables and the module's constants, never by judging prose:
- the doc exists (the pointer in `docs/prose-inventory.md` resolves) and
  names the module's schema string;
- § v0.1 fields: the plain paths and the fact paths equal the module's;
- the statuses, the unknown reasons and the policy deny-list equal the
  module's.
"""

import os
import re
import sys

from lib.lintkit import R, c, read

META = {
    "id": "L15",
    "title": "the roz-state contract has one field table",
    "tier": "lint (#239)",
    "ledger": "`references/roz-state.md` exists and names the schema string of "
              "`hooks/state_contract.py`; its plain paths, fact paths, statuses, unknown reasons "
              "and policy deny-list equal the module's — a field added to one and not the other "
              "fails.",
}

DOC = "references/roz-state.md"


def section(text, heading):
    m = re.search(r"^#{2,3} %s\s*$(.*?)(?=^#{2,3} |\Z)" % re.escape(heading), text, re.M | re.S)
    return m.group(1) if m else ""


def col1(body):
    """Every back-ticked token in the first column of the section's table."""
    out = set()
    for line in body.split("\n"):
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|[-\s|]+\|$", line):
            continue
        out |= set(re.findall(r"`([^`]+)`", re.split(r"(?<!\\)\|", line)[1]))
    return out


_have = os.path.exists(os.path.join(R, DOC))
c.expect("pattern", "L15: %s exists" % DOC, _have)
_text = read(DOC) if _have else ""
try:
    sys.path.insert(0, os.path.join(R, "hooks"))
    import state_contract as sc
except ImportError:
    sc = None
finally:
    sys.path.pop(0)
c.expect("pattern", "L15: hooks/state_contract.py imports", sc is not None)

if sc is not None:
    # the `schema` row of § Plain values, not any mention (the versioning
    # rule names the next version too)
    c.expect("pattern", "L15: the doc's `schema` row carries the schema string %s" % sc.SCHEMA,
             "| `schema` | `%s` |" % sc.SCHEMA in _text)
    for name, heading, want in (
            ("plain paths", "Plain values", set(sc.PLAIN) | {"config.%s" % k for k in sc.CONFIG}),
            ("fact paths", "Facts", set(sc.FACTS)),
            ("statuses", "The three statuses", set(sc.STATUSES)),
            ("unknown reasons", "Reasons", set(sc.REASONS)),
            ("policy deny-list", "Never a fact", set(sc.POLICY_KEYS))):
        got = col1(section(_text, heading))
        c.expect("pattern", "L15: %s — doc § %s equals the module (doc only: %s; module only: %s)"
                 % (name, heading, ", ".join(sorted(got - want)) or "none",
                    ", ".join(sorted(want - got)) or "none"), bool(got) and got == want)
    c.expect("pattern", "L15: docs/prose-inventory.md still points at %s" % DOC,
             "`%s`" % DOC in read("docs/prose-inventory.md"))
