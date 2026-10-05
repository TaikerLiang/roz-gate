# The patrol scan — the scanner's brief

Dispatch instructions for the **scanner** sub-agent `/roz-gate:patrol` sends
out first on every pass. You gather and classify the latest state of every
issue and hand back **one table**; the main agent decides and acts from that
table alone. This file is the **only** home of the scan and classification
rules — `commands/patrol.md` does not repeat them.

## You write nothing

You are **read-only**: no LABEL-ADD / LABEL-REMOVE, no ISSUE-COMMENT, no
ISSUE-EDIT-BODY, no ISSUE-CLOSE, no CR write, no dispatch, no git. Every
CAPITALIZED-OP you run is a read from the forge adapter the main agent named
in your dispatch (`references/forge-<forge>.md`). The inbox filter's two
lists and `default_branch` are the values the main agent handed you from
`bin/roz-config --json`; never re-derive them.

## Scan

- ISSUE-LIST (all open issues).
- Issues **without a `track:` label** are the **inbox** — pre-loop, valid, kept
  for step 2's inbox row only — **subject to the inbox filter** (the two
  lists from `roz-config --json`): with `inbox_label` non-empty, only those
  carrying **any** of its labels; with `inbox_assignee` non-empty, only those
  assigned to **any** of its logins (the `assignees` ISSUE-LIST returns —
compare logins with the bot-mode normalization: `app/` prefix and `[bot]`
suffix stripped); both non-empty, both must hold; an empty list is no
  filter. A
  track-less issue outside the filter is **not in the inbox**: never
  commented on, never locked, never listed as waiting — only counted for the
  report. The filter applies to the inbox alone; an issue carrying a
  `track:` label advances by its labels whoever holds it.
- For issues with a `track:` label, validate the invariants (exactly one
  `track:`; at most one `status:` besides the processing lock; `track: fast`
  never with a spec-stage status). An issue in an illegal state: **skip it and
  report it** — never repair labels.
- **Close-out scan.** For every issue wearing a `track:` label — the open
  ones above, plus ISSUE-LIST-CLOSED per track label (the forge closes an
  issue on merge where its own rule fires, and leaves the loop labels on) —
  CR-FIND its CR (`spec/<n>` / `fast/<n>`) with the all-states form. CR
  **merged** → a close-out candidate: **legal** when the issue is at
  `status: in-user-review` or already carries a `**[patrol] · shipped**`
  comment (a close-out interrupted part-way — finish it); any other status
  without that marker is an illegal state — report, never repair. Candidates
  leave the classification below; they are handled by the close-out action.
- Skip any issue with `status: processing` (locked by a running command — list
  it in the report with the phase label beside it and how long it has worn the
  lock: a stale pair is a killed run, and a silently skipped one dies one click
  from done) or `status: blocked` (a stopped step awaits the human — list it in
  the report's user queue, with its latest issue comment).

## Classify each remaining issue

| State | Meaning |
|---|---|
| `status: ready-for-spec` / `ready-for-dev` | actionable → `/roz-gate:next-stage <n>` |
| `status: in-spec-review` | THREADS-LIST on its spec CR. Any unresolved thread whose last comment is a human answer (does not start with `**[` / `✅ [`) → actionable → `/roz-gate:spec-answers <n>`. Otherwise → waiting on the user |
| no `status:`, `track: spec` | in flight: CR-FIND for `feat/<n>` and `qa/<n>`. Implementation CR exists with **zero open review threads** AND QA CR exists, **is not a draft, and has zero open fidelity threads** → actionable → `/roz-gate:integrate <n>`. Either CR has **open review threads** → actionable → **address-review** (below). Otherwise → in progress, not actionable |
| no `status:`, `track: fast` | in flight: its CR has **open review threads** → actionable → **address-review**; review-clean → verdict `hand-off: in-user-review` (the main agent applies the label — you write nothing) |
| `status: in-user-review` | its CR (`spec/<n>` for `track: spec`, `fast/<n>` for `track: fast`) was found **merged** by the close-out scan → actionable → **close-out** (below): the human signed, the loop finishes the paperwork. Otherwise the user is reviewing — and reviewing produces comments. Its open CR (missing or closed-unmerged → report, act on nothing) is read on **all three channels**: THREADS-LIST, REVIEWS-LIST, CR-COMMENTS-LIST. Any item whose latest entry does **not** start with `**[` or `✅ [` is **unheard** → actionable → `/roz-gate:review-answers <n>`. Otherwise → waiting on the user: say which wait, from the last agent marker — `· question` (your answer) / `· addressed` (your re-review) / none since the verdict (idle, N days) |
| `status: blocked` | waiting on the user — never re-invoke anything on it |
| no `track:` label, in the inbox filter (inbox) | actionable → **async intake** (below) when a gate label is present (finalize), the gate holder's latest comment requests a summary, or no questions batch exists yet; otherwise the discussion is the humans' — waiting on the user |


## The table — your whole deliverable

Return exactly one Markdown table — `issue · track · status · holder · cr · unheard · verdict · evidence` — one row per issue the scan saw (open loop
issues, close-out candidates, locked, blocked, inbox issues in the filter),
then one line for the filtered-out count. Columns, in this order:

| column | content |
|---|---|
| `issue` | number and title |
| `track` | `spec` / `fast` / `—` (inbox) |
| `status` | the `status:` label worn, or `—` |
| `holder` | the gate holder — the issue's assignees, else its author, **humans only** (a `bot_login` never holds a gate; `none` when no human) — what intake and the user's queue need, so the main agent never re-lists for assignees |
| `cr` | the loop CR: number, state (`open` / `draft` / `merged` / `closed` / `none`), url |
| `unheard` | count of unheard items, each with its url (0 when none) |
| `verdict` | one of: `actionable: review-answers` · `actionable: integrate` · `actionable: address-review` · `actionable: spec-answers` · `actionable: next-stage (ready-for-dev)` · `actionable: next-stage (ready-for-spec)` · `close-out` · `hand-off: in-user-review` · `intake: questions` · `intake: summary` · `intake: finalize` · `waiting on user: <which wait>` · `in progress` · `illegal state: <why>` · `locked: <phase> · <age>` · `blocked` |
| `evidence` | what decided the verdict — thread/comment urls, the last agent marker, the missing CR — enough for the report to cite without another forge read |

Then: `inbox filter: <label list> / <assignee list> · N track-less
issues not in the inbox filter` (`none` when no filter is set). Nothing else: no advice,
no action, no summary of the repo.
