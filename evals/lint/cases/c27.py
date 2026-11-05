"""C27 · A gate label on a stage that passed is an illegal state: reported, never acted on  (#209)
`ready-for-dev` is consumed at B6 — the open implementation CR becomes the
state. A holder who applies it again (ConsoleAPI #27: the implementation
merged, the QA CR clean, the holder wanting integrate) authorizes nothing:
the label gates a stage that passed. The scanner reads the implementation
CR in its all-states form and reports the row when it merged — open is a
STOP's resume, whose line re-applies the label; next-stage refuses before
its lock, with no STOP exit (its resume line would re-apply the label);
tip names the repair. A closed-unmerged CR or none is a re-implementation.
Replay F14 measures the pass; this case holds every surface that states
the rule.
"""

from lib.lintkit import src

META = {
    "id": 'C27',
    "title": 'A gate label on a passed stage is an illegal state the scan reports, never acts on',
    "tier": 'lint (#209)',
    "ledger":
        '"The scanner CR-FINDs a `track: spec` + `ready-for-dev` issue\'s `<feat-branch>` in the '
        'all-states form and, merged, gives the verdict literal `illegal state: '
        'ready-for-dev on a passed stage`, never repair, never route — open (a STOP\'s '
        'resume), closed unmerged or none is classified normally; patrol carries the clause '
        'and the queue verb; next-stage runs '
        'a read-only passed-stage check before Path B\'s lock, not the STOP exit; tip, workflow '
        'and README say it." (ConsoleAPI #27: the gate-label audit asked only who applied the '
        'label, so the holder\'s second `ready-for-dev` read as authorization over merged work)',
}

src("C27: the scanner names the rule", "references/patrol-scan.md",
    "- **A gate label on a stage that passed.** For a `track: spec` issue")
src("C27: the scanner reads the implementation CR in the all-states form",
    "references/patrol-scan.md",
    "CR-FIND its\n  `<feat-branch>` (bound by Lookup — `references/branch-names.md`) in the\n"
    "  all-states form.")
src("C27: merged into the bound spec branch is the passed stage", "references/patrol-scan.md",
    "CR **merged into the bound `<spec-branch>`** (its base:")
src("C27: an earlier {seq} attempt's merged CR is history (codex review, PR #212)",
    "references/patrol-scan.md",
    "under a `{seq}` template an earlier\n  attempt's merged CR targets the earlier spec branch")
src("C27: next-stage scopes the check to the bound spec branch", "commands/next-stage.md",
    "**Merged into the bound `<spec-branch>`** (its base; an earlier\n`{seq}` attempt's")
src("C27: open is a STOP's resume, classified normally", "references/patrol-scan.md",
    "Open → classify normally: the STOP exit's resume line re-applies the\n  label over an open CR")
src("C27: the verdict literal", "references/patrol-scan.md",
    "verdict `illegal state: ready-for-dev\n  on a passed stage (<feat-branch> merged)`")
src("C27: never repaired, never routed — not to next-stage, not on to the CRs' action",
    "references/patrol-scan.md",
    "never repair the label, never route the row to `next-stage`, nor on\n"
    "  to the action its CRs would get (integrate, qa) while the label is worn.")
src("C27: closed unmerged or none is a re-implementation", "references/patrol-scan.md",
    "no CR → classify normally (a re-implementation, #209).")
src("C27: patrol's clause", "commands/patrol.md",
    "passed reads `illegal: ready-for-dev on a passed stage (<feat-branch> merged)`.")
src("C27: patrol's queue verb", "commands/patrol.md",
    "remove `status: ready-for-dev` from a stage that passed —\nnothing else: patrol resumes "
    "from the CRs")
src("C27: patrol names it among the rows it cannot act on", "commands/patrol.md",
    "or worn\non a stage that passed, a scan that contradicts")
src("C27: the route table points at the check", "commands/next-stage.md",
    "**B — implementation + review (3)+(5)** — its passed-stage check first")
src("C27: next-stage's passed-stage check", "commands/next-stage.md",
    "**Passed-stage check (first, read-only):** Lookup `<feat-branch>`")
src("C27: next-stage — no lock, no writes, not the STOP exit", "commands/next-stage.md",
    "Take no lock and write nothing — **not** the STOP\nexit, whose resume line would have the "
    "holder re-apply the label this\ncheck refuses")
src("C27: next-stage continues over an open CR (a STOP's resume)", "commands/next-stage.md",
    "Open → continue: a STOP's resume line\nre-applies the label over an open CR")
src("C27: next-stage's remedy", "commands/next-stage.md",
    "**remove\n`status: ready-for-dev`, nothing else**")
src("C27: tip classifies it", "commands/tip.md",
    "- **`track: spec` + `ready-for-dev` with the implementation CR merged**\n"
    "  (into the bound spec branch")
src("C27: workflow's state machine", "references/workflow.md",
    "- `spec`+`ready-for-dev` with the implementation CR merged is **illegal**")
src("C27: README's patrol paragraph", "README.md",
    "A `ready-for-dev` applied again on a stage that passed")
