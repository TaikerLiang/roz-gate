"""D6 · the blind dispatch never opens the implementation CR (defect 1.9.0-, #96)
The brief's step zero sent the implementation-blind reviewer to
"implementation-CR threads" — inline threads anchored at src/…:line whose
comments quote the code. A THREADS-LIST names no src/, so rule E cannot
see it. The dispatcher (the main agent, not blind) now checks contract
currency first and hands the reviewer a code-free amendment list; the
reviewer verifies it and never opens the implementation CR.
"""

from lib.lintkit import must_not_match, read, src

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
    "commands/next-stage.md", "**Contract currency, by you — not blind.**")
src("D6: B5b refuses to dispatch on a (5) breach", "commands/next-stage.md",
    "and **do not\n  dispatch**")
src("D6: B5b gives the list its shape (codex review, PR #104)", "commands/next-stage.md",
    "the heading `Amendment list:`, then one\n  line per amendment")
src("D6: B5b names the empty declaration", "commands/next-stage.md",
    "`Amendment list: none since <sha>`")
src("D6: B5b says the scanner's read is not the check", "commands/next-stage.md",
    "the scanner's read of the\n  CRs while classifying is not this check")
src("D6: the brief names the heading", "references/fidelity-brief.md",
    "under the heading `Amendment list:`")
src("D6: the procedure's four steps are named", "commands/next-stage.md",
    "the contract-currency step, the marker, the dispatch, the\n  marker off")
src("D6: patrol's re-check carries the step", "commands/patrol.md",
    "contract currency by you, marker on,\n   dispatch, marker off")
src("D6: patrol's fidelity-audit carries the step", "commands/patrol.md",
    "contract currency by you first")
src("D6: hooks/README records rule E's cannot-see", "hooks/README.md",
    "cannot see a forge read of the implementation CR")
