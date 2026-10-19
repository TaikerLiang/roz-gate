---
description: What does issue #n need next? Read its labels, CRs, threads and branches, answer from the workflow — your move, the loop's move, and what is off when the state is illegal or stuck. Read-only; answers in the terminal
argument-hint: "<n>"
---

One issue, one answer: what #<n> needs next, from its live state and the
workflow this plugin ships. You type this command; patrol never does. Follow
these steps; do nothing beyond them.

**Read-only.** This command writes nothing: no label, no comment, no commit,
no branch, no lock. Every forge call below is a read op of the adapter, and
the only git calls are `git ls-remote` and `git worktree list`. Asked to act
on what it finds, name the command or the human act that does it — never do
it here.

**The argument.** `n` is required: without it, say so and stop — patrol's
report is the whole-loop view; this command answers for one issue.

## 0. Load config, adapter, names

Read the `### Roz Gate config` block in the project's CLAUDE.md (or
CLAUDE.local.md), then `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`
for the concrete CLI behind every CAPITALIZED-OP. Missing config → stop; tell
the user to run `/roz-gate:init`. **Local keys** — `default_branch`,
`branch_user`, `branch_template`, and the inbox filter `inbox_label` / `inbox_assignee` — from
`python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`; the block's `bot_login`
list (normalized as patrol does: `app/` prefix and `[bot]` suffix stripped)
tells a human holder from a bot.
**Branch names**: run one `git ls-remote --heads origin` (a query of the
remote; it touches no checkout and no local ref) and bind `<spec-branch>`,
`<feat-branch>`, `<qa-branch>`, `<fast-branch>` by **Lookup** over it per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md` (the local key
`branch_template`, `""` → `{kind}/{n}`; several attempts → the highest
`{seq}` is the live one, the others are earlier attempts). Nothing below
spells a branch name.

This command takes no `processing` lock: the lock belongs to state-mutating
commands (`references/workflow.md` → Command lifecycle), and this one mutates
nothing. A lock it finds on the issue is part of the answer, never something
it waits on or clears.

## 1. Read — the reads, and only these

- ISSUE-VIEW #<n>: its `track:` / `status:` labels, assignees (the gate
  holder: assignees minus the block's `bot_login`s, else the author if
  human), the last comment's marker (`**[<command>] · blocked**` and its
  **To resume:** line; `**[intake] · summary**`; `**[patrol] · shipped**`).
- CR-FIND in its **all-states form** for every bound branch that Lookup
  found on the remote: the CR's number, state (`open` / `draft` / `merged`
  / `closed` / none), url.
- On each **open** CR, the three channels — THREADS-LIST (inline threads),
  REVIEWS-LIST (review summary bodies — GitHub only), CR-COMMENTS-LIST
  (top-level comments). An item is **unheard** when its latest entry does
  NOT start with `**[` or `✅ [` (the rule `references/patrol-scan.md`
  classifies by); a thread is **answered** when it is unresolved and its
  last comment is a human's; a thread with one human comment and no agent
  reply is an **amendment request** (`spec-answers` folds it).
- `git worktree list`: a worktree under `.git/roz-gate/wt/` on one of the
  bound branches is a leftover of a killed run when no command is running.
- The fidelity record: on the QA CR, CR-COMMENTS-LIST for a
  `**[reviewer] · fidelity**` comment — stage (6) requires it. The
  code-review record: on the implementation CR (or the fast CR),
  CR-COMMENTS-LIST for a `**[reviewer] · code-review**` comment and whether
  its `reviewed-sha:` is the branch's head in the `ls-remote` output —
  review-clean is that record current **and** zero open threads
  (`workflow.md` (5)), never zero threads alone.

No ISSUE-LIST, no other issue, no dispatch: one issue, read once. Everything
you need to answer is in these reads and in
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` (the loop, the label state
machine, the owner table, the STOP protocol), `references/branch-names.md`
(Re-entry) and `references/patrol-scan.md` (the classification table).

## 2. Classify — the normal states

Match the labels and the CRs against `workflow.md` → Label state machine and
`patrol-scan.md` → Classify. Each normal state has two answers — **yours**
(the human's move) and **the loop's** (what the next patrol pass, or which
command, does if you do nothing):

| state | yours | the loop's |
|---|---|---|
| no `track:`, **outside the inbox filter** (`inbox_label` / `inbox_assignee` set and not matched) | bring it into your inbox — add one of the filter labels or assign a filtered login — or file it with `/roz-gate:to-issues` | nothing — patrol only counts it, even with a gate label on (`patrol-scan.md § Scan`) |
| no `track:` (the inbox, in the filter), no `**[intake]**` batch yet | nothing — or run `/roz-gate:patrol` now | the next pass posts the questions batch (async intake, (1b)) |
| inbox, batch posted, no summary requested | the gate holder answers in the comments; ends a comment with `summary` when it settles, or applies the gate label directly | nothing until the holder speaks |
| inbox, the gate holder's latest comment requests `summary` (its first or last non-empty line, stripped of emphasis/backticks/quotes and case, is exactly `summary`; no `**[intake] · summary**` since) | nothing | the next pass posts the `**[intake] · summary**` (`patrol.md` → the async-intake action) |
| inbox, `**[intake] · summary**` posted | the holder applies `ready-for-spec` (⇒ `track: spec`) or `ready-for-dev` (⇒ `track: fast`) — the label is the confirmation; corrections: reply, end with `summary` | finalize on the next pass after the label: body rewrite + the `track:` |
| `spec` + `ready-for-spec`, or `fast` + `ready-for-dev`, no branch of that kind on the remote | nothing — you authorized it | `/roz-gate:next-stage <n>` cuts the branch on the next pass: (2) the spec stage, or the fast track |
| `spec` + `ready-for-dev`, the spec CR open — the one you approved | nothing — you authorized it | `/roz-gate:next-stage <n>` launches (3)+(5) off `<spec-branch>` on the next pass (Path B); QA follows once the implementation lands |
| `in-spec-review`, an unresolved thread whose last comment is yours (answered), or a thread you opened | nothing further | `/roz-gate:spec-answers <n>` folds it on the next pass |
| `in-spec-review`, unresolved threads awaiting you | answer each inline on the spec CR — each is one contract clause with a recommendation; or open a thread yourself for a gap | nothing until you answer |
| `in-spec-review`, every thread resolved, nothing unheard | apply `status: ready-for-dev` — all threads resolved is the (2) → (3) gate (`workflow.md` → owner table) | nothing until the label; then `next-stage` launches (3)+(5) |
| no `status:`, `track: spec`, the implementation CR open, no QA CR (in flight, (3)) | nothing — unless a CR thread is `· question` to you | address-review while the CR has open review threads; patrol's `code-review` action when its `**[reviewer] · code-review**` record is missing or stale; **review-clean** (record current, zero threads) → `/roz-gate:next-stage <n>` runs Path B2: lands the implementation on `<spec-branch>` and launches (4)+(5q) — the next pass does whichever applies (`workflow.md` (3)/(5), `patrol-scan.md § Classify`) |
| no `status:`, `track: spec`, the implementation CR merged, no QA CR | nothing | `/roz-gate:next-stage <n>` (Path B2) cuts `<qa-branch>` off the spec tip and launches (4)+(5q) on the next pass |
| no `status:`, `track: spec`, the implementation CR merged (or review-clean), the QA CR open (in flight, (4)) | nothing — unless a CR thread is `· question` to you, or a `[qa]` thread on the spec CR is yours to answer (then the issue wears `in-spec-review`) | address-review while the QA CR has open fidelity threads; the fidelity audit when it lacks its record; `/roz-gate:integrate <n>` when it is ready, audited and thread-clean (or merged) — the next pass does whichever applies |
| no `status:`, `track: fast`, CR open | nothing | address-review while threads are open; patrol's `code-review` action when the record is missing or stale; review-clean (record current, zero threads) → the pass applies `in-user-review` |
| `in-user-review`, something unheard on the CR | nothing further — you were heard | `/roz-gate:review-answers <n>` on the next pass |
| `in-user-review`, the last agent marker is `· question` | reply on the CR — that answer is what (7) waits on | nothing until you reply |
| `in-user-review`, nothing unheard, no `· question` | review the CR: **merge it, change it (comment — `review-answers` hosts the turn), or send it back to intake** (strip `track:` + `status:`) | nothing until you move |
| `in-user-review`, the CR **merged** | nothing | the next pass's **close-out** (labels off, issue closed) — the forge may already have closed it |
| `blocked` | read the last `**[<command>] · blocked**` comment: its evidence and its **To resume:** line say which label to clear, which to apply, where the answer goes — do that | nothing — patrol never re-invokes anything on `blocked` |
| `processing` beside a phase label | wait — a command holds the lock: this session's, or a scheduled patrol's in another; `Check:` says what the evidence shows | the running command's exit (Done or STOP) |

Cite the passage behind each line (`workflow.md § The loop (2a)`, `§ Label
state machine`, `§ (7) Review`, `branch-names.md § Re-entry`,
`patrol-scan.md § Classify`) — the answer is a reading of the documents,
never a new rule.

## 3. Classify — illegal or stuck states

Each of these is a `Check:` line: what is off, and the repair the documents
already give. Never perform the repair here.

- **`fast` + `ready-for-spec`** (or `fast` + `in-spec-review`): illegal
  (`workflow.md` → Label state machine). Fix the labels by hand — a fast
  issue is gated by `ready-for-dev`; a design need → `track: spec` +
  `ready-for-spec` (the escalation valve's pair).
- **Two `track:` labels, or two `status:` labels besides `processing`**:
  illegal; every command stops on it and none repairs it — remove the wrong
  one yourself.
- **`blocked` beside any other `status:`**: a STOP leaves `blocked` alone;
  the pair means a hand edit after the stop. Clear the extra label, then act
  on the STOP comment's resume line.
- **A gate label on a track-less issue**: the one legal transient of intake
  — the next pass finalizes it (`workflow.md` → Label state machine). Nothing
  to fix.
- **`processing` beside a phase label**: a lock, not a phase. This command
  cannot tell a live lock from a stale one from its reads — a scheduled
  patrol may hold it from another session, and the label carries no age
  here — so it never declares the lock stale. It reports the pair, the
  phase the label names, and the evidence: a worktree on the issue's bound
  branch (`git worktree list`) is a run in progress or its leftover; a lock
  older than a pass takes with no worktree and no new comment is a killed
  run. Clearing it is yours, after you have checked that nothing is running
  anywhere; then re-run that phase's command — commands are idempotent on
  re-entry (`README` → Troubleshooting).
- **A branch-cutting gate worn while that kind's branch exists on the remote**
  — `ready-for-spec` on `track: spec` with `<spec-branch>` found, or
  `ready-for-dev` on `track: fast` with `<fast-branch>` found (never `spec` +
  `ready-for-dev`: there the open spec CR is what you approved, and
  `next-stage` builds from it). CR-FIND says that CR is **open** → the gate
  label is wrong, not the branch (someone is still reviewing it;
  `next-stage` A2/C2 STOPs on it): remove the gate label, or close the CR
  first. CR **closed unmerged, or none** → a re-entry
  (`branch-names.md` → Re-entry): with a `{seq}` template the next pass cuts
  the next sequence and nothing is yours to do; without `{seq}` the stale
  branch is yours to remove — `git push origin --delete <branch>` (and
  `<feat-branch>` / `<qa-branch>` if present) — yours to run; the agent
  never does — then re-apply the gate label.
- **`in-user-review` with the CR merged and the issue still open**: the
  close-out never ran — the next patrol pass runs it; nothing yours.
- **`in-user-review` or `in-spec-review` with the CR missing or closed
  unmerged**: the conversation has no CR to live on — nothing listens. Your
  call: re-spec (route (ii): amend the issue, re-apply `ready-for-spec`;
  `workflow.md` → (2a) three routes) or send it back to intake (strip
  `track:` + `status:`).
- **No `status:`, `track: spec`, no CR on the remote**: not stuck — it was
  never gated. Apply `ready-for-spec` when you want design to start.
- **A leftover worktree** under `.git/roz-gate/wt/<branch>` with no lock on
  the issue: a killed run's. `git worktree list`, then
  `git worktree remove --force <path>` — yours; the next command would
  otherwise refuse the branch (`workflow.md` → The workspace). With the lock
  still on, see the lock above — it may be a run in progress.
- **A legacy config block or a stale workflow stamp**: not an issue state
  — say so in one line and point at `/roz-gate:init`.

## 4. Answer

Print exactly this, in the terminal:

```
**#<n> · <track label> · <status labels, or "no status">**
Yours:
- <one move per bullet, with its link, ending with the source — `workflow.md § …`>
The loop's:
- <what the next pass or which command does if you do nothing; "nothing until you move" when so>
Check:
- <only when step 3 found something: what is off, the repair, the source>
```

`Yours:` and `The loop's:` are always present (a bullet may read `nothing`);
`Check:` appears only when step 3 found something. Every bullet that names a
thread, a comment or a CR carries its url. Keep it to the moves: no summary
of the issue, no restatement of the workflow, no advice beyond what the
documents say.

Hard rules: never apply or remove a label; never post a comment, a reply or
a review; never commit; never cut, delete or push a branch; never clear
`blocked`; never dispatch a seat. If the user then says "do it", the answer
names the command that does it — `/roz-gate:next-stage`, `spec-answers`,
`integrate`, `review-answers`, `patrol` — or the act that is theirs alone:
the gate label, the merge, the delete.
