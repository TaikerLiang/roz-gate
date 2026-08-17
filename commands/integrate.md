---
description: Drive stage (6) integration — merge the implementation and QA CRs into the spec branch, run the QA black-box tests against the implementation, report the verdict
argument-hint: "[issue-number]"
---

Drive **integration (6)** — the spec-compliance verdict — for one feature.
Preconditions: the implementation CR's review threads are all resolved and the
QA CR is complete. Follow these steps exactly; do nothing beyond them.

**Safety invariant:** the local checkout is disposable, and the remote is
untouched until a green verdict. The only remote writes this command ever
makes: status labels, the green-verdict push of `spec/<n>`, and an issue
comment when it stops. A local failure needs no remote cleanup — discard and
re-run.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (`forge`,
`default_branch`, `test`, `acceptance_test`, `env_sync`, `lockfile`,
`lockfile_regen`, `acceptance_dir`), then
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
- From issue `<n>` (`$ARGUMENTS`): the spec branch `spec/<n>`, the
  implementation CR (head `feat/<n>`), the QA CR (head `qa/<n>`) — CR-FIND.
  Verify the **implementation CR has no open review threads** (THREADS-LIST).
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
- Checkout `spec/<n>`. `git merge --no-edit feat/<n>` then
  `git merge --no-edit qa/<n>` — this brings the contract + code + tests
  together for the first time.
- One mechanical carve-out: a conflict **only in `<lockfile>`** — accept both
  sides' manifest entries, regenerate (config `lockfile_regen`), continue, note
  it in the report.
- **Any other conflict, or any environment failure** (config `env_sync`, DB,
  migrations) → the **STOP exit** (step 6).
- Run config `env_sync`.

## 4. Run the verdict
- Run QA's black-box suite against the implementation: config
  `acceptance_test` for the feature (`<acceptance_dir>/<feature>/`).
  **Capture the run's output verbatim** (a local file is fine) — it is the
  evidence source for the final-gate kit's observed values.
- Sanity-check the implementation's unit suites too (config `test`).

## 5. Read the verdict
- **GREEN** → the implementation matches the spec. Finalize — each step checks
  whether it already happened (a re-run after a partial finalize just completes
  the remainder):
  1. Push `spec/<n>` (this completes the implementation + QA CRs into the spec
     branch), unless already pushed.
  2. Bring the default branch in: on `spec/<n>`,
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
     to have outrun them. Kit comment or approved SHA missing (pre-1.10.0
     flow) → skip, note it in the report.
  4. LABEL-ADD `status: in-user-review`; LABEL-REMOVE `status: processing`.
  The feature now waits at **(7)**, where the user reviews the spec CR and the
  main agent hosts the conversation (`/roz-gate:review-answers`). State what
  the run licenses and nothing more: *"green against the pre-rework spec, at
  SHA `<x>`"* — never "verified".
- **RED, every failure cleanly classifiable** → route each fix, never finalize:
  - **real bug** in the implementation → dispatch `implementer` to fix on
    `feat/<n>`,
  - **harness issue** in the QA tests — a failure where the test **never
    reached its assertion** (import path / async / DB isolation — the known
    cost of blind QA) → dispatch `qa` to fix on `qa/<n>`,
  - **contract defect** — the test reached its assertion, the assertion
    faithfully states the contract, and reality disagrees (a guaranteed
    behaviour that measurably does not hold) → **STOP exit**: the contract
    is amended through the existing backward transition, then QA re-derives
    the test from the amended contract.
  **An integration RED is never resolved by editing a QA assertion to match
  observed behaviour** — that rewrites the verdict into an echo of the
  implementation. Push the fix, re-run from step 3. Cap: **3** fix-and-rerun
  rounds; still red → STOP exit.
- **Anything else** — a failure that fits neither class, or anything
  surprising → STOP exit.

## 6. The STOP exit — when in doubt, hand it to the human
1. Discard local state (`git merge --abort` / reset). There is nothing to
   clean up remotely.
2. LABEL-REMOVE `status: processing`; LABEL-ADD `status: blocked`.
3. ISSUE-COMMENT: what happened, the evidence (conflicting files / test output
   / error), and your **recommended next step**.
Patrol skips `blocked` issues. The human decides, clears the label, and
integration re-runs.

## 7. Report
The verdict (green / red and what was fixed where / stopped and why), any
lockfile regeneration, and what waits on whom. Rule/scenario IDs in the
report follow the citation convention: first mention carries the ID's title
and a link to its definition. A red verdict is a **result**; a
STOP is a **failed verdict attempt** — say which it was. Never silently merge a
red integration.
