# next-stage — Path C

Routed here by `commands/next-stage.md` §4: `track: fast` + `status: ready-for-dev`.
You have read that file's §0–4 (config, forge adapter, branch names,
workspace, invariants, the map); they hold here. The STOP exit and the
one-issue rule are at the end of `commands/next-stage.md`.

## Path C — fast track

The main agent implements this itself (the one R&R exception). No spec branch,
no QA branch, no integration stage — the guards are unit tests, CI, the
reviewer, and the user's CR review.

### C1. Lock
LABEL-ADD `status: processing`.

### C2. Branch
**The branch may already exist** — a previous attempt at this stage. Before
the cut, **Lookup** the fast kind of #<n> (`git ls-remote --heads origin`
matched against the template — `references/branch-names.md`). A match →
CR-FIND (all-states form) its CR: **open** → illegal state, **STOP** (someone
is still reviewing it; the gate label is wrong, not the branch); **closed
unmerged, or no CR** → this is a **re-spec**, and the route is the
template's. It carries **`{seq}`** → `<fast-branch>` is **1 + max(`{seq}`)**
over Lookup's matches (Expand — never 1 + the count: a gap in the sequences
makes the count an existing ref, #135); **check the expanded name against
the same `ls-remote` output before the cut** — already present → a
collision, **STOP** naming it, never a silent bump. The previous attempts
stay on the remote, readable in their closed CRs — cite them in the report —
and the cut below proceeds. It carries **no
`{seq}`** → the stale branch is the
human's to remove: **STOP**, and the `blocked` comment and the report carry
the remedy verbatim — `git push origin --delete <fast-branch>` — *the human
runs this; the agent never does*: an agent never deletes or force-pushes a
remote branch, and the previous attempt stays readable in its closed CR
(cite it). The resume line reads: run the delete, then re-apply the gate label; the next pass cuts fresh (the cut
uses `-B`, so the previous attempt's local ref cannot block it).

Create `<fast-branch>` from `<default_branch>` **in a worktree** —
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<fast-branch> -B <fast-branch> origin/<default_branch>` (`-B`, not `-b`: after a re-spec the previous attempt's **local** `<fast-branch>` ref may survive its removed worktree, and `-B` resets it onto the base; a local ref is not a remote branch — the invariant is untouched; a `-B` refused because the branch is checked out elsewhere is the mutex, a STOP)
— and work there from here on (`git fetch --prune` first — a stale tracking ref would pass the check for a base the forge deleted; then verify `origin/<default_branch>` exists — `git rev-parse --verify -q origin/<default_branch>` — and if it does not, **STOP**: the base the config names is not on the remote; never cut from anything else).

### C3. Implement — with the escalation valve armed
- Make the minimum change that satisfies the issue's acceptance criteria. A bug
  fix MUST carry a unit test reproducing it.
- **Escalation valve:** the moment this stops being trivial — a real design
  decision, user-facing behaviour beyond the issue's AC, a growing diff — STOP.
  Relabel atomically: LABEL-REMOVE `track: fast`, `status: ready-for-dev`,
  `status: processing`; LABEL-ADD `track: spec`, `status: ready-for-spec`.
  Delete `<fast-branch>` if empty, and report why it escalated. The issue rejoins
  the loop at (2).

### C4. Verify
Run the affected tests plus the existing suite (config `test`). The suite must
stay green before opening the CR.

### C5. Commit + push + open the CR (target = default branch)
Commit through the **commit** sub-agent, on `helper_model` when set —
`${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the `<fast-branch>` worktree
path, branch, files and message; it returns one `branch · sha · hook` row and
the pre-commit output stays out of your context. Push from the returned
`sha` (`no-verify:` → say so; `failed:` → STOP with the excerpt). Then
CR-OPEN from `<fast-branch>` targeting `<default_branch>`, title
`fast: #<n> <title>`, body ending `Closes #<n>`.

### C6. Code review (5)
- Dispatch the **reviewer** agent on `git diff origin/<default_branch>...<fast-branch>`,
  **attaching the seat's R&R row and the issue body** (story + acceptance criteria — the claim the
  diff is reviewed against) — same inline-thread mechanics as B5
  (`${CLAUDE_PLUGIN_ROOT}/references/code-review-mechanics.md` — read it now), **and the
  same record**: one top-level `**[reviewer] · code-review**` comment with
  `reviewed-sha: <head>` and the counts, posted last, even with zero
  findings — patrol's hand-off to `in-user-review` reads it (review-clean =
  record current + zero threads, `workflow.md` (5)). The main
  agent wrote this code, so the reviewer is the independent check; it is NOT
  skippable — except for **doc-only** diffs (a doc-only CR carries the record
  all the same, with `skipped: doc-only` in place of the counts).

### C7. Remove the worktree, flip labels + report
- `git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<fast-branch>`
  then `git worktree prune`.
- LABEL-REMOVE `status: ready-for-dev` and `status: processing`.
- Report the CR and any review threads. **Next:** address review threads; once
  review-clean (the record current, zero threads), LABEL-ADD `status: in-user-review` — then
  the user reviews and merges the CR; merging closes the issue (patrol's
  close-out finishes it where the forge does not).
  `/roz-gate:integrate` does not apply.
