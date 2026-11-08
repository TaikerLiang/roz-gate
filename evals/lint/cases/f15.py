"""F15 · A gated row with an open blocker waits  (#205)
ConsoleAPI #28 waited on #27's C10 and still read `actionable: next-stage`
at `ready-for-dev`: the scanner classified each issue on its own labels.
Rulings: the forge's own relationship only (GitHub `blocked by`, GitLab
`is_blocked_by`), read on gated rows, an open blocker → `waits on #n`
(never `blocked`), a closed one releases, a failed read is `blockers
unknown` and needs you, the loop never writes one. Replay F15 measures a
pass; this case holds the statements on every surface.
"""

from lib.lintkit import src

META = {
    "id": 'F15',
}

src("F15: GitHub has the op", "references/forge-github.md",
    '| ISSUE-BLOCKERS | `gh api --paginate '
    '"repos/<owner>/<repo>/issues/<n>/dependencies/blocked_by"')
src("F15: GitLab has the op (both forges, one name)", "references/forge-gitlab.md",
    "| ISSUE-BLOCKERS | `glab api \"projects/:id/issues/<n>/links\" --jq '.[] \\| "
    "select(.link_type == \"is_blocked_by\")")
src("F15: GitHub — a failed read is never no blockers", "references/forge-github.md",
    'is a **failed read**, never "no blockers"')
src("F15: GitLab — a failed read is never no blockers", "references/forge-gitlab.md",
    'A non-zero exit is a **failed read**, never "no blockers"')
src("F15: GitLab Free's relates_to is no blockers, not a failure", "references/forge-gitlab.md",
    "On GitLab Free every link is `relates_to`, so the read succeeds with no blockers")
src("F15: the scanner reads blockers on gated rows", "references/patrol-scan.md",
    "- **Blockers on a gated row** (#205). For every loop issue at `status:\n"
    "  ready-for-spec` / `ready-for-dev`")
src("F15: the forge's relationship only, never body prose", "references/patrol-scan.md",
    "the forge's own relationship, never a `Blocked by`\n  line in a body or a spec")
src("F15: an open blocker → waiting on, open ones only", "references/patrol-scan.md",
    "Any blocker still **open** → verdict\n  `waiting on: #<n>` "
    "(several: `waiting on: #<n>, #<m>`, open ones only)")
src("F15: a closed blocker releases", "references/patrol-scan.md",
    "A **closed** blocker releases\n  it")
src("F15: a failed read → blockers unknown", "references/patrol-scan.md",
    "The read **fails** (a non-zero exit) → verdict\n"
    "  `waiting on: blockers unknown (<the error>)`")
src("F15: the scanner never writes a relationship", "references/patrol-scan.md",
    "You never write a relationship.")
src("F15: the verdict list carries both", "references/patrol-scan.md",
    "`waiting on: #<n>[, #<m>]` · `waiting on: blockers unknown (<error>)`")
src("F15: the report clause, needs you —, never blocked:", "commands/patrol.md",
    "is `waits on #<n>` — the open blockers only, `needs you: —`")
src("F15: the report — blockers unknown needs you", "commands/patrol.md",
    "is `waits on: blockers\n  unknown` with `needs you: yes`")
src("F15: the queue verb", "commands/patrol.md", "fix the dependency lookup — `<error>`")
src("F15: the queue item links the issue itself (baseline: 3 of 5 wrote none)",
    "commands/patrol.md", "Its queue item links **the\n  issue itself**")
src("F15: the queue verb names its link", "commands/patrol.md",
    "are unknown; its link is the issue's)")
src("F15: a waiting row is never queued: (baseline run 4)", "commands/patrol.md",
    "the clause is `waits on #<n>` alone, never `queued: waits\n  on …`")
src("F15: tip's row", "commands/tip.md",
    "| waits on #<n> until it closes — patrol reads the blockers of every gated row")
src("F15: the workflow states the wait", "references/workflow.md",
    "A gate label authorizes; it does not make the issue ready.")
src("F15: README says patrol only reads them", "README.md",
    "Patrol only\nreads those relationships — it never writes one.")
