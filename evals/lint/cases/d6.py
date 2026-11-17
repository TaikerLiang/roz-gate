"""D6 · the blind dispatch never opens the implementation CR (defect 1.9.0-, #96)
The brief's step zero sent the implementation-blind reviewer to
"implementation-CR threads" — inline threads anchored at src/…:line whose
comments quote the code. A THREADS-LIST names no src/, so rule E cannot
see it. The dispatcher (the main agent, not blind) now checks contract
currency first and hands the reviewer a code-free amendment list; the
reviewer verifies it and never opens the implementation CR.
A copy of the procedure that names the marker but not the contract-currency
step is what the seat followed (#363: patrol's QA fix dispatch carried no
`Amendment list:`): every list item that invokes it names all its steps or
none.
"""

import os
import re

from lib.lintkit import R, c, must_not_match, read, src

META = {
    "id": 'D6',
}

src("D6: the brief's step zero receives the list", "references/fidelity-brief.md",
    "the dispatch hands you the **amendment\nlist**")
src("D6: the brief aborts without the list", "references/fidelity-brief.md",
    "**No\nlist in the dispatch → abort and say so.**")
src("D6: the brief names implementation-CR threads as never the reviewer's",
    "references/fidelity-brief.md", "Implementation-CR threads are\nnever yours")
must_not_match("D6: the retired step-zero instruction is gone",
               r"spec-CR threads, implementation-CR threads, and issue comments",
               read("references/fidelity-brief.md"))
src("D6: B5b's procedure opens with contract currency by the dispatcher",
    "references/next-stage-path-b2.md", "**Contract currency, by you — not blind.**")
src("D6: B5b refuses to dispatch on a (5) breach", "references/next-stage-path-b2.md",
    "and **do not\n  dispatch**")
src("D6: B5b gives the list its shape (codex review, PR #104)", "references/next-stage-path-b2.md",
    "the heading `Amendment list:`, then one\n  line per amendment")
src("D6: B5b names the empty declaration", "references/next-stage-path-b2.md",
    "`Amendment list: none since <sha>`")
src("D6: B5b says the scanner's read is not the check", "references/next-stage-path-b2.md",
    "the scanner's read of the\n  CRs while classifying is not this check")
src("D6: the brief names the heading", "references/fidelity-brief.md",
    "under the heading `Amendment list:`")
src("D6: the procedure's four steps are named", "references/next-stage-path-b2.md",
    "the contract-currency step, the marker, the dispatch, the\n  marker off")
src("D6: patrol's re-check carries the step", "commands/patrol.md",
    "contract currency by you, marker on,\n   dispatch, marker off")
src("D6: patrol's fidelity-audit carries the step", "commands/patrol.md",
    "contract currency by you first")
src("D6: hooks/README records rule E's cannot-see", "hooks/README.md",
    "cannot see a forge read of the implementation CR")

# #363: each list item invoking the procedure (or B2.4's QA dispatch
# procedure, the same one under the QA brief) that names the marker also
# names the contract-currency step — a partial step list is red.
_PROC = re.compile(r"(fidelity-dispatch|QA dispatch) procedure", re.I)
_ITEM = re.compile(r"^\s*(?:\d+\.|[-*]|#+)\s|^\s*$")


def _items(text):
    cur = []
    for ln in text.splitlines():
        if cur and _ITEM.match(ln):
            yield " ".join(" ".join(cur).split())
            cur = []
        cur.append(ln)
    if cur:
        yield " ".join(" ".join(cur).split())


_hits = 0
for _d in ("commands", "references", "agents"):
    for _base, _, _names in os.walk(os.path.join(R, _d)):
        for _n in sorted(_names):
            if not _n.endswith(".md"):
                continue
            _rel = os.path.relpath(os.path.join(_base, _n), R)
            for _it in _items(read(_rel)):
                if _PROC.search(_it) and re.search(r"\bmarker\b", _it, re.I):
                    _hits += 1
                    c.expect("pattern", "D6 (#363): %s — an item naming the procedure's marker "
                             "names the contract-currency step: %s" % (_rel, _it[:70]),
                             re.search(r"contract[- ]currency", _it, re.I) is not None)
c.expect("pattern", "D6 (#363): the item scan found the procedure's step lists", _hits >= 3)
src("D6 (#363): patrol's QA fix dispatch points to B2.7, no step list", "commands/patrol.md",
    "the fidelity-dispatch procedure** (`references/next-stage-path-b2.md` B2.7,\n"
    "   every step, with `seat=qa`)")
src("D6 (#363): spec-answers' QA re-dispatch points to B2.4, no step list",
    "commands/spec-answers.md",
    "under the QA dispatch procedure (`references/next-stage-path-b2.md` B2.4, every step)")
