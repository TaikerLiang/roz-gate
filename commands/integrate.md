---
description: Drive stage (6) integration — merge the implementation and QA CRs into the spec branch, run the QA black-box tests against the implementation, report the verdict
argument-hint: "[issue-number]"
---

Drive **integration (6)** — the spec-compliance verdict — for one feature.
Preconditions: the implementation CR's review threads are all resolved and the
QA CR is complete. Follow these steps exactly; do nothing beyond them.

**Safety invariant:** the user's checkout is **untouchable** — the user may be
mid-edit on it when a scheduled patrol invokes this — and the **worktree** is
the disposable thing: all merging and every test run happens in a linked
worktree (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → The main agent →
The workspace), and the remote is untouched until a green verdict. The only
remote writes this command ever makes: status labels, the green-verdict push
of `<spec-branch>`, and an issue comment when it stops. A local failure needs no
remote cleanup — remove the worktree and re-run.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (`forge`,
`test`, `acceptance_test`, `env_sync`, `lockfile`, `lockfile_regen`,
`acceptance_dir`, `branch_template`, `fix_rounds`). `fix_rounds` is optional — a non-negative integer, the fix-and-rerun
budget; **absent → 3; any other value → stop here, before the lock**, a
config error like a missing block: name the key and the value, default
nothing. **Local keys** — `default_branch`, `inbox_label`, `inbox_assignee`,
`helper_model`, `branch_user` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists, empty strings). **Branch names**: bind `<spec-branch>`,
`<feat-branch>`, `<qa-branch>`, `<fast-branch>` per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md` (the block's
`branch_template`, absent → `{kind}/{n}`; an existing branch is found by
Lookup, never guessed). Nothing below spells a branch name. Then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. **Personas**: the `implementer` / `qa` fix dispatches in
step 5 resolve through the `### Roz Gate personas` block — dispatch the
mapped subagent, attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults.

## 1. Preconditions (read-only)
- `track: fast` → stop: the fast track has no integration stage — its CR merges
  straight to the default branch after review.
- `status: processing` → stop: another command holds it. (A stale lock from a
  died run: report it, clear it, re-run.)
- `status: blocked` → stop: waiting on the human — see the issue's last
  comment.
