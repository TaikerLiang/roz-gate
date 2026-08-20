---
description: Scan spec-CR review threads for the user's answers, fold each into the spec via the role agent that raised it, and resolve the thread
argument-hint: "[issue-number]"
---

Process the user's answers to open-question threads on spec change requests.
Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. **Personas**: the role re-spawns in step 5 resolve through
the `### Roz Gate personas` block — dispatch the mapped subagent, attaching
the seat's R&R row from `${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its
contract. Block missing → plugin defaults (`roz-gate:<role>`; implementer =
the project's `implementer` agent).

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
- the **last** comment does NOT start with `**[` or `✅ [` (agent question
  comments and agent replies start with `**[` / `✅ [`; anything else is a
  human answer — note the bracket: a human's own `✅ 看起來可以` is an answer,
  and the marker must not swallow it).

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
   answer. Instruct it to **fold the decision into the document the raising
   seat owns** — `spec.md`; **`technical-spec.md` for `[implementer]`
   questions** (the contract QA tests against must learn the answer — a fold
   that lands as prose near the question while the contract text stays
   unchanged ships the defect with a resolved thread pointing at it). A
   `[qa]`-tagged thread folds by document owner too (qa never writes spec
   text); qa gets the thread reply. Then mark the item resolved in
   `spec.md`'s `## Open Questions`, and adjust any affected section. NO
   implementation code. Two rules ride every fold:
   - **The holder is not an oracle about reality.** Empirical content inside
     an answer ("MariaDB defaults to case-insensitive, so pick (b)") folds
     with **both tags, separately**: the ruling carries its authority tag
     `(from Q<j>)` as usual, and the empirical premise carries `(unverified)`
     as its evidence tag — never merged into one parenthesis (the two axes
     never share a tag, per A3's placement rule, and the Path B and promote
     greps match the literal `(unverified)`). The ruling part is the
     holder's; the claim about the world still needs measuring or demoting.
   - **A fold touching an evidence-tagged sentence re-derives the tag**: the
     measurement still covers the edited claim, or the tag downgrades to
     `(unverified)`. A stale `(measured, <date>, <scope>)` certifying a claim
     nobody measured is worse than no tag.
   **Resolved-entry shape** (spec.md stays current truth; the argument lives
   in the ledger and the thread): a resolved `## Open Questions` item keeps
   exactly its title line, the question sentence, and a `**Resolved:**` block
   of — the ruling, holder attribution + date, **one sentence of the
   holder's rationale**, and "folded into <IDs>" pointers. It drops the
   option bullets and any back-and-forth, and it **never restates
   rule/scenario/contract text — it points at IDs** (a second prose copy is
   a copy that can drift). The verbatim answer and the interpretation gap
   already live in the gate kit's decision ledger.
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

## 6b. Update the spec-gate kit
COMMENT-EDIT the spec CR's gate-kit comment
(`${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md`): append one decision-ledger
entry per folded thread — the question, **the user's answer quoted
verbatim**, and **the fold** (the spec text that resulted, quoted with its
link); anything the folding agent wrote beyond the literal answer is marked
*interpretation:*. Refresh the attention list (a re-folded rule sorts under
"changed after your ruling"). Kit comment missing (pre-1.10.0 CR) → skip,
note it in the report.

## 7. Promote when fully answered
Re-check the CR's threads. If **every** thread is resolved, the next step
depends on where the issue is:
- **First pass through (2a)** — no `feat/<n>` / `qa/<n>` CRs exist:
  LABEL-REMOVE `status: processing` (leave `status: in-spec-review`). Before
  reporting ready, two checks:
  - `grep -n '(unverified)' <specs_dir>/<n>/*.md` — any hit is an unresolved
    blocker: the report lists the claims and does **not** say "ready for
    approval" (measure, or demote to `(assumed-empirical: <risk>)`). Zero
    hits in a pre-vocabulary spec (no evidence tags anywhere) is absence of
    the vocabulary, not verification — say which the report means.
  - **Walk currency**: if any fold added or reshaped a scenario since the §5
    observability walk's commit, those walk rows are stale — re-dispatch the
    implementer for exactly those rows before reporting ready (same shape as
    the fidelity brief's step zero).
  Then report that #<n> is fully answered and ready for the user's approval
  to move to implementation. Do NOT touch the gate — applying `ready-for-dev`
  is the user's.
- **Mid-flight re-entry** — open `feat/<n>` / `qa/<n>` CRs exist (the thread
  was a contract ambiguity raised during (3)+(4)): LABEL-REMOVE both
  `status: in-spec-review` and `status: processing`, then re-dispatch the
  paused side (normally `qa`) with the amended contract so it resumes. When
  `qa` reports its suite complete, CR-READY its CR — until then it stays
  draft. Report the amendment and what resumed.
- **Post-integration re-entry** — `feat/<n>` / `qa/<n>` exist but are
  **merged** (the issue came back from (7): the user's review raised something
  that changed what a rule means). The work is built, so this never returns to
  implementation. Fold, then: if the amendment changed behaviour, honour the
  **hand-back rule** — re-run config `acceptance_test` and config `test` on
  `spec/<n>`, capture the output, regenerate the gate kit's evidence cards
  wholesale and re-stamp `cards-sha`. A red here is the stage-(6) taxonomy
  (`commands/integrate.md` step 5), never an assertion edited to match. Then
  LABEL-REMOVE both `status: in-spec-review` and `status: processing`,
  LABEL-ADD `status: in-user-review` — the conversation resumes at (7) where
  it paused. Report the amendment and the re-run's result.

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
