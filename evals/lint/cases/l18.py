"""L18 · the evaluation charter keeps its shape and its pointers      (#257)
`evals/charter.md` is the one place the eval program's levels, terms and
claim boundaries are defined: Compliance, Judgment, Workflow value; a tier
is how evidence is produced, a level is the product claim it may support.
The other pages apply it by pointing at it — `evals/README.md` links it,
`evals/CONTRIBUTING.md` and the plan-issue skill send a new eval to its six
questions. This case holds the charter's load-bearing parts and those
pointers, and holds out the sentence the charter retired ("the only tier
that measures whether the spec stage earns its cost" — a Level-3 claim made
for a seven-item Level-2 seed). It compares no prose across pages.
"""

import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L18",
    "title": "the evaluation charter keeps its shape and its pointers",
    "tier": "lint (#257)",
    "ledger": "`evals/charter.md` is at most 80 lines and carries the four terms, the three "
              "levels, the sentence that a level is not determined by the runner or directory, "
              "every counted tier under § Current usage, and six numbered rules for new eval "
              "work naming both `product decision` and `stopping rule`; `evals/README.md` links "
              "it; `evals/CONTRIBUTING.md` and the plan-issue skill point at its rules; the "
              "retired overclaim is in neither README (#257: compliance evidence was readable "
              "as proof of engineering value).",
}

CHARTER = "evals/charter.md"
POINTER = "charter.md § Rules for new eval work"
RETIRED = "whether the spec stage earns its cost"
TERMS = ("**Verification**", "**Compliance eval**", "**Judgment eval**",
         "**Workflow-value eval**")
LEVELS = ("## Level 1 — Compliance", "## Level 2 — Judgment", "## Level 3 — Workflow value")
NOT_THE_RUNNER = ("the level is determined by the product question and experimental claim, "
                  "not by the runner or directory")
BOUNDARY = "does not prove Roz Gate improves engineering outcomes"


def flat(s):
    return " ".join(s.split())


def section(text, heading):
    m = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    return m.group(1) if m else ""


_have = os.path.exists(os.path.join(R, CHARTER))
c.expect("pattern", "L18: %s exists" % CHARTER, _have)
_text = read(CHARTER) if _have else ""
_flat = flat(_text)
c.expect("pattern", "L18: the charter is at most 80 lines (%d)" % len(_text.splitlines()),
         _have and len(_text.splitlines()) <= 80)
for _t in TERMS:
    c.expect("pattern", "L18: the charter defines %s" % _t, _t in _text)
for _h in LEVELS:
    c.expect("pattern", "L18: the charter has `%s`" % _h, _h in _text)
c.expect("pattern", "L18: a level is not determined by the runner or directory",
         NOT_THE_RUNNER in _flat)
c.expect("pattern", "L18: a green Level 1 is bounded", BOUNDARY in _flat)
for _d in ("BLOCK", "FLAG_AND_CONTINUE", "NO_FINDING"):
    c.expect("pattern", "L18: Level 2 names the decision `%s`" % _d, "`%s`" % _d in _text)

# every tier the ledger counts is placed — the names come from the counts
# block tools/ledger.py renders, never retyped here
_counts = re.search(r"<!-- counts -->\n(.*?)<!-- /counts -->", read("evals/README.md"), re.S)
_tiers = re.findall(r"^\| \*\*([a-z]+)\*\* \|", _counts.group(1) if _counts else "", re.M)
c.expect("pattern", "L18: the README counts block names tiers", len(_tiers) >= 4)
_usage = section(_text, "Current usage")
for _tier in _tiers:
    c.expect("pattern", "L18: § Current usage places the `%s` tier" % _tier,
             re.search(r"`%s[/`]" % re.escape(_tier), _usage) is not None)

_rules = section(_text, "Rules for new eval work")
_items = re.findall(r"^(\d+)\. ", _rules, re.M)
c.expect("pattern", "L18: six numbered rules for new eval work (%s)" % ",".join(_items),
         _items == ["1", "2", "3", "4", "5", "6"])
for _lit in ("product decision", "stopping rule"):
    c.expect("pattern", "L18: the rules name the %s" % _lit, _lit in flat(_rules))

c.expect("pattern", "L18: evals/README.md links the charter",
         "(charter.md)" in read("evals/README.md"))
for _p in ("evals/CONTRIBUTING.md", ".claude/skills/plan-issue/SKILL.md"):
    c.expect("pattern", "L18: %s points at the rules" % _p, POINTER in flat(read(_p)))
for _p in ("evals/README.md", "evals/judgment/README.md"):
    c.expect("pattern", "L18: %s no longer makes the retired claim" % _p,
             RETIRED not in flat(read(_p)))