- `status: ready-for-spec` / `ready-for-dev` → stop: a gate state,
  `next-stage`'s to pick up. `status: in-spec-review` → stop: a spec thread
  is open, `spec-answers` owns the issue. The legal entries are **no
  `status:`** (patrol's route, or the human cleared `blocked`) and **`status:
  in-user-review`** (the human moved `<spec-branch>` and wants it
  re-verified; the finalize re-applies the label it found).
- From issue `<n>` (`$ARGUMENTS`): the spec branch `<spec-branch>`, the
  implementation CR (head `<feat-branch>`), the QA CR (head `<qa-branch>`) —
  CR-FIND **in its all-states form** (`--state all` / `--all`): a CR the
  forge shows as **merged** is the signal step 3 reads — its content is
  already in `<spec-branch>`. Bind each CR's state, `open` / `draft` /
  `merged`; a closed-unmerged CR counts as absent, and a CR that is absent
  stops the run as it always has.
  Verify the **implementation CR has no open review threads** (THREADS-LIST)
  — a merged CR too: a merged MR can still carry an unresolved thread.
  If any are open, stop and list them — review must be clean before
  integration.
- Verify the **QA CR is not a draft** (CR-VIEW) — draft means QA is still
  working or paused on a question; a verdict run against an incomplete suite is
  a silently weakened verdict. If draft, stop and say so.
- Verify the **QA CR has no open fidelity threads** (THREADS-LIST) — the
  symmetric precondition: a verdict computed from a suite with known-open
  fidelity findings is the same silently weakened verdict. If any are open,
  stop and list them.

## 2. Lock
LABEL-ADD `status: processing`. Every exit — green or STOP — removes this
label.

## 3. Local integration (get the verdict BEFORE finalizing)
- `git fetch`, then
  `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> <spec-branch>`
  and work **in that worktree** for every step below (`cd` there or `git -C`).
  `git worktree add` refusing (the branch is checked out elsewhere) → STOP
  exit. First, in it, `git merge --ff-only origin/<spec-branch>`: the
  worktree starts at the **remote's** tip, never at a stale local ref an
  earlier run left behind — the spec branch moves from elsewhere (a rebase,
  another clone), and a re-verdict merges nothing that would catch the ref
  up. A local ref that cannot fast-forward carries commits the remote lacks
  → STOP exit, naming both SHAs: pushing them is the human's decision.
  Then, **merge what is open, never what is merged**: for each of the
  two CRs, state `open` → `git merge --no-edit origin/<feat-branch>` /
  `git merge --no-edit origin/<qa-branch>` — this brings the contract + code
  + tests together for the first time; state `merged` → nothing to merge,
  its content is already in `<spec-branch>`. **Both merged → nothing is
  merged**: the worktree holds `<spec-branch>`'s tip as it stands, and steps
  4–5 run against it — a **re-verdict**. Once both CRs are merged, integrate
  validates the current `<spec-branch>` tip; it never reconstructs it from
  stale `feat`/`qa` branch tips. The spec branch is the integration source
  of truth from that moment, and it legitimately moves without either
  branch changing — a rebase onto a new base, a sync with concurrently
  merged work, a resolved conflict, a cherry-pick — each wanting a fresh
  verdict on the tip as it stands. Re-merging a merged branch re-introduces
  an input already consumed, and its stale tip conflicts with every later
  move of the spec branch (#77).
- One mechanical carve-out: a conflict **only in `<lockfile>`** — accept both
  sides' manifest entries, regenerate (config `lockfile_regen`), continue, note
  it in the report.
- **Any other conflict, or any environment failure** (config `env_sync`, DB,
  migrations) → the **STOP exit** (step 6).
- Run config `env_sync`.

## 4. Run the verdict
- Run QA's black-box suite against the implementation: config
  `acceptance_test` for the feature (`<acceptance_dir>/<feature>/`). **On a
  re-verdict run the full acceptance suite**, not the feature-scoped one:
  the spec branch moved by means a feature-scoped run cannot see (a sync
  with concurrently merged work), and the hand-back rule wants a captured,
  full run at the SHA that will wear the label.
  **Capture the run's output verbatim** (a local file is fine) — it is the
  evidence source for the final-gate kit's observed values.
- Sanity-check the implementation's unit suites too (config `test`).

## 5. Read the verdict
- **GREEN** → the implementation matches the spec. Finalize — each step checks
  whether it already happened (a re-run after a partial finalize just completes
  the remainder):
  1. Push `<spec-branch>` (this completes the implementation + QA CRs into the spec
     branch), unless already pushed.
  2. Bring the default branch in: on `<spec-branch>`,
     `git merge --no-edit <default_branch>` — resolve conflicts **here** so the
     spec CR's diff stays clean; if the merge changed anything, satisfy the
     **hand-back rule** (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`) before
     pushing: the **full** acceptance suite and config `test`, captured, at the
     SHA that will wear the label. Feature-scoped is not enough here — the
     merge imported exactly the code a feature-scoped run cannot see. Skip if
     already merged in.
  3. Extend the spec CR's gate-kit comment into the **final-gate kit**
     (COMMENT-EDIT, per `${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md`):
     evidence cards from the captured run output + the trace-marker map
     (four buckets — covered / partial / not covered /
     cannot-be-covered-black-box), and the **since-you-approved diff**
     (`git diff <approved-sha>..HEAD -- <specs_dir>/<n>/`, each hunk
     annotated with the thread or amendment that caused it; empty → say
     "the spec you approved is byte-identical"). Stamp `cards-sha` — the
     commit the cards were computed from — so a later (7) change can be seen
     to have outrun them. On a re-verdict the cards are regenerated
     **wholesale** from the new run and `cards-sha` re-stamped (the
     hand-back rule; `${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md`) — never
     patched. Kit comment or approved SHA missing (pre-1.10.0
     flow) → skip, note it in the report.
  4. `git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch>`
     then `git worktree prune` — the pushed branch is the record.
  5. LABEL-ADD `status: in-user-review`; LABEL-REMOVE `status: processing`.
  The feature now waits at **(7)**, where the user reviews the spec CR and the
  main agent hosts the conversation (`/roz-gate:review-answers`). State what
  the run licenses and nothing more: *"green against the pre-rework spec, at
  SHA `<x>`"* — never "verified".
