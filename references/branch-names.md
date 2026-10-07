# Branch names

Every branch the loop cuts is named by **one template**, and every command
binds its names **here, once, in its step 0** — `<spec-branch>`,
`<feat-branch>`, `<qa-branch>`, `<fast-branch>` — and uses the bound names
everywhere after. Nothing else in the commands spells a branch name.

The four kinds, and what each is cut from:

| kind | stage | cut from | its CR targets |
|---|---|---|---|
| `spec` | (2) | `<default_branch>` | `<default_branch>` |
| `feat` | (3) | `<spec-branch>` | `<spec-branch>` |
| `qa` | (4) | `<spec-branch>` | `<spec-branch>` |
| `fast` | fast track | `<default_branch>` | `<default_branch>` |

## The template

`branch_template` in the `### Roz Gate config` block — **committed,
team-wide**: everyone's commands and the hooks render the same names.
Absent → `{kind}/{n}`, which is `spec/<n>`, `feat/<n>`, `qa/<n>`, `fast/<n>`
— the names every release before 1.29.0 hardcoded.

| placeholder | renders as |
|---|---|
| `{kind}` | `spec` / `feat` / `qa` / `fast` |
| `{type}` | spec branch → `spec`; qa branch → `test`; feat and fast branches → the issue's `type:` label — `type: feat` / `type: fix` / `type: chore` → `feat` / `fix` / `chore`; no `type:` label → `feat` |
| `{user}` | the local key `branch_user` (`bin/roz-config --json`); empty → WHOAMI (the adapter op: the forge login of the account running the command) in user mode, the first `bot_login` in bot mode |
| `{n}` | the issue number |
| `{seq}` | the attempt counter: 1 + the number of branches **Lookup** (below) finds for this kind and issue |

A template is **valid** when it contains `{n}` and at least one of `{kind}`
/ `{type}` (without one, the spec and qa branches of an issue collide), and
every `{…}` in it is one of the five. Anything else → **STOP** before any
branch is cut; the `blocked` comment quotes the template and names what is
missing or unknown — the block is edited by hand, never by a command.

Example — the convention `{type}/{user}/{n}/{seq}` renders, for issue #5
labelled `type: fix`, `branch_user` = `pwliangc`, first attempt:
`spec/pwliangc/5/1` · `fix/pwliangc/5/1` · `test/pwliangc/5/1` — and the
fast track of a `type: chore` issue #4: `chore/pwliangc/4/1`. A template
without `{kind}` renders feat and fast identically; they never coexist for
one issue (`track: spec` vs `track: fast`), so that is the convention's
choice, not an error.

## Expand — at cut time

Render every placeholder for the kind being cut. `{user}` is **this**
command's user (the local key or WHOAMI); `{seq}` is **1 + the Lookup
count** — the first attempt is `1`, a re-entry after a closed CR is `2`,
and so on. The result is the bound name; the worktree is
`$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>`, the name as-is
(slashes are directories, as they always were).

## Lookup — any later time

A command that did not cut a branch cannot compute its name: another
person's `{user}` and the attempt's `{seq}` are not knowable from the
config. So a branch is **found, never guessed**:
`git ls-remote --heads origin` (a query of the remote — no fetch, no local
ref touched), and match every `refs/heads/…` against the
template rendered with `{user}` → any single path segment (`[^/]+`),
`{seq}` → any number (`[0-9]+`), and the other placeholders expanded
exactly for the kind and issue (the `type:` label is read from the issue
each time). Under the default template this is an exact name.

- **Zero matches** → the branch does not exist.
- **One match** → that is the bound name.
- **Several, different `{seq}`** → the **highest `{seq}`** is the live
  attempt; the others are earlier attempts, kept (an agent never deletes a
  remote branch — `references/workflow.md`).
- **Several at the same `{seq}`** (two people cut the same kind for the
  same issue under a template without `{seq}`, or a `{user}`-only
  template) → an ambiguity the command must not resolve: **STOP**, naming
  both.

CR-FIND and CR-OPEN take the bound name; the adapter ops do not change.
A reader that may not run git — patrol's scanner — is handed the
`ls-remote` output by the main agent and matches the same way.

## Re-entry — the branch already exists

`next-stage` checks before every cut from `<default_branch>` (A2, C2).
Lookup finds a branch for this kind and issue → CR-FIND (all-states form)
its CR:

- **open** → illegal state, **STOP** — someone is still reviewing it; the
  gate label is wrong, not the branch.
- **closed unmerged, or no CR** → a re-entry (a re-spec, or a fast attempt
  abandoned). Then, by the template:
  - it carries **`{seq}`** → Expand renders the **next sequence** and the
    cut proceeds; the previous attempt stays on the remote, readable in its
    closed CR — cite it in the report. Nothing is deleted, nothing
    force-pushed.
  - it carries **no `{seq}`** (the default among them) → there is no slot
    to count in, and the stale branch is the human's to remove: **STOP**;
    the `blocked` comment and the report carry the remedy verbatim —
    `git push origin --delete <branch>` — *the human runs this; the agent
    never does*. Re-apply the gate label after deleting; the next pass cuts
    fresh.

## The hooks

- **guard-acceptance** decides "is HEAD a spec branch" by the template:
  the spec kind rendered with `{user}` / `{seq}` / `{n}` as patterns. No
  `branch_template` line in the block → `spec/*`, as before.
- **guard-blind** reads the forbidden implementation ref from the marker:
  the dispatching command writes `feat=<feat-branch>` into
  `roz-gate/fidelity-dispatch` (next-stage B5b, patrol's address-review);
  while the marker exists, a git action on that ref is denied — and on any
  `feat/` ref regardless, the pre-template rule, kept.

## Changing the template

The template is read on every command run; an issue already cut under the
previous template (or a `type:` label changed mid-loop) is the human's to
move — retarget its CRs, rename or re-cut — exactly as a `default_branch`
handover. Nothing in the loop pins a template per issue, and nothing
detects the change.
