---
description: One patrol pass — a read-only scanner sub-agent classifies every issue into one table; the main agent acts on it (one loop issue, every close-out, the whole inbox) and reports what waits on the user
---

One **patrol pass** over the loop (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → Invocation policy). A
scanner sub-agent reads state into one table; you act once from it, report. Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (or CLAUDE.local.md), then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. A legacy `### Gated Loop config` block (the plugin's
pre-1.0 name) counts as present — use its values and flag the re-init in the
report. **Local keys** — `default_branch`, `inbox_label`, `inbox_assignee`,
`helper_model`, `branch_user`, `branch_template` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists, empty strings). **Branch names**: bind `<spec-branch>`,
`<feat-branch>`, `<qa-branch>`, `<fast-branch>` per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md` (the local key
`branch_template`, `""` → `{kind}/{n}`; an existing branch is found by
Lookup, never guessed). Nothing below spells a branch name. The report names the
effective values of the four.

**Model**: `helper_model` from `bin/roz-config --json`, when set, is the
model the two mechanical sub-agents run on — the **scanner** (§1) and the
**commit** sub-agent (address-review, step 2 below) — basic work that a
cheaper model does; absent (`""`) → the runtime's default. Seats (`product`,
`implementer`, `reviewer`) always run on the runtime default: no key
configures them. It never changes the model this command itself runs on —
that is the session's.

**Personas**: every role dispatch below (`product`, `implementer`,
`reviewer`) resolves through the `### Roz Gate personas` block — dispatch the
mapped subagent, attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults (`roz-gate:<role>`; implementer = the project's
`implementer` agent).

**Version check**: compare the workflow section's
`<!-- roz-gate workflow-template vN -->` stamp against the one in
`${CLAUDE_PLUGIN_ROOT}/templates/claude-workflow.md`. Stamp missing or
different → the section's shape is out of date: flag it in the report
("re-run `/roz-gate:init` to refresh the workflow section") and ignore any
workflow prose embedded in CLAUDE.md (a fat pre-0.6 copy) — the plugin's
`references/workflow.md` and command files are authoritative. A matching
stamp means no re-init is needed, whatever the plugin version.

## 1. Dispatch the scanner — read state through one sub-agent

Dispatch **one** sub-agent (the plugin default `general-purpose`, on
`helper_model` when set; it dispatches nothing itself) with, as its whole prompt:
`${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md` (the scan and
classification rules — this command does not repeat them), the forge
adapter path (`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`), and the
local keys from `bin/roz-config --json` (`helper_model` is the dispatch's
model, not a value the scanner reads), and the config block's
`bot_login` list (normalized: `app/` prefix and `[bot]` suffix stripped;
empty in user mode) so the scanner can tell a human holder from a bot, the
local `branch_template` (`""` → `{kind}/{n}`), and **the remote's
heads** — the output of one `git ls-remote --heads origin`, run by you
here (a query of the remote; it touches no checkout and no local ref) —
so the scanner can bind every issue's branch names by Lookup
(`references/branch-names.md`) without running git itself. The
scanner is **read-only**
and returns the table the brief defines; everything it read stays in its
context, not yours.

## 2. The table is the only source

