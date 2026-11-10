"""E13 · step zero's questioned → drivable → undrivable → wait chain is four decisions  (#262)
The #199 Haiku reading: the seat obeyed half of one paragraph — it raised the
`[qa]` question — and violated the other half: it wrote no test for a
scenario the contract could drive (D18/D19, D10/D11@C). #243 fixed the
rule's meaning; #262 fixes its density: one executable rule answers one
decision question, so the chain is a numbered list, one decision per item,
in the order the seat must take them. This case pins that structure only —
four items, in order, each with its lead — never the wording; E12 holds the
statements, and replay D18/D19/D10/D11 under `--variant A1` vs `A2`
measure the effect.
"""

import re

from lib.lintkit import c, read

META = {
    "id": "E13",
    "title": "Step zero's questioned → drivable → undrivable → wait chain is four numbered "
             "decisions, in order",
    "tier": "lint (#262)",
    "ledger": "`references/qa-brief.md` § Step zero carries a numbered list of four items, in "
              "order, led by **A finding does not stop you**, **Can the contract as built and "
              "the declared port drive it?**, **Undrivable**, **Only an undrivable scenario "
              "waits** — structure pinned, wording free (#262: each decision fails on its own, "
              "so each is its own item).",
}

LEADS = ("**A finding does not stop you**",
         "**Can the contract as built and the declared port drive it?**",
         "**Undrivable**",
         "**Only an undrivable scenario waits**")

_text = read("references/qa-brief.md")
_m = re.search(r"^## Step zero — the contract review\s*$(.*?)(?=^## |\Z)", _text, re.M | re.S)
_sec = _m.group(1) if _m else ""
c.expect("pattern", "E13: the brief has § Step zero — the contract review", bool(_sec))

# numbered items: "N. " at line start, continuation lines indented; flattened
_items = [" ".join(x.split()) for x in re.findall(r"^(\d+\. .*(?:\n {3}.*)*)", _sec, re.M)]
for k, lead in enumerate(LEADS, 1):
    # by source position, not by the number written on the item (Codex, PR #266)
    c.expect("pattern", "E13: the %s numbered item in the section is %d. %s"
             % ("1st 2nd 3rd 4th".split()[k - 1], k, lead),
             len(_items) >= k and _items[k - 1].startswith("%d. %s" % (k, lead)))
c.expect("pattern", "E13: the chain is exactly four numbered items (found %d)" % len(_items),
         len(_items) == 4)
c.expect("pattern", "E13: each lead appears once in step zero",
         all(" ".join(_sec.split()).count(lead) == 1 for lead in LEADS))
