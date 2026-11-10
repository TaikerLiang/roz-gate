"""L14 · a kernel rule has one definition                              (#263)
`docs/prose-inventory.md` § Kernel lists the semantic invariants that several
executable files share and the one file that defines each. A rule restated
in several places drifts the moment one copy is reworded, so this case holds
the tables to the shape #263 ruled — mechanically, never by judging whether
prose "means" the same thing:
- each kernel row's owner carries the bold ID label (`**QA-4**`) exactly
  once, and its definition anchor literally;
- every listed consumer carries its anchor, and the anchor carries the
  pointer `QA-4`;
- no file under `agents/`, `commands/`, `references/`, `templates/` carries
  a retired literal of that rule;
- every case in the row is a ledger ID.
"""

import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L14",
    "title": "a kernel rule has one definition",
    "tier": "lint (#263)",
    "ledger": "every `docs/prose-inventory.md` § Kernel row's owner carries its bold ID label "
              "exactly once and its definition anchor; every listed consumer carries its anchor "
              "with the ID pointer; no retired literal of the rule is back in `agents/`, "
              "`commands/`, `references/` or `templates/`; every case is a ledger ID.",
}

PAGE = "docs/prose-inventory.md"
DIRS = ("agents", "commands", "references", "templates")


def flat(s):
    return " ".join(s.split())


def section(text, heading, level):
    m = re.search(r"^%s %s\s*$(.*?)(?=^#{2,%d} |\Z)" % ("#" * level, re.escape(heading), level),
                  text, re.M | re.S)
    return m.group(1) if m else None


def table(body):
    out = []
    for line in (body or "").split("\n"):
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|[-\s|]+\|$", line):
            continue
        out.append([x.strip() for x in re.split(r"(?<!\\)\|", line)[1:-1]])
    return out[1:]


def tree():
    for d in DIRS:
        for root, _dirs, files in os.walk(os.path.join(R, d)):
            for f in files:
                if f.endswith(".md"):
                    p = os.path.join(root, f)
                    yield os.path.relpath(p, R), open(p, encoding="utf-8").read()


_text = read(PAGE) if os.path.exists(os.path.join(R, PAGE)) else ""
_kernel = section(_text, "Kernel", 2)
# the entry table only, not the subsections under it
_rows = table(re.split(r"^### ", _kernel or "", flags=re.M)[0])
c.expect("pattern", "L14: %s § Kernel has at least one row" % PAGE, bool(_rows))
_ledger = set(re.findall(r"^\| ([A-Z]\d+) \|", read("evals/LEDGER.md"), re.M))
_files = dict(tree())

for r in _rows:
    if len(r) != 4:
        c.expect("pattern", "L14: kernel row %r has 4 cells" % r[:1], False)
        continue
    kid, owner, anchor, cases = r
    tag = "L14: %s" % kid
    body = _files.get(owner) or (read(owner) if os.path.exists(os.path.join(R, owner)) else "")
    c.expect("pattern", "%s — the owner %s carries `**%s**` exactly once" % (tag, owner, kid),
             body.count("**%s**" % kid) == 1)
    c.expect("pattern", "%s — the owner carries its definition anchor" % tag,
             bool(anchor) and flat(anchor) in flat(body))
    for f, txt in _files.items():
        if f != owner:
            c.expect("pattern", "%s — no second definition label in %s" % (tag, f),
                     "**%s**" % kid not in txt)
    cons = table(section(_kernel, "%s consumers" % kid, 3))
    c.expect("pattern", "%s — § %s consumers lists at least two" % (tag, kid), len(cons) >= 2)
    for cf, ca in cons:
        ctxt = _files.get(cf) or (read(cf) if os.path.exists(os.path.join(R, cf)) else "")
        c.expect("pattern", "%s — consumer %s carries its anchor %r" % (tag, cf, ca[:40]),
                 bool(ca) and flat(ca) in flat(ctxt))
        c.expect("pattern", "%s — consumer %s's anchor carries the pointer" % (tag, cf),
                 kid in ca)
    for (lit,) in table(section(_kernel, "%s retired wording" % kid, 3)):
        hits = [f for f, txt in _files.items() if flat(lit) in flat(txt)]
        c.expect("pattern", "%s — retired %r is absent (found in: %s)"
                 % (tag, lit[:40], ", ".join(hits) or "none"), not hits)
    named = {x.strip() for x in cases.split(",")}
    c.expect("pattern", "%s — every case is a ledger ID (unknown: %s)"
             % (tag, ", ".join(sorted(named - _ledger)) or "none"), named <= _ledger)