The scanner's table (columns `issue · track · status · holder · cr · unheard ·
verdict · evidence`, then the `inbox filter:` line) is the state of the loop for this
pass. **Never re-read the forge to confirm a row** — no ISSUE-LIST, no
CR-FIND, no channel listing in this command; the action you take on an issue
reads what *it* needs (a `/roz-gate:review-answers` turn reads its CR). A row
you cannot act on as written — a verdict outside the brief's list, a missing
`cr` for an actionable row — is reported as an illegal state, never
re-derived. The report's rows and the user's queue cite the `evidence`
column.

## 3. Act — one loop issue per pass, plus the whole inbox
In-loop work: from the rows whose `verdict` starts with `actionable:`, pick the
issue **closest to done** — priority:
`/roz-gate:review-answers` > `/roz-gate:integrate` > address-review >
fidelity-audit > code-review > `/roz-gate:next-stage` (`qa` — Path B2) >
`/roz-gate:spec-answers` > `/roz-gate:next-stage` (`ready-for-dev`) >
`/roz-gate:next-stage` (`ready-for-spec`) — and perform that action. The (7)
conversation ranks first: it is definitionally the closest to done, and the
person waiting there never queues behind machine work. If nothing is
actionable, act on nothing.

A `/roz-gate:review-answers` turn that only **answers** — no seat dispatch, no
commit — is exempt from the one-issue rule, like intake: it costs a comment,
and a multi-day conversation must not starve the rest of the loop. A turn that
dispatches or commits consumes the pass.

Then, for every row with verdict `hand-off: in-user-review` (a review-clean
fast CR — its `**[reviewer] · code-review**` record current and zero threads,
never zero threads alone), LABEL-ADD `status: in-user-review` — a status
report, not a stage advance, so exempt from the one-issue rule; the issue
now waits on the user.

Then **close out every** issue whose CR is merged (the rows with verdict
`close-out`; the action below) — a
finalize, not a stage advance, so like intake it is exempt from the
one-issue rule.

Then triage **every** actionable inbox issue (the rows with an `intake:`
verdict; async intake, below), one dispatch per issue. Intake is comment-only — no code, no gate labels — so it
is exempt from the one-issue rule: after a single pass, everything that waits
on the user is already posted.

### The close-out action — labels retire at close
For an issue at `status: in-user-review` whose CR is **merged**. The forge
closes the issue itself only when its own rule fires (GitHub: `Closes #<n>`
in the body **and** a CR targeting the repository's default branch; GitLab:
the same keyword, and only against the default branch) — a release-branch
base or a GitLab MR leaves the issue open wearing `in-user-review`. Patrol
finishes it, in this order — the comment is the durable marker, so a pass
interrupted anywhere after it is recognized and resumed by the next scan,
and a pass interrupted before it has written nothing:
1. ISSUE-COMMENT one line: `**[patrol] · shipped** — <CR url> merged; labels
   retired.` Skip if a `**[patrol] · shipped**` comment is already there.
2. ISSUE-CLOSE, if still open.
3. LABEL-REMOVE every `track:` and `status:` label the issue still wears
   (skip what is already gone) — last, because without a label the issue
   drops out of the scan.
No lock: every step is idempotent and nothing dispatches. A merged CR on an
issue in **any other** status, with no shipped marker, is an illegal state —
report it, never repair.

