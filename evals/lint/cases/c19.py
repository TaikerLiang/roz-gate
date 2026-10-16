"""C19 · tip is read-only and answers from the documents          (preventive, #121)
/roz-gate:tip <n> reads one issue's labels, CRs, threads and branches and
answers in the terminal — the human's move, the loop's move, the repair
when the state is illegal or stuck. It writes nothing and takes no lock;
the state machine it reads is workflow.md's, never a rule of its own. The
anchors pin that contract: the argument, the read ops (each named in both
adapters), the three answer sections, every illegal state named, and no
write op anywhere in the file — the only `git push` is the human's delete
remedy, addressed to them (C10's rule for every `--delete` in the prose).
"""

from lib.lintkit import c, must_not_match, read, src

META = {
    "id": 'C19',
    "title": 'tip is read-only and answers from the documents',
    "tier": 'lint (preventive, #121)',
    "ledger":
        '"`tip.md` requires `n`, takes no `processing` lock, reads only ISSUE-VIEW / CR-FIND / '
        'THREADS-LIST / REVIEWS-LIST / CR-COMMENTS-LIST / `git ls-remote` / `git worktree list`'
        ' (each named in both adapters), answers in the three fixed sections, names every '
        'illegal state `workflow.md` lists with its repair, and contains no write op — the only'
        ' `git push` in it is the human\'s delete remedy." (state management is the adopter\'s '
        'pain — #121)',
}

_tip = read("commands/tip.md")
src("C19: tip is read-only", "commands/tip.md",
    "**Read-only.** This command writes nothing: no label, no comment, no commit,")
src("C19: n is required", "commands/tip.md",
    "**The argument.** `n` is required: without it, say so and stop")
src("C19: tip takes no processing lock", "commands/tip.md",
    "This command takes no `processing` lock: the lock belongs to state-mutating")
src("C19: patrol never invokes tip", "commands/tip.md",
    "You type this command; patrol never does.")
src("C19: the git reads are ls-remote and worktree list", "commands/tip.md",
    "the only git calls are `git ls-remote` and `git worktree list`")
src("C19: branch names are bound by Lookup, never spelled", "commands/tip.md",
    "bind `<spec-branch>`,\n`<feat-branch>`, `<qa-branch>`, `<fast-branch>` by **Lookup**")
for _op, _lit in (("ISSUE-VIEW", "ISSUE-VIEW #<n>"),
                  ("CR-FIND", "CR-FIND in its **all-states form**"),
                  ("THREADS-LIST", "THREADS-LIST (inline threads)"),
                  ("REVIEWS-LIST", "REVIEWS-LIST (review summary bodies — GitHub only)"),
                  ("CR-COMMENTS-LIST", "CR-COMMENTS-LIST")):
    src("C19: tip reads %s" % _op, "commands/tip.md", _lit)
for _f in ("references/forge-github.md", "references/forge-gitlab.md"):
    for _op in ("ISSUE-VIEW", "CR-FIND"):
        src("C19: %s names %s" % (_f, _op), _f, "| %s |" % _op)
    for _op in ("THREADS-LIST", "CR-COMMENTS-LIST"):
        src("C19: %s names %s" % (_f, _op), _f, "**%s**" % _op)
src("C19: GitHub names REVIEWS-LIST", "references/forge-github.md", "**REVIEWS-LIST**")
src("C19: GitLab says REVIEWS-LIST has no equivalent — tip says GitHub only",
    "references/forge-gitlab.md", "**REVIEWS-LIST has no GitLab equivalent**")
src("C19: the unheard rule is patrol-scan's", "commands/tip.md",
    "NOT start with `**[` or `✅ [` (the rule `references/patrol-scan.md`")
for _sec in ("Yours:", "The loop's:", "Check:"):
    src("C19: the answer carries the section %s" % _sec, "commands/tip.md", "\n%s\n" % _sec)
src("C19: Check appears only when something is off", "commands/tip.md",
    "`Check:` appears only when step 3 found something")
src("C19: every bullet names its source passage", "commands/tip.md",
    "ending with the source — `workflow.md § …`")
