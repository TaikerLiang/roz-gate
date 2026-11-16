"""D27 · the dispatch's `Implementation:` line is rendered from the list the hook enforces   (#281)
Rule E knew one layout, `src/`. `implementation_dirs` lets a project list
its own — and then two things read the list: guard-blind, which denies the
read, and the blind dispatch, which must be told what it may not open. If
each had its own copy they could disagree (the config says `lib, app`, a
stale step renders `src`), and for a blindness boundary that is the wrong
kind of bug: the seat obeys the text and the hook blocks something else.

So there is one resolver, `hooks/implementation_dirs.py`. The guard imports
it; `bin/roz-implementation-dirs` imports it and prints the line; the three
dispatch sites append what the tool prints. No command, brief or reference
writes a directory value, and neither the guard nor the tool parses the key
itself. The behaviour is the hook tests'
(`hooks/tests/test_implementation_dirs.py`); this case holds the wiring.
"""

import glob
import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "D27",
    "title": "The dispatch's `Implementation:` line is rendered from the list the hook enforces",
    "tier": "lint (#281)",
    "ledger": "`references/next-stage-path-b2.md` (B2.4, B2.7) and `commands/patrol.md`'s "
              "fidelity step append the line `bin/roz-implementation-dirs` prints; "
              "`qa-brief.md` and `fidelity-brief.md` point at `Implementation:`; "
              "`hooks/guard_blind.py` and the tool both call `implementation_dirs.load` and "
              "neither parses the key; no command or reference spells a directory after "
              "`Implementation:`; the deny message is built from the list in force; "
              "`hooks/README.md` documents the key (#281: rule E knew one layout).",
}


def flat(path):
    return " ".join(read(path).split())


B2 = flat("references/next-stage-path-b2.md")
c.expect("references/next-stage-path-b2.md B2.4",
         "D27: the QA dispatch appends the line the tool prints",
         "`python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-implementation-dirs`" in B2)
c.expect("references/next-stage-path-b2.md B2.4 + B2.7",
         "D27: both blind dispatches name the tool (%d mentions, want >= 2)"
         % B2.count("roz-implementation-dirs"),
         B2.count("roz-implementation-dirs") >= 2)
c.expect("commands/patrol.md (the fidelity step)",
         "D27: patrol's fidelity dispatch carries the tool's line",
         "roz-implementation-dirs" in flat("commands/patrol.md"))
for _brief in ("references/qa-brief.md", "references/fidelity-brief.md"):
    c.expect(_brief, "D27: the brief points at the dispatch's `Implementation:` line",
             "`Implementation:`" in flat(_brief))

GUARD = read("hooks/guard_blind.py")
TOOL = read("bin/roz-implementation-dirs")
for _name, _text in (("hooks/guard_blind.py", GUARD), ("bin/roz-implementation-dirs", TOOL)):
    c.expect(_name, "D27: reads the list through implementation_dirs.load()",
             "import implementation_dirs" in _text and "implementation_dirs.load(" in _text)
    c.expect(_name, "D27: carries no parse of the key of its own",
             not re.search(r"implementation_dirs:(?:\\s|\[)", _text)
             and "find_block" not in _text.replace("from config_block import find_block", "")
             .replace("blk = find_block(top)", ""))
c.expect("hooks/guard_blind.py", "D27: the deny message names the list in force",
         "member.label" in GUARD and "implementation-blind: %s and `feat/<n>`" in GUARD)

_spelled = []
for _path in sorted(glob.glob(os.path.join(R, "commands", "*.md"))
                    + glob.glob(os.path.join(R, "references", "*.md"))
                    + glob.glob(os.path.join(R, "agents", "*.md"))):
    _rel = os.path.relpath(_path, R)
    for _m in re.finditer(r"Implementation: *([^\s`<…]\S*)", read(_rel)):
        _spelled.append("%s: %s" % (_rel, _m.group(0)))
c.expect("commands/, references/, agents/",
         "D27: no prose spells a directory after `Implementation:` (found: %s)"
         % ("; ".join(_spelled) or "none"), not _spelled)
c.expect("hooks/README.md", "D27: the hook README documents `implementation_dirs`",
         "`implementation_dirs`" in read("hooks/README.md"))