### The address-review action — the (5) loop's engine
For an in-flight CR with open review threads. Every dispatch below works in
a linked worktree of its branch
(`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>`
after a `git fetch`; `git worktree remove --force` + `git worktree prune`
at step 4 and on STOP) — patrol itself never runs git in the user's checkout;
its scan is forge calls only
(`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → The main agent → The
workspace).
1. Lock: LABEL-ADD `status: processing` (so the next pass doesn't
   double-dispatch).
2. Spec track: implementation CR threads → dispatch `implementer` on
   `<feat-branch>`; QA CR fidelity threads → dispatch `qa` on `<qa-branch>` **under
   the fidelity-dispatch procedure** (next-stage.md B2.7: marker on, carrying
   `feat=<feat-branch>`, the test port's `read=` lines and `seat=qa`, dispatch, marker
   off — guard-blind denies any
   `src/` read outside `<acceptance_dir>` and the port, or git action on
   `<feat-branch>`, while it runs; the `<qa-branch>` carries the
   implementation since 2.0.0, so the marker is the blindness) (it may
   decline a finding that lacks verbatim citations) — fix and/or reply.
   Fast track: the main agent addresses its own CR's threads directly
   (it wrote the code; `implementer` is never dispatched onto `<fast-branch>`).
   Either way the seat never commits: commit through the **commit**
   sub-agent — one dispatch per branch, on `helper_model` when set,
   `${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the worktree
   path, branch, files and message; it returns one `branch · sha · hook`
   row and the pre-commit output stays out of your context — then push
   from the returned `sha` (`no-verify:` → say so; `failed:` → STOP with
   the excerpt).
3. Dispatch `reviewer` to re-check the addressed threads and THREAD-RESOLVE
   those it is satisfied with; what stays open waits for the next round.
   On the implementation CR (spec or fast track), when the re-check resolves
   the **last** open thread, it COMMENT-EDITs the CR's
   `**[reviewer] · code-review**` record so its `reviewed-sha:` is the head
   it re-checked — one record, re-stamped; a head it did not re-check keeps
   the old SHA and the record reads stale (`workflow.md` (5)).
   Re-checks of QA-CR fidelity threads use a fresh implementation-blind
   dispatch under the fidelity brief, on `<qa-branch>` only — the same
   fidelity-dispatch procedure (contract currency by you, marker on,
   dispatch, marker off). A re-check
   posts no second summary — the first audit's `**[reviewer] · fidelity**`
   comment stays the record.
4. Remove the worktree(s), clear the lock. Failures follow the STOP protocol
   — the `blocked` comment's evidence folds under
   `<details><summary>Evidence</summary>`.

### The code-review action — the review that never ran (or never re-checked)
For an in-flight implementation CR (`track: spec`, `<feat-branch>`) or fast CR
(`track: fast`, `<fast-branch>`) whose `**[reviewer] · code-review**` record
is missing, or whose `reviewed-sha:` is not the CR's head: B5 (or C6) stopped
before the reviewer posted, or the head moved without a re-check — and a
thread-clean CR would otherwise read as a reviewed one (#95's shape on the
implementation side; #140 ruling 9). Patrol runs the review alone.
1. Lock: LABEL-ADD `status: processing`.
2. `git fetch`, then
   `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>`
   for the CR's head branch — a refusal (the branch is checked out
   elsewhere) → the STOP exit.
3. Dispatch the **reviewer** as next-stage B5 does (C6 on the fast track):
   the CR's diff against its base, `<specs_dir>/<n>/spec.md` and
   `technical-spec.md` attached (the issue body on the fast track), the
   as-built contract diff and the CR's `## Contract deviations` for a
   `track: spec` CR. It posts its severity-graded threads and, **last**, the
   `**[reviewer] · code-review**` record with `reviewed-sha: <head>` and the
   counts — the record this action exists to produce; a stale record is
   re-stamped by COMMENT-EDIT rather than duplicated. It never commits,
   never resolves a thread.
4. `git worktree remove --force` the worktree, `git worktree prune`, clear
   the lock. Failures follow the STOP protocol — the `blocked` comment's
   evidence folds under `<details><summary>Evidence</summary>`.

### The fidelity-audit action — the audit that never ran
For a `track: spec` issue whose QA CR exists, is not a draft, and carries no
`**[reviewer] · fidelity**` comment: B2.7 stopped before the reviewer posted (a
denied read, a killed run), and a thread-clean suite would otherwise read as
an audited one. Patrol runs the audit alone — nothing else of B2.7.
1. Lock: LABEL-ADD `status: processing`.
2. `git fetch`, then
   `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<qa-branch> <qa-branch>`
   — a refusal (the branch is checked out elsewhere) → the STOP exit.
3. **The fidelity-dispatch procedure** (next-stage.md B2.7, verbatim):
   contract currency by you first — THREADS-LIST on both CRs, the
   amendment list and the implementation CR's `## Contract deviations`
   (copied verbatim under `Contract deviations:`) into the dispatch text,
   no dispatch on a (5) breach —
   then write the marker —
   `mkdir -p "$(git rev-parse --git-common-dir)/roz-gate" && printf 'issue=<n>\nfeat=<feat-branch>\nread=<path>\nseat=<seat>\n' > "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`
   — one `read=<path>` line per path `technical-spec.md`'s `**Test port**`
   line names, none for `none`, `seat=reviewer`, and the same paths on a line of their own
   in the dispatch text, `Test port: …` (B2.7, #125) — then dispatch the **reviewer** seat in a
   **fresh context** with
   `${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract, in
   the `<qa-branch>` worktree; immediately after it returns,
   `rm -f "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`.
   The dispatch posts its two-way-cited threads on the QA CR and the
   `**[reviewer] · fidelity**` summary — the record this action exists to
   produce. It never commits, never touches `<feat-branch>`, never resolves
   a thread.
4. `git worktree remove --force` the worktree, `git worktree prune`, clear
   the lock. Failures follow the STOP protocol — the `blocked` comment's
   evidence folds under `<details><summary>Evidence</summary>`.

### The async-intake action — the inbox's engine ((1b))
For an open issue with no `track:` label. **Gate holder** = the row's
`holder` column — the issue's assignee (unassigned → the issue author, **if
human**), read from the table, never re-listed. A bot identity
(`bot_login`, or the forge's bot shape — `patrol-scan.md`'s human-comment
test) never holds a gate: a bot-authored, unassigned issue has **no
gate holder** — only the questions batch may be posted on it, and the
report lists it in the user's queue as "needs an assignee". The thread is
free-form and open to
anyone; the clarification thinking is always the dispatched `product` agent's
(async mode, with `${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md`, the
issue body, and all comments), never patrol's own.
1. Lock: LABEL-ADD `status: processing`.
2. Route by the issue's state — first match wins:
   - **Gate label present** (`ready-for-spec` / `ready-for-dev` on this
     track-less issue — the gate holder's confirmation, possibly without a
     prior summary) → **finalize**. The label means "build the story from
     everything I said": **only the gate holder's words drive the issue
     body**. Obtain the summary — reuse the latest `**[intake] · summary**`
     comment **verbatim** if no gate-holder comment follows it (comments
     from anyone else are thread discussion: never folded in, never listed,
     never a reason to wait); if the holder commented after it, or no summary
     exists, dispatch for a fresh one whose fold-in scope is **the holder's
     words only** (bystander input is context, folded in solely through the
     holder's explicit endorsement) and ISSUE-COMMENT it, prefixed
     `**[intake] · summary**` — the paper trail precedes the body edit.
     Then ISSUE-EDIT-BODY to its story template (user story / acceptance
     criteria / context), LABEL-ADD the track the label choice itself
     confirms: `ready-for-spec` ⇒ `track: spec`, `ready-for-dev` ⇒
     `track: fast`. The issue is now at (1a), already gated — the next pass
     advances it.
   - **The gate holder's latest comment requests a summary** — its first or
     last non-empty line, stripped of emphasis/backticks/quotes and case,
     is exactly `summary`, so corrections and the request can share one
     comment — (and no `**[intake] · summary**` has been posted since it)
     → dispatch for the summary; ISSUE-COMMENT it, prefixed
     `**[intake] · summary**`. A summary request from anyone else never
     triggers.
   - **No `**[intake]**` questions comment exists yet** → dispatch for the
     question batch; ISSUE-COMMENT it verbatim as **one comment**, prefixed
     `**[intake]**`. The batch is asked **once** — patrol never re-batches;
     unanswered questions surface later as assumptions in the summary.
   - **A human comment follows the latest agent `**[intake]` comment** (the
     scan's human-comment test, `patrol-scan.md` — from anyone, not only
     the holder; a bot or an agent-marker comment never counts) → dispatch
     for a **reply** (the brief's reply deliverable); ISSUE-COMMENT it
     verbatim as **one comment**, prefixed `**[intake] · reply**` — one per
     issue per pass, covering every human comment since that `**[intake]`
     comment. A reply answers; it never re-asks the batch, never edits the
     body or a label, never @-mentions anyone, and decides nothing — only
     the holder's `summary` line and gate label act. guard-gate rule I
     denies a reply with no human comment to answer (#174).
   - **Otherwise** → not actionable: no human has spoken since the latest
     `**[intake]` comment — the thread waits on the humans.
3. Clear the lock. Never apply a gate label. Failures follow the STOP
   protocol — the `blocked` comment's evidence folds under
   `<details><summary>Evidence</summary>`.

## 4. Report
The report is the scanner's table rendered for the user, plus what this pass
did — one fixed shape, so the first screen of a phone-width read says
everything that needs them. Patrol has no memory across passes and the
reader has no previous report in front of them: every row states its own
state and its own wait, and no row cites another pass — "unchanged",
"same as previous pass", "see last pass" are not clauses.

**The table** — this header, one row per issue the scanner listed (open loop
issues, close-out candidates, locked, `blocked`, inbox issues in the filter),
in the scanner's order, nothing else in it:

`| issue | state | this pass | needs you |`

- `issue` — `#n title`. No links here: the report is a terminal print, and
  links live in the queue.
- `state` — the scanner's `track · status` as read: `spec · in-spec-review`,
  `fast · ready-for-dev`, `spec · in flight` (no `status:`), `spec · blocked`,
  `inbox`.
- `this pass` — **one clause, at most 12 words**, from this vocabulary:
  `acted: <action> — <outcome>` · `queued: <action>` · `waits on you: <what>`
  · `blocked: <the STOP comment's title>` · `locked: <phase> · <age>` ·
  `illegal: <why>` · `shipped` · `in progress`. Never a list, never a commit
  log — that is Details material. The scanner's gate-label audit reads
  `illegal: gate label applied by <login>`.
- `needs you` — `yes` or `—`; `yes` whenever the next move is a human's: a
  wait, a `blocked`, an illegal row, a stale lock, an intake batch, an
  intake reply or a `· question` posted this pass, a review to merge.

Then the filter line, when an inbox filter is configured — `inbox filter:
label discuss · N track-less issues not in the inbox filter` — so a quiet
inbox is never a mystery.

**The queue** — `Your queue:` then exactly the `needs you` rows, in table
order, one line each, `- #n — <verb phrase> — <link>` (answer the threads,
answer the intake questions, read the intake reply, say `summary`, apply
the gate label, decide the STOP, review & merge, needs an assignee, clear
a stale lock, remove
the gate label `<login>` applied — then reapply it yourself to authorize:
re-adding a label already worn records no new event, so the bot's stays
the latest). A row
that does not need them is not a queue item; a queue item without its link
is not written. What §0 flags for the **whole loop**, not an issue — the
workflow stamp missing or outdated, a legacy config block — is a queue item
too, `- loop — re-run /roz-gate:init — <why>` (no link: nothing on the forge
to open); the effective branch names §0 has the report state go under
Details.

**A row the pass cannot act on as written** — a verdict outside the brief's
list, a missing `cr` for an actionable row (§2), a gate label the scanner's
audit found applied by a bot identity (`references/patrol-scan.md`), a scan that contradicts
what this session read earlier (`blocked` now, `illegal state` a pass ago)
— is `illegal: <why>` with `needs you: yes` and a queue item (`decide:
<why>`); never a note under Details, never re-derived.

The table, the filter line and the queue are the **must-read**; anything
else — per-issue notes, what a dispatch returned, why a row was skipped,
what a lock looked like — goes under a trailing `## Details` heading after
the queue, omitted when empty (this report is printed to a terminal, not a
forge, so it uses a heading rather than a `<details>` tag). Nothing that
needs the human is ever only in Details.

## 5. Notification (optional)
If a messaging channel (e.g. Telegram) is connected and an issue **newly**
entered a waiting-on-you state this pass, send a one-line notification with
the link. If no channel is configured, skip silently.

At (7) notify on what this pass **did**, not on a transition: the label sits at
`in-user-review` from the first comment to the merge, so it never *newly*
enters anything and a conversation would otherwise be answered into silence.
Any `**[review] · question**` or `· addressed` posted this pass is a
notification.

Hard rules: never apply a gate label; never run intake for the user beyond the
protocol above; anything unexpected (failed command, merge conflict, illegal
state) → stop and report, never improvise.