for _nm, _lit in (("fast + ready-for-spec", "**`fast` + `ready-for-spec`**"),
                  ("two track or two status labels",
                   "**Two `track:` labels, or two `status:` labels besides `processing`**"),
                  ("blocked beside another status", "**`blocked` beside any other `status:`**"),
                  ("a gate label on a track-less issue", "**A gate label on a track-less issue**"),
                  ("the processing lock", "**`processing` beside a phase label**: a lock"),
                  ("a branch-cutting gate beside an existing branch",
                   "**A branch-cutting gate worn while that kind's branch exists on the "
                   "remote**"),
                  ("in-user-review with a merged CR",
                   "**`in-user-review` with the CR merged and the issue still open**"),
                  ("a review state with no CR",
                   "**`in-user-review` or `in-spec-review` with the CR missing or closed\n"
                   "  unmerged**"),
                  ("a leftover worktree", "**A leftover worktree**")):
    src("C19: the diagnosis names %s" % _nm, "commands/tip.md", _lit)
src("C19: the re-entry repair is branch-names.md's — seq cuts next, else the human deletes",
    "commands/tip.md", "with a `{seq}` template the next pass cuts\n  the next sequence")
# codex, PR #129: the four ways a reading of the state can mislead
src("C19: the re-entry diagnosis spares spec + ready-for-dev (codex, PR #129)",
    "commands/tip.md", "never `spec` +\n  `ready-for-dev`")
src("C19: the approved spec branch is a normal row, not a re-entry", "commands/tip.md",
    "| `spec` + `ready-for-dev`, the spec CR open — the one you approved |")
src("C19: tip never declares a lock stale from its reads (codex, PR #129)",
    "commands/tip.md", "cannot tell a live lock from a stale one from its reads")
src("C19: tip loads the inbox filter keys (codex, PR #129)", "commands/tip.md",
    "the inbox filter `inbox_label` / `inbox_assignee`")
src("C19: an issue outside the filter is outside patrol's inbox", "commands/tip.md",
    "| no `track:`, **outside the inbox filter**")
src("C19: a pending summary request is the loop's move (codex, PR #129)",
    "commands/tip.md", "the gate holder's latest comment requests `summary`")
must_not_match("C19: no write op in tip.md",
               r"LABEL-ADD|LABEL-REMOVE|ISSUE-COMMENT|ISSUE-EDIT-BODY|ISSUE-CLOSE|CR-COMMENT\b"
               r"|THREAD-REPLY|THREAD-RESOLVE|CR-OPEN|CR-READY|CR-MERGE|--add-label"
               r"|--remove-label|--unlabel|gh issue comment|glab issue note|git commit"
               r"|git worktree add|pr create|mr create", _tip)
_pushes = [ln for ln in _tip.splitlines() if "git push" in ln]
c.expect("pattern", "C19: the only `git push` in tip.md is the human's delete remedy",
         _pushes != [] and all("git push origin --delete <branch>" in ln and "yours" in ln
                               for ln in _pushes))
src("C19: tip's hard rules name every write it never does", "commands/tip.md",
    "Hard rules: never apply or remove a label; never post a comment, a reply or")
src("C19: workflow.md lists tip as human-initiated", "references/workflow.md",
    "except `/roz-gate:to-issues` and `/roz-gate:tip`, which you always initiate")
src("C19: workflow.md's tooling list names tip", "references/workflow.md",
    "`/roz-gate:tip` (what #n needs next — read-only)")
src("C19: README's command table has the row", "README.md", "| `/roz-gate:tip <n>` |")
src("C19: README's Troubleshooting points at tip", "README.md",
    "**Not sure what an issue needs?** `/roz-gate:tip <n>`")
src("C19: the onboarding page points at tip (en)", "docs/onboarding.html",
    "<code>/roz-gate:tip &lt;n&gt;</code> reads the issue and tells you")
src("C19: the onboarding page points at tip (zh)", "docs/onboarding.html",
    "<code>/roz-gate:tip &lt;n&gt;</code> 會讀這張 issue 告訴你")
src("C19: the guide's wizard points at tip (en)", "docs/index.html",
    "<code>/roz-gate:tip &lt;n&gt;</code> gives the same answer from the issue's live state")
src("C19: the guide's wizard points at tip (zh)", "docs/index.html",
    "<code>/roz-gate:tip &lt;n&gt;</code> 會從 issue 的即時狀態給出同一個答案")
