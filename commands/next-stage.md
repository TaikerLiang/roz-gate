---
description: Advance one issue to its next stage — spec refinement (2), implementation + review (3+5), validation once the implementation has landed (4+5q), or the fast track — routed by its labels and CR state; prints the workflow map first
argument-hint: "[issue-number]"
---

Advance **one** issue to its next stage (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`). Route by the issue's labels —
and, for the one path that starts from an in-flight issue (B2), by its CRs;
follow the matched path's steps exactly and do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (or CLAUDE.local.md) (`forge`,
`test`, `env_sync`, `lockfile`, `specs_dir`, `acceptance_dir`).
**Local keys** — `default_branch`, `inbox_label`,
`inbox_assignee`, `helper_model`, `branch_user`, `branch_template` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists, empty strings).
`default_branch` is the loop's **base**: `<spec-branch>` and `<fast-branch>` are cut from
it and their CRs target it; `<feat-branch>` and `<qa-branch>` stay siblings off
`<spec-branch>`. **Bind the branch names** — `<spec-branch>`, `<feat-branch>`,
`<qa-branch>`, `<fast-branch>` — per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md`: the local key
`branch_template` (`""` → `{kind}/{n}`), an existing branch found by
**Lookup**, a new one rendered by **Expand**; an invalid template is a STOP
before any cut. Nothing below spells a branch name. Then read `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`
and use its concrete CLI for every CAPITALIZED-OP below. Label names follow the
adapter's scheme (GitLab uses scoped forms). If the config block is missing,
stop and tell the user to run `/roz-gate:init`. **Personas**: every role
dispatch below (`em`, `product`, `implementer`, `qa`, `reviewer`) resolves
through the `### Roz Gate personas` block — dispatch the mapped subagent,
attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults (`roz-gate:<role>`; implementer = the project's
`implementer` agent).

**Workspace.** Every git step below runs in a linked worktree, never in the
user's checkout (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → The main
agent → The workspace): `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> …`
at the branch step, `cd` there (or `git -C`) for everything after, and
`git worktree remove --force` + `git worktree prune` on **both** exits.
`git worktree add` refusing because the branch is checked out elsewhere →
another command holds it → STOP.

## 1. Select the issue
- If an issue number was passed (`$ARGUMENTS`), target that issue. Verify it
  carries a gate label (`status: ready-for-spec` or `status: ready-for-dev`)
  — or is **in flight on `track: spec` with no `status:`**, the entry of
  Path B2 (its CRs decide, §4); anything else → stop and say so.
- Otherwise ISSUE-LIST filtered by each gate label, excluding any issue that
  also carries `status: processing`.
  - None → report "no gated issues" and stop. (Path B2 is reached by
    number only — patrol's `next-stage (qa)` row passes it; this command
    never scans for it.)
  - Several → list them, pick the **oldest**.

## 2. Validate the label invariants (before anything else)
- Exactly **one** `track:` label. Zero or two → stop and report.
- `track: fast` + `status: ready-for-spec` is **illegal** (fast has no spec
  stage) → stop and report.
- Never repair labels yourself — a violation stops here and is reported.

## 3. Print the workflow map
Show the whole workflow with the issue's current position and what this run
will do, THEN act:

`track: spec`:
```
(1) intake → (2) spec → (2a) Q&A → (3) impl → (5) review → (4) QA → (5q) → (6) integrate → (7) main
                ▲ #<n> is here — ready-for-spec: running spec refinement now
```
`track: fast`:
```
(1) intake → (3') implement (main agent) → (5) review → merge to main
                ▲ #<n> is here — ready-for-dev: implementing now
```

## 4. Route
| Labels | Path | File |
|---|---|---|
| `track: spec` + `status: ready-for-spec` | **A — spec refinement (2)** | `references/next-stage-path-a.md` |
| `track: spec` + `status: ready-for-dev` | **B — implementation + review (3)+(5)** — its passed-stage check first | `references/next-stage-path-b.md` |
| `track: spec`, no `status:`, the implementation CR **review-clean or merged**, no QA CR (CR-FIND, all-states form) | **B2 — validation (4)+(5q)** — the one route read from CR state; the scanner computes it (`actionable: next-stage (qa)`), a human may run it | `references/next-stage-path-b2.md` |
| `track: fast` + `status: ready-for-dev` | **C — fast track** | `references/next-stage-path-c.md` |

**Read the routed path's file now** — `${CLAUDE_PLUGIN_ROOT}/` + its File
cell, that file and no other path's — before the lock, then follow it from
its first line to its last; the STOP exit below is its failure exit.

---

Process exactly **one** issue per run.

**Failure = the STOP exit.** If any step after the lock fails — or you hit
anything this command cannot or should not decide — follow the STOP protocol
(`references/workflow.md` → The main agent): `git worktree remove --force` every
worktree this run created (then `git worktree prune`) — never touch the user's
checkout — replace
the issue's status labels with `status: blocked` alone, and post the issue
comment. This command **creates remote artifacts as it goes**, so the comment
must inventory what already exists — branches pushed, CRs opened, partial
deliverables committed — say which step it died on, and recommend how to
continue; that is the must-read, the evidence folds under
`<details><summary>Evidence</summary>`. The must-read opens with
`**[next-stage] · blocked**` and ends with the resume line — **To resume:**
clear `status: blocked`, apply the gate label this run consumed
(`status: ready-for-spec` or `status: ready-for-dev`) — yourself, or tell the
main agent; nothing to answer — run the remedy first, if there is one. Path
B2 consumed no gate label (it entered from in flight): its line reads
**To resume:** clear `status: blocked` — nothing else; patrol's next pass
re-runs it, or run `/roz-gate:next-stage <n>`. A B2.2 STOP names the
conflicting files and says nothing was pushed. **The base lacks a dependency**
(#213): a seat reported that `<default_branch>` lacks code this issue needs
— the must-read names the missing code and the branch that holds it, and
the resume line reads **To resume:** sync `<default_branch>` yourself, then
clear `status: blocked`, apply the gate label this run consumed — yourself,
or tell the main agent; nothing to answer — run the remedy first. Never
merge that branch into the issue branch instead (guard-gate rule K denies
it). The escalation valve (C3) is **not** a failure — it is a designed
transition and never uses the STOP exit.
