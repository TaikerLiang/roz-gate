---
description: Scan spec-CR review threads for the user's answers, fold each into the spec via the role agent that raised it, and resolve the thread
argument-hint: "[issue-number]"
---

Process the user's answers to open-question threads on spec change requests.
Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Gated Loop config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/gated-loop:init`.

## 1. Find spec CRs to check (read-only)
- If an issue number was passed (`$ARGUMENTS`), use the CR whose head branch is
  `spec/<n>` (CR-FIND).
- Otherwise, for every issue with label `status: in-spec-review`, find its spec
  CR (head branch `spec/<n>`, open).
- Skip any issue carrying `status: processing` (another command holds it) or
  `status: blocked` (waiting on the human).
- An `in-spec-review` issue whose spec CR is missing or closed is an impossible
  state → the STOP exit (step 9).

## 2. Read the review threads
THREADS-LIST on each CR.

## 3. Identify ANSWERED threads
A thread needs processing when ALL of:
- it is **unresolved**, AND
- it has **more than one** comment, AND
- the **last** comment does NOT start with `**[` (agent question comments and
  agent replies start with `**[` / `✅`; anything else is a human answer).

If a thread has only the original `**[...]**` question and no reply → leave it,
the user has not answered yet. If no thread qualifies on any CR → report "no
new answers" and stop (no lock was taken).

## 4. Lock, per issue with work
Work issues one at a time. Before touching an issue's threads:
LABEL-ADD `status: processing`. The lock coexists with `in-spec-review` — it is
a mutex, not a phase. The issue's run ends at step 8 (done) or step 9 (STOP);
both remove the lock.

## 5. Process each answered thread
One at a time — fold → reply → resolve, so at most one thread is ever
half-done:
1. Read the role from the question comment's `[role]` tag and the user's
   answer text.
2. **Re-spawn that role agent** (`product` / `em` / `implementer`), giving it:
   the issue body, the current `<specs_dir>/<n>/spec.md` (and
   `technical-spec.md` if relevant), the original question, and the user's
   answer. Instruct it to **fold the decision into the spec doc** — edit the
   file, mark the item resolved with the chosen decision in `## Open
   Questions`, and adjust any affected section. NO implementation code.
3. If the agent needs more information rather than a final decision, it must
   NOT resolve — instead THREAD-REPLY a follow-up (starting
   `**[<role>] · follow-up**`) and leave the thread unresolved.
4. Otherwise, after the spec edit: THREAD-REPLY
   `✅ [<role>] resolved — <decision>, folded into spec.md.` then
   THREAD-RESOLVE.
5. **Story-level check:** if the resolution changes the user story /
   acceptance criteria, ISSUE-COMMENT a summary linking the thread. Do NOT
   edit the issue body/AC — the user decides whether to amend.

## 6. Commit the spec edits
After processing, commit the spec changes on `spec/<n>` and push (so the CR
reflects the resolutions). Use `--no-verify` only for unrelated hook failures,
and say so.

## 7. Promote when fully answered
Re-check the CR's threads. If **every** thread is resolved, the next step
depends on where the issue is:
- **First pass through (2a)** — no `feat/<n>` / `qa/<n>` CRs exist:
  LABEL-REMOVE `status: processing` (leave `status: in-spec-review`) and report
  that #<n> is fully answered and ready for the user's approval to move to
  implementation. Do NOT touch the gate — applying `ready-for-dev` is the
  user's.
- **Mid-flight re-entry** — open `feat/<n>` / `qa/<n>` CRs exist (the thread
  was a contract ambiguity raised during (3)+(4)): LABEL-REMOVE both
  `status: in-spec-review` and `status: processing`, then re-dispatch the
  paused side (normally `qa`) with the amended contract so it resumes. When
  `qa` reports its suite complete, CR-READY its CR — until then it stays
  draft. Report the amendment and what resumed.

If threads remain open: LABEL-REMOVE `status: processing` and list which
questions are still waiting.

## 8. The STOP exit
On anything this command cannot or should not decide — a fold that keeps
failing, a rejected push, an impossible state: follow the STOP protocol.
Discard uncommitted spec edits (`git checkout`), replace the issue's status
labels with `status: blocked` alone, and ISSUE-COMMENT: what happened, the
evidence, and your recommended next step. Name the half-done thread if there is
one — a folded-but-unresolved thread will be re-folded on re-run, and the human
should know. Already-resolved threads are idempotent; a re-run skips them.

## 9. Report
Per issue: which questions you folded, which got follow-ups, any issue comments
posted for story-level changes, what resumed (mid-flight) or what is still
outstanding — and, if you stopped, which exit and why.
