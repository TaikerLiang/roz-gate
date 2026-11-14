"""L20 · next-stage loads one path                                     (#279)
`commands/next-stage.md` held all four paths, so every call loaded four to
walk one. The paths now live in `references/next-stage-path-{a,b,b2,c}.md`
and the command keeps config, selection, invariants, the map, the route and
the STOP exit. This case holds the hand-off, mechanically:
- the route table names, per row, the one path file of that row's path, and
  the file exists;
- every step id A1–A8, B1–B6, B2.1–B2.8, C1–C7 is a heading in exactly one
  file — its path's — so no step is missing, doubled, or left behind in the
  command;
- the transfer instruction is present.
Whether a run Reads exactly that file is behaviour: the replay runner
reports it (`path_files_read`), never scores it.
"""

import os
import re

from lib.lintkit import R, c, read, src

META = {
    "id": "L20",
    "title": "next-stage loads one path",
    "tier": "lint (#279)",
    "ledger": "the `commands/next-stage.md` route table names, per row, the existing "
              "`references/next-stage-path-<x>.md` of that row's path; every step id A1–A8, "
              "B1–B6, B2.1–B2.8, C1–C7 is a heading in exactly one file, its path's; the "
              "transfer instruction is present (#279: every call loaded four paths to walk one).",
}

CMD = "commands/next-stage.md"
PATHS = {k: "references/next-stage-path-%s.md" % k for k in ("a", "b", "b2", "c")}
STEPS = {
    "a": ["A1", "A2", "A3", "A4", "A5", "A6", "A6b", "A6c", "A7", "A8"],
    "b": ["B%d" % i for i in range(1, 7)],
    "b2": ["B2.%d" % i for i in range(1, 9)],
    "c": ["C%d" % i for i in range(1, 8)],
}
HEADING = re.compile(r"^### ([ABC]\d+(?:\.\d+)?[a-z]?)[. ]", re.M)
TRANSFER = ("**Read the routed path's file now** — `${CLAUDE_PLUGIN_ROOT}/` + its File\n"
            "cell, that file and no other path's — before the lock")


def text(rel):
    return read(rel) if os.path.exists(os.path.join(R, rel)) else ""


def route_rows(cmd):
    """{path letter(s): file cell} from the § 4 route table."""
    m = re.search(r"^## 4\. Route\s*$(.*?)(?=^## |^---$|\Z)", cmd, re.M | re.S)
    out = {}
    for line in (m.group(1) if m else "").split("\n"):
        cells = [x.strip() for x in line.strip().split("|")[1:-1]]
        if len(cells) < 3:
            continue
        p = re.match(r"\*\*(A|B2|B|C) — ", cells[1])
        if p:
            out.setdefault(p.group(1).lower(), []).append(cells[-1])
    return out


_cmd = text(CMD)
_rows = route_rows(_cmd)
for _k, _rel in PATHS.items():
    c.expect("pattern", "L20: the route row of Path %s names `%s` alone" % (_k.upper(), _rel),
             _rows.get(_k) == ["`%s`" % _rel])
    c.expect("pattern", "L20: %s exists" % _rel, os.path.exists(os.path.join(R, _rel)))

_found = {}
for _rel in [CMD] + list(PATHS.values()):
    for _sid in HEADING.findall(text(_rel)):
        _found.setdefault(_sid, []).append(_rel)
for _k, _ids in STEPS.items():
    for _sid in _ids:
        c.expect("pattern", "L20: step %s is a heading in exactly one file, %s (found in: %s)"
                 % (_sid, PATHS[_k], ", ".join(_found.get(_sid, [])) or "none"),
                 _found.get(_sid) == [PATHS[_k]])

src("L20: the command hands off to the routed path's file", CMD, TRANSFER)
