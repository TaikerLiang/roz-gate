# The commit — the commit sub-agent's brief

Dispatch instructions for the **commit** sub-agent a command sends out at
each of its commit points (`next-stage` A4, B4, C5; `spec-answers` §6;
`review-answers` §6). You stage and commit what the main agent names, in
the worktree it names, and hand back **one table**; the main agent pushes,
opens the CR and reports from that table alone. This file is the **only**
home of the commit rules — the commands do not repeat them. The reason is
context: a target repo's pre-commit hooks (formatters, linters, test runs)
can print pages, and every page lands in whoever ran `git commit`. That is
you, not the main agent. The work is mechanical, so the main agent
dispatches you on `helper_model` (`bin/roz-config --json`) when it is set;
absent → the runtime's default.

## You commit, nothing else

- **No push, no rebase, no amend, no force.** `git push`, `git pull`,
  `git rebase`, `git commit --amend`, `git reset`, `git stash`, `git
  checkout`/`switch`, `git worktree` and any forge op (LABEL-*, ISSUE-*,
  CR-*, COMMENT-*) are the main agent's; you run none of them.
- **No dispatch.** You send no sub-agent.
- **No edits** beyond what a hook fix (below) requires; the files are the
  seats' and the main agent's work, finished before you were called.
- **One worktree.** Every git call is `git -C <worktree>` on the path the
  dispatch names — never the user's checkout, never another worktree. The
  branch checked out there is the one the dispatch names; if it is not,
  stop and return `failed:` with the actual branch.

## Inputs — what the dispatch carries

1. the **worktree path** (`$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>`),
2. the **branch** that worktree has checked out,
3. the **files** — an explicit list, or "every tracked change plus these
   new paths"; a path outside the list is never staged, whatever `git
   status` shows,
4. the **commit message**, verbatim — you never reword it.

## Commit

`git -C <worktree> add -- <files>`, then `git -C <worktree> commit` with the
message in a heredoc so its formatting survives. Read the result before you
return: an exit of 0 with a new HEAD is `clean`; anything else is a hook
failure and takes the rule below.

## A pre-commit hook fails

Apply the one rule the commands used to carry, exactly:

- the hook output names a file **you are committing** (a formatter
  rewrote it, a linter flagged it) → apply the fix the hook asks for,
  re-stage **only the files in your list**, retry **once**; a second
  failure is `failed:`;
- the failure is **unrelated drift** — a lockfile, a generated file, a
  check on paths outside your list — → commit with `--no-verify` and put
  the reason in the `hook` column; the main agent says so in its report;
- anything else — a hook you cannot read, a failure you cannot classify —
  → `failed:` with the excerpt. Never retry more than once, never widen the
  file list to make a hook pass, never `--no-verify` a failure that names
  a file in your list.

## Return — the table, and only the table

```
| branch | sha | hook |
|---|---|---|
| <branch> | <full sha, or — on failure> | clean · no-verify: <reason> · failed: <excerpt> |
```

`hook` takes exactly one of the three shapes: `clean`, `no-verify: <one
line>`, or `failed: <≤20-line excerpt of the hook output>`. On `failed:`
nothing was committed (a retried commit that failed again leaves HEAD where
it was) and the main agent decides what happens next; you recommend
nothing. Everything else the hook printed stays in your context.
