---
description: Scan spec-CR review threads for the user's answers, fold each into the spec via the role agent that raised it, and resolve the thread
argument-hint: "[issue-number]"
---

Process the user's answers to open-question threads on spec change requests.
Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (or CLAUDE.local.md), then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. **Local keys** — `default_branch`, `inbox_label`, `inbox_assignee`,
`helper_model`, `branch_user` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists, empty strings). **Branch names**: bind `<spec-branch>`,
`<feat-branch>`, `<qa-branch>`, `<fast-branch>` per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md` (the block's
`branch_template`, absent → `{kind}/{n}`; an existing branch is found by
Lookup, never guessed). Nothing below spells a branch name. **Personas**: the role re-spawns in step 5 resolve through
the `### Roz Gate personas` block — dispatch the mapped subagent, attaching
the seat's R&R row from `${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its
contract. Block missing → plugin defaults (`roz-gate:<role>`; implementer =
the project's `implementer` agent).

## 1. Find spec CRs to check (read-only)
- If an issue number was passed (`$ARGUMENTS`), use the CR whose head branch is
  `<spec-branch>` (CR-FIND).
- Otherwise, for every issue with label `status: in-spec-review`, find its spec
  CR (head branch `<spec-branch>`, open).
- Skip any issue carrying `status: processing` (another command holds it) or
  `status: blocked` (waiting on the human).
- An `in-spec-review` issue whose spec CR is missing or closed is an impossible
  state → the STOP exit (step 9).

## 2. Read the review threads
THREADS-LIST on each CR.

## 3. Identify ANSWERED threads — and AMENDMENT requests
A thread needs processing when it is **unresolved** and EITHER:
- **an answer**: it has **more than one** comment and the **last** comment does
  NOT start with `**[` or `✅ [` (agent question comments and agent replies
  start with `**[` / `✅ [`; anything else is a human answer — note the
  bracket: a human's own `✅ 看起來可以` is an answer, and the marker must not
  swallow it); OR
- **an amendment request**: its **first** comment does NOT start with `**[`
  or `✅ [` — the human opened the thread themselves ("the spec misses X";
  the issue was right, the spec must cover more) — and its last comment is
  not an agent marker either. One comment is enough. No `[role]` tag exists:
  the role is the **document the thread sits on** (THREADS-LIST returns each
  thread's `path` and `line`; a thread with no path — a CR-level comment — is
  `product`'s) — `technical-spec.md` →
  `implementer`; `spec.md` → `product`, or `em` when the thread is on a
  section em owns (Problem Statement, Success Metrics, Architecture Notes,
  Out of Scope); any other file → `product`.

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
   answer text — for an amendment request, the role from the document (step
   3) and the human's comment as the ruling; there is no question to answer,
   only a gap to cover.
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
     never share a tag, per A3's placement rule; the Path B and promote
     greps are widened to catch a merged parenthesis anyway — convention
     first line of defense, grep the second). The ruling part is the
     holder's; the claim about the world still needs measuring or demoting.
   - **A fold touching an evidence-tagged sentence re-derives the tag**: the
     measurement still covers the edited claim, or the tag downgrades to
     `(unverified)`. A stale `(measured, <date>, <scope>)` certifying a claim
     nobody measured is worse than no tag.
   **An amendment** has no `## Open Questions` item yet: add one, resolved
   on arrival — `**[<role>] · A<k> · <2–4-word title>**` with a
   `**Resolved:**` block (the human's ruling, attribution + date, "folded
   into <IDs>") — so the collection point stays complete and a rule born
   from an amendment carries `(from A<k>)` as its provenance, never
   `(assumed)`.
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
   `✅ [<role>] resolved — <decision>, folded into spec.md.` (an amendment:
   `✅ [<role>] amended — <what changed>, folded into <document>.`) then
   THREAD-RESOLVE.
5. **Story-level check:** if the resolution changes the user story /
   acceptance criteria, ISSUE-COMMENT a summary linking the thread. Do NOT
   edit the issue body/AC — the user decides whether to amend.

## 6. Commit the spec edits
Every fold above edits the spec **in a worktree of `<spec-branch>`** —
`git fetch`, then
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> <spec-branch>`
before the first fold (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → The
main agent → The workspace); a refusal means another command holds the
branch → the STOP exit. After processing, commit the spec changes there
through the **commit** sub-agent — one dispatch, on `helper_model` when set,
`${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the worktree path,
`<spec-branch>`, the spec files and the message; it returns one `branch · sha ·
hook` row and the hook output stays out of your context — then push from
the returned `sha` (so the CR reflects the resolutions; `no-verify:` → say
so; `failed:` → STOP with the excerpt). **Keep the worktree** through
step 7 — the post-integration re-entry runs the hand-back suites in it —
and remove it at step 7's end.

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
depends on where the issue is — decided by CR-FIND for `<feat-branch>` /
`<qa-branch>` **in its all-states form** (the adapter's merged-CR variant,
`--state all` / `--all`): the open-only default reads *merged* as
*absent* and would send a shipped issue back through implementation.
- **First pass through (2a)** — no `<feat-branch>` / `<qa-branch>` CRs exist:
  LABEL-REMOVE `status: processing` (leave `status: in-spec-review`). Before
  reporting ready, two checks:
  - `grep -nE '(^|[(,])[[:space:]]*unverified' <specs_dir>/<n>/*.md` (the
    widened form — it also catches a tag illegally merged into another
    parenthesis or split by a wrap) — any hit is an unresolved
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
- **Mid-flight re-entry** — open `<feat-branch>` / `<qa-branch>` CRs exist (the thread
  was a contract ambiguity raised during (3)+(4)): LABEL-REMOVE both
  `status: in-spec-review` and `status: processing`, then re-dispatch the
  paused side (normally `qa`) with the amended contract so it resumes. When
  `qa` reports its suite complete, CR-READY its CR — until then it stays
  draft. Report the amendment and what resumed.
- **Post-integration re-entry** — `<feat-branch>` / `<qa-branch>` exist but are
  **merged** (the issue came back from (7): the user's review raised something
  that changed what a rule means). The work is built, so this never returns to
  implementation. Fold, then: if the amendment changed behaviour, honour the
  **hand-back rule** — re-run config `acceptance_test` and config `test` on
  `<spec-branch>`, capture the output, regenerate the gate kit's evidence cards
  wholesale and re-stamp `cards-sha`. A red here is the stage-(6) taxonomy
  (`commands/integrate.md` step 5), never an assertion edited to match. Then
  LABEL-REMOVE both `status: in-spec-review` and `status: processing`,
  LABEL-ADD `status: in-user-review` — the conversation resumes at (7) where
  it paused. Report the amendment and the re-run's result.

If threads remain open: LABEL-REMOVE `status: processing` and list which
questions are still waiting.

Whichever branch ran, end step 7 with
`git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch>`
then `git worktree prune`.

## 8. The STOP exit
On anything this command cannot or should not decide — a fold that keeps
failing, a rejected push, an impossible state: follow the STOP protocol.
`git worktree remove --force` the `<spec-branch>` worktree **if this run created
it** (the uncommitted spec edits live nowhere else; the user's checkout was
never touched — and a refused `worktree add` means the worktree is another
run's, so remove nothing), replace the issue's status
labels with `status: blocked` alone, and ISSUE-COMMENT: what happened and
your recommended next step as the must-read, the evidence folded under
`<details><summary>Evidence</summary>`. Name the half-done thread if there is
one — a folded-but-unresolved thread will be re-folded on re-run, and the human
should know. Already-resolved threads are idempotent; a re-run skips them.

## 9. Report
Per issue: which questions you folded, which got follow-ups, any issue comments
posted for story-level changes, what resumed (mid-flight) or what is still
outstanding — and, if you stopped, which exit and why.
