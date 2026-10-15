"""C7 · a branch is cut only from a base the remote has         (defect: 1.18.0-)
Issue #38: the base is config default_branch at every site, and a
base the remote lacks stops the cut instead of cutting from nothing.
"""

import re

from lib.lintkit import c, read, section, src

META = {
    "id": 'C7',
}

_ns = read("commands/next-stage.md")
_a2 = section(_ns, r"^### A2\. Branch", r"^### A3\. ")
_c2 = section(_ns, r"^### C2\. Branch", r"^### C3\. ")
for _nm, _blk in (("A2", _a2), ("C2", _c2)):
    c.expect("pattern", "C7: %s cuts from `<default_branch>`" % _nm,
             "from `<default_branch>`" in _blk)
    c.expect("pattern", "C7: %s prunes stale tracking refs before the check" % _nm,
             "git fetch --prune" in _blk)
    c.expect("pattern", "C7: %s verifies the base exists on the remote before cutting" % _nm,
             "git rev-parse --verify -q origin/<default_branch>" in _blk)
    c.expect("pattern", "C7: %s stops when the base is missing" % _nm,
             "**STOP**" in _blk)
src("C7: A5 targets `<default_branch>`", "commands/next-stage.md",
    "CR-OPEN from `<spec-branch>` targeting `<default_branch>`")
src("C7: C5 targets `<default_branch>`", "commands/next-stage.md",
    "CR-OPEN from `<fast-branch>` targeting `<default_branch>`")
# #90: both read the remote's tip — these anchors pinned the local ref until then.
src("C7: C6 diffs against `origin/<default_branch>`", "commands/next-stage.md",
    "git diff origin/<default_branch>...<fast-branch>")
src("C7: integrate merges `origin/<default_branch>` in", "commands/integrate.md",
    "git merge --no-edit origin/<default_branch>")
for _f in ("commands/next-stage.md", "commands/integrate.md"):
    c.expect("pattern", "C7: %s names no literal trunk as a base" % _f,
             re.search(r"from `(main|master)`|--base (main|master)\b|targeting `(main|master)`",
                       read(_f)) is None)
