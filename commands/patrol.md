---
description: One patrol pass — a read-only scanner sub-agent classifies every issue into one table; the main agent acts on it (one loop issue, every close-out, the whole inbox) and reports what waits on the user
---

One **patrol pass** over the loop (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → Invocation policy). A
scanner sub-agent reads state into one table; you act once from it, report. Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. A legacy `### Gated Loop config` block (the plugin's
pre-1.0 name) counts as present — use its values and flag the re-init in the
report. **Local keys** — `default_branch`, `inbox_label`, `inbox_assignee` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists). The report names the
effective values of the three.

**Model**: `patrol_model` in the config block, when present, is the model
every seat dispatched from this command runs on (`product` for async intake,
`implementer` for address-review); absent → the runtime's default. It never
changes the model this command itself runs on — that is the session's.

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

Dispatch **one** sub-agent (the plugin default `general-purpose`; it
dispatches nothing itself) with, as its whole prompt:
`${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md` (the scan and
classification rules — this command does not repeat them), the forge
adapter path (`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`), and the
three local keys from `bin/roz-config --json`, and the config block's
`bot_login` list (normalized: `app/` prefix and `[bot]` suffix stripped;
empty in user mode) so the scanner can tell a human holder from a bot. The
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
fast CR), LABEL-ADD `status: in-user-review` — a status report, not a stage
advance, so exempt from the one-issue rule; the issue now waits on the user.

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
   `feat/<n>`; QA CR fidelity threads → dispatch `qa` on `qa/<n>` **under
   the fidelity-dispatch procedure** (next-stage.md B5b: marker on,
   dispatch, marker off — guard-blind denies any `src/` read or `feat/`
   action while it runs) (it may
   decline a finding that lacks verbatim citations) — fix and/or reply,
   push. Fast track: the main agent addresses its own CR's threads directly
   (it wrote the code; `implementer` is never dispatched onto `fast/<n>`).
3. Dispatch `reviewer` to re-check the addressed threads and THREAD-RESOLVE
   those it is satisfied with; what stays open waits for the next round.
   Re-checks of QA-CR fidelity threads use a fresh implementation-blind
   dispatch under the fidelity brief, on `qa/<n>` only — the same
   fidelity-dispatch procedure (marker on, dispatch, marker off).
4. Remove the worktree(s), clear the lock. Failures follow the STOP protocol
   — the `blocked` comment's evidence folds under
   `<details><summary>Evidence</summary>`.

### The async-intake action — the inbox's engine ((1b))
For an open issue with no `track:` label. **Gate holder** = the row's
`holder` column — the issue's assignee (unassigned → the issue author, **if
human**), read from the table, never re-listed. A bot identity
(`bot_login`) never holds a gate: a bot-authored, unassigned issue has **no
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
     never blocking); if the holder commented after it, or no summary
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
     `**[intake]**`. Asked **once** — patrol never re-batches; unanswered
     questions surface later as assumptions in the summary.
   - **Otherwise** → not actionable: the thread belongs to the humans until
     the gate holder requests a summary or applies a gate label.
3. Clear the lock. Never apply a gate label. Failures follow the STOP
   protocol — the `blocked` comment's evidence folds under
   `<details><summary>Evidence</summary>`.

## 4. Report
A short table: issue · state · action taken this pass, or what it waits on and
who. When an inbox filter is configured, one line under the table states the
filter and the count it excluded — `inbox filter: label discuss · N
track-less issues not in the inbox filter` — so a quiet inbox is never a
mystery. End with the user's queue: what (if anything) needs them — answer threads,
answer intake questions, say `summary`, confirm a summary with the gate
label, apply a gate label, or review &
merge — with links. Close-outs appear in the table as `shipped`. The table, the filter line and the queue are the
**must-read**; anything else — per-issue notes, why an issue was skipped,
what a lock looked like — goes under a trailing `## Details` heading after
the queue (this report is printed to a terminal, not a forge, so it uses a
heading rather than a `<details>` tag). Nothing that needs the human is ever
only in Details.

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
