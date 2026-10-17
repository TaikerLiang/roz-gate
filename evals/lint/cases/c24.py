"""C24 · A bot-applied gate label is an illegal state: reported, never acted on  (#144, 2.1.0)
Rule B stops the reference client from applying a gate label; a foreign
agent the hook cannot reach still can. Detection is the scanner's: the
forge's label events (ISSUE-LABEL-EVENTS, one op under one name in both
adapters) say who applied the gate label worn, and a bot actor — a
configured `bot_login`, a GitHub `[bot]`, a GitLab project/group bot —
makes the row an illegal state: reported, queued, never dispatched, never
repaired. A human actor, holder or not, is the authorization. Replay F13
measures the pass; this case holds every surface that states the rule.
"""

from lib.lintkit import src

META = {
    "id": 'C24',
    "title": 'A bot-applied gate label is an illegal state the scan reports and never acts on',
    "tier": 'lint (#144, 2.1.0)',
    "ledger":
        '"ISSUE-LABEL-EVENTS exists under one name in both adapters (the timeline on GitHub, '
        '`resource_label_events` on GitLab); the scanner audits every gate label worn by its '
        'latest `labeled` event, normalizes the actor, and names the bot test — the handed '
        '`bot_login` list or the forge\'s bot shape — the verdict literal `illegal state: gate '
        'label applied by <login>`, never repair, never route; patrol carries the clause and '
        'the queue verb; workflow, protocol §4, README and both pages say it." (the layer the '
        'hook cannot be: rule B binds this agent, and a foreign agent\'s label looked exactly '
        'like the human\'s until the actor was read)',
}

src("C24: the GitHub adapter has the op", "references/forge-github.md",
    "| ISSUE-LABEL-EVENTS | `gh api --paginate \"repos/<owner>/<repo>/issues/<n>/timeline\"")
src("C24: the GitHub op reads the actor's type", "references/forge-github.md",
    "type: .actor.type")
src("C24: the GitHub identity note names the timeline actor shape", "references/forge-github.md",
    "The issue timeline's `actor` for an App is `<slug>[bot]`\n    with `type` `Bot`")
src("C24: the GitLab adapter has the op", "references/forge-gitlab.md",
    "| ISSUE-LABEL-EVENTS | `glab api --paginate \"projects/:id/issues/<n>/resource_label_events")
src("C24: the GitLab op names both bot shapes", "references/forge-gitlab.md",
    "`project_<id>_bot_<hash>`, a group token's `group_<id>_bot_<hash>`")
src("C24: the scanner audits every gate label worn", "references/patrol-scan.md",
    "- **Gate-label audit.** For every issue wearing a gate label")
src("C24: the scanner reads the latest labeled event", "references/patrol-scan.md",
    "take the **latest\n  `labeled`** (GitLab: `add`) event for that label")
src("C24: the scanner normalizes the actor", "references/patrol-scan.md",
    "Normalize the actor (`app/` prefix and `[bot]` suffix stripped)")
src("C24: the bot test names the handed bot_login list", "references/patrol-scan.md",
    "actor is a **bot** when it is in the `bot_login` list the main agent\n  handed you")
src("C24: the bot test names both forge shapes", "references/patrol-scan.md",
    "(GitHub: `type` `Bot`, or a `[bot]` suffix; GitLab: a `project_<id>_bot_`\n"
    "  / `group_<id>_bot_` prefix)")
src("C24: the verdict literal", "references/patrol-scan.md",
    "`illegal state: gate label applied by <login>`, skip classification")
src("C24: never repaired, never routed", "references/patrol-scan.md",
    "never repair the label, never route the row to `next-stage`\n  or to finalize")
src("C24: a human actor is the authorization", "references/patrol-scan.md",
    "A **human** actor — the gate holder or any other\n  collaborator — is the authorization")
src("C24: the inbox row never finalizes a flagged label", "references/patrol-scan.md",
    "(finalize — never one the audit flagged: that row is illegal)")
src("C24: the evidence column carries the event", "references/patrol-scan.md",
    "the gate label's latest `labeled` event (label · actor · time) on every gated row")
src("C24: patrol's clause", "commands/patrol.md",
    "The scanner's gate-label audit reads\n  `illegal: gate label applied by <login>`.")
src("C24: patrol's queue verb", "commands/patrol.md",
    "remove\nthe gate label `<login>` applied — then reapply it yourself to authorize:\n"
    "re-adding a label already worn records no new event")
src("C24: patrol names the audit among the rows it cannot act on", "commands/patrol.md",
    "a gate label the scanner's\naudit found applied by a bot identity "
    "(`references/patrol-scan.md`)")
src("C24: workflow states detection", "references/workflow.md",
    "a foreign agent it cannot\nreach is held by **detection**: patrol's scanner reads the forge's "
    "label\nevents (ISSUE-LABEL-EVENTS)")
src("C24: workflow — never acted on, never repaired", "references/workflow.md",
    "reported in the pass and the\nqueue, never acted on, never repaired")
src("C24: the invocation policy", "references/workflow.md",
    "never applies a gate label — and never acts on one a bot identity\napplied")
src("C24: protocol §4 — not an authorization", "docs/protocol.md",
    "A gate label applied by a **bot identity is not an authorization**")
src("C24: README's patrol paragraph", "README.md",
    "reports one a bot identity applied\n(the scanner audits the forge's label events) as an "
    "illegal state it never\nacts on")
src("C24: the index's label card", "docs/index.html",
    "One applied by a bot identity is reported by patrol as an illegal state and never acted on.")
src("C24: onboarding's patrol paragraph", "docs/onboarding.html",
    "It never applies a gate label, and reports one a bot applied as an illegal state.")
src("C24: the forge stub serves the route (a fixture never goes UNKNOWN on it)",
    "evals/replay/forge-stub/gh", 'journal("label-events", issue=n, explicit="timeline" in iss)')
