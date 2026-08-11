---
description: One patrol pass — scan open issues' worn state, auto-invoke the right workflow command, triage the inbox, and report what waits on the user
---

One **patrol pass** over the loop (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → Invocation policy). Read
state, act once, report. Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. A legacy `### Gated Loop config` block (the plugin's
pre-1.0 name) counts as present — use its values and flag the re-init in the
report.

**Personas**: every role dispatch below (`product`, `implementer`,
`reviewer`) resolves through the `### Roz Gate personas` block — dispatch the
mapped subagent, attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults (`roz-gate:<role>`; implementer = the project's
`implementer` agent).

**Version check**: compare the workflow section's
`<!-- roz-gate workflow-template vN -->` stamp against the one in
`${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE-workflow.md`. Stamp missing or
different → the section's shape is out of date: flag it in the report
("re-run `/roz-gate:init` to refresh the workflow section") and ignore any
workflow prose embedded in CLAUDE.md (a fat pre-0.6 copy) — the plugin's
`references/workflow.md` and command files are authoritative. A matching
stamp means no re-init is needed, whatever the plugin version.

## 1. Scan
- ISSUE-LIST (all open issues).
- Issues **without a `track:` label** are the **inbox** — pre-loop, valid, kept
  for step 2's inbox row only.
- For issues with a `track:` label, validate the invariants (exactly one
  `track:`; at most one `status:` besides the processing lock; `track: fast`
  never with a spec-stage status). An issue in an illegal state: **skip it and
  report it** — never repair labels.
- Skip any issue with `status: processing` (locked by a running command) or
  `status: blocked` (a stopped step awaits the human — list it in the report's
  user queue, with its latest issue comment).

## 2. Classify each remaining issue

| State | Meaning |
|---|---|
| `status: ready-for-spec` / `ready-for-dev` | actionable → `/roz-gate:next-stage <n>` |
| `status: in-spec-review` | THREADS-LIST on its spec CR. Any unresolved thread whose last comment is a human answer (does not start with `**[` / `✅`) → actionable → `/roz-gate:spec-answers <n>`. Otherwise → waiting on the user |
| no `status:`, `track: spec` | in flight: CR-FIND for `feat/<n>` and `qa/<n>`. Implementation CR exists with **zero open review threads** AND QA CR exists **and is not a draft** → actionable → `/roz-gate:integrate <n>`. Implementation CR has **open review threads** → actionable → **address-review** (below). Otherwise → in progress, not actionable |
| no `status:`, `track: fast` | in flight: its CR has **open review threads** → actionable → **address-review**; review-clean → LABEL-ADD `status: in-user-review` and treat as waiting on the user |
| `status: in-user-review` | waiting on the user |
| `status: blocked` | waiting on the user — never re-invoke anything on it |
| no `track:` label (inbox) | actionable → **async intake** (below) when a gate label is present (finalize), the gate holder's latest comment requests a summary, or no questions batch exists yet; otherwise the discussion is the humans' — waiting on the user |

## 3. Act — one loop issue per pass, plus the whole inbox
In-loop work: pick the actionable issue **closest to done** — priority:
`/roz-gate:integrate` > address-review > `/roz-gate:spec-answers` >
`/roz-gate:next-stage` (`ready-for-dev`) > `/roz-gate:next-stage`
(`ready-for-spec`) — and perform that action. If nothing is actionable, act
on nothing.

Then triage **every** actionable inbox issue (async intake, below), one
dispatch per issue. Intake is comment-only — no code, no gate labels — so it
is exempt from the one-issue rule: after a single pass, everything that waits
on the user is already posted.

### The address-review action — the (5) loop's engine
For an in-flight CR with open review threads:
1. Lock: LABEL-ADD `status: processing` (so the next pass doesn't
   double-dispatch).
2. Spec track: dispatch `implementer` on the CR's branch to address each open
   thread — fix and/or reply, push. Fast track: the main agent addresses its
   own CR's threads directly (it wrote the code; `implementer` is never
   dispatched onto `fast/<n>`).
3. Dispatch `reviewer` to re-check the addressed threads and THREAD-RESOLVE
   those it is satisfied with; what stays open waits for the next round.
4. Clear the lock. Failures follow the STOP protocol.

### The async-intake action — the inbox's engine ((1b))
For an open issue with no `track:` label. **Gate holder** = the issue's
assignee (unassigned → the issue author, **if human**). A bot identity
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
3. Clear the lock. Never apply a gate label. Failures follow the STOP protocol.

## 4. Report
A short table: issue · state · action taken this pass, or what it waits on and
who. End with the user's queue: what (if anything) needs them — answer threads,
answer intake questions, say `summary`, confirm a summary with the gate
label, apply a gate label, or review &
merge — with links.

## 5. Notification (optional)
If a messaging channel (e.g. Telegram) is connected and an issue **newly**
entered a waiting-on-you state this pass, send a one-line notification with
the link. If no channel is configured, skip silently.

Hard rules: never apply a gate label; never run intake for the user beyond the
protocol above; anything unexpected (failed command, merge conflict, illegal
state) → stop and report, never improvise.
