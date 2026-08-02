---
description: One patrol pass — scan open issues' worn state, auto-invoke the right workflow command, triage the inbox, and report what waits on the user
---

One **patrol pass** over the loop (see the Gated Loop workflow section in the
project's CLAUDE.md → Invocation policy). Read state, act once, report. Follow
these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Gated Loop config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/gated-loop:init`.

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
| `status: ready-for-spec` / `ready-for-dev` | actionable → `/gated-loop:next-stage <n>` |
| `status: in-spec-review` | THREADS-LIST on its spec CR. Any unresolved thread whose last comment is a human answer (does not start with `**[` / `✅`) → actionable → `/gated-loop:spec-answers <n>`. Otherwise → waiting on the user |
| no `status:`, `track: spec` | in flight: CR-FIND for `feat/<n>` and `qa/<n>`. Implementation CR exists with **zero open review threads** AND QA CR exists **and is not a draft** → actionable → `/gated-loop:integrate <n>`. Implementation CR has **open review threads** → actionable → **address-review** (below). Otherwise → in progress, not actionable |
| no `status:`, `track: fast` | in flight: its CR has **open review threads** → actionable → **address-review**; review-clean → LABEL-ADD `status: in-user-review` and treat as waiting on the user |
| `status: in-user-review` | waiting on the user |
| `status: blocked` | waiting on the user — never re-invoke anything on it |
| no `track:` label (inbox) | actionable → **async intake** (below) — unless its last `**[intake]**` comment is still unanswered (then: waiting on the user) |

## 3. Act — one loop issue per pass, plus the whole inbox
In-loop work: pick the actionable issue **closest to done** — priority:
`/gated-loop:integrate` > address-review > `/gated-loop:spec-answers` >
`/gated-loop:next-stage` (`ready-for-dev`) > `/gated-loop:next-stage`
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
For an open issue with no `track:` label:
1. Lock: LABEL-ADD `status: processing`.
2. **Dispatch the `product` agent in async mode** with
   `${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md`, the issue body, and all
   comments — the clarification thinking is the sub-agent's, never patrol's
   own. Per the brief's async contract it returns one batch of questions or
   the final proposal; patrol executes the matching forge op:
   - **Questions returned** → ISSUE-COMMENT the batch verbatim as **one
     comment**, prefixed `**[intake]**` — every open question in a single
     pass, so a once-a-day scan still converges.
   - **Proposal returned** → ISSUE-COMMENT it, prefixed
     `**[intake] · proposal**`, ending: "Reply `approve` to file it like this,
     or correct anything first."
   - **The user's last comment is `approve`** (or a correction — re-dispatch
     with it folded in, and treat as approved if they said so) →
     ISSUE-EDIT-BODY to the proposal's story template (user story / acceptance
     criteria / context), LABEL-ADD the confirmed `track:` label. The issue is
     now at (1a); the gate label is the user's.
3. Clear the lock. Never apply a gate label. Failures follow the STOP protocol.

## 4. Report
A short table: issue · state · action taken this pass, or what it waits on and
who. End with the user's queue: what (if anything) needs them — answer threads,
answer intake questions, `approve` a proposal, apply a gate label, or review &
merge — with links.

## 5. Notification (optional)
If a messaging channel (e.g. Telegram) is connected and an issue **newly**
entered a waiting-on-you state this pass, send a one-line notification with
the link. If no channel is configured, skip silently.

Hard rules: never apply a gate label; never run intake for the user beyond the
protocol above; anything unexpected (failed command, merge conflict, illegal
state) → stop and report, never improvise.