- **RED, every failure cleanly classifiable** → route each fix, never finalize:
  - **real bug** in the implementation → dispatch `implementer` to fix on
    `<feat-branch>`,
  - **harness issue** in the QA tests — a failure where the test **never
    reached its assertion** (import path / async / DB isolation — the known
    cost of blind QA) → dispatch `qa` to fix on `<qa-branch>`,
  - **contract defect** — the test reached its assertion, the assertion
    faithfully states the contract, and reality disagrees (a guaranteed
    behaviour that measurably does not hold) → **STOP exit**: the contract
    is amended through the existing backward transition, then QA re-derives
    the test from the amended contract.
  **An integration RED is never resolved by editing a QA assertion to match
  observed behaviour** — that rewrites the verdict into an echo of the
  implementation. Push the fix, re-run from step 3. Cap: config
  **`fix_rounds`** fix-and-rerun rounds (absent → 3; `0` → every RED is a
  STOP at once, the human routes each fix; §0 already refused anything
  else), counted **per run** — a run cleared from `blocked` starts at
  round 1; still red at the cap → the **cap STOP** (step 6).
  **After a re-verdict RED** the fixed branch's CR is merged, so step 3 would
  skip the fix: route as (7) does (`commands/review-answers.md` §6) — a
  **real bug** is fixed by `implementer` **on `<spec-branch>` in the
  worktree** (the code lives there now); a **harness issue** is fixed by `qa`
  on `<qa-branch>` as always (the acceptance guard allows no other road) and
  you **merge `origin/<qa-branch>` back** into `<spec-branch>` in the worktree
  after the push — its commits since the merged CR are the fix; a conflict
  there is the STOP exit like any other. Then re-run from step 4 in the same
  worktree.
- **Anything else** — a failure that fits neither class, or anything
  surprising → STOP exit.

## 6. The STOP exit — when in doubt, hand it to the human
1. **If this run created it**,
   `git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch>`
   then `git worktree prune` — the half-merged state lives nowhere else, and
   the user's checkout was never touched. A STOP because `worktree add`
   refused removes nothing: that worktree is another run's. There is nothing
   to clean up remotely.
2. LABEL-REMOVE `status: processing` **and the phase label the run entered
   from** (`status: in-user-review` on a re-verdict) — `blocked` is worn
   alone, never beside a phase label; LABEL-ADD `status: blocked`.
3. ISSUE-COMMENT: what happened and your **recommended next step** as the
   must-read; the evidence (conflicting files / test output / error) folded
   under `<details><summary>Evidence</summary>`. When a CR was already
   merged (a post-green shape), the next step reads: clear `blocked` —
   patrol re-verdicts on its next pass, or run `/roz-gate:integrate <n>`.
   **The cap STOP** (`fix_rounds` spent, still red) has a fixed shape. The
   must-read: the cap was reached (*N of N rounds*); the **pattern** line —
   *N rounds · class · file* ("4 harness issues in a row, all in
   `…AcceptanceSupport`"); and the human's **three doors**, one sentence
   each: **clear `blocked`** (patrol re-runs integrate with a fresh budget),
   **raise `fix_rounds`** in the block, or **send it back** (a contract
   defect / a spec round). N rounds of the same class in the same file is
   information, not bad luck — say so. Inside the Evidence block, above
   the last run's output, the **round ledger**: one row per round,
   `round · class · fixed · branch · sha · first failing line` (the fix
   commit the seat returned; the first line of that round's first failure).
Patrol skips `blocked` issues. The human decides, clears the label, and
integration re-runs.

## 7. Report
The verdict (green / red and what was fixed where / stopped and why) with
the **rounds spent** — *green after round 2 of 3*, *stopped at the cap, 3 of
3* — what step 3 merged — *merged `<feat-branch>` and `<qa-branch>`*, *merged
`<qa-branch>` only*, or *re-verdict at SHA `<x>`, nothing merged — both CRs
were already incorporated; `<spec-branch>` moved independently* — any
lockfile regeneration, and what waits on whom. Rule/scenario IDs in the
report follow the citation convention: first mention carries the ID's title
and a link to its definition. A red verdict is a **result**; a
STOP is a **failed verdict attempt** — say which it was. Never silently merge a
red integration.
