---
title: Joining a Roz Gate thread
---

# Joining a Roz Gate thread — the 60-second guide

Someone's repository runs an AI-driven workflow where agents clarify ideas,
write specs, build and test — and stop at explicit gates for humans. You do
not need to install anything or learn a tool. Everything happens in ordinary
issue and pull-request comments, and you only ever need **four moves**.

## 1. Answer the questions

An agent posts one batch of numbered questions (it starts with
`**[intake]**`), each with (a)/(b) options and a marked recommendation.
Reply free-form — `1a 2b` shorthand is welcome, so is disagreeing in prose.
**Anyone may weigh in**; it is a normal discussion thread. The batch is asked
once: whatever stays unanswered resolves to its recommendation and is listed
as an assumption.

## 2. Say `summary` (gate holders only)

The **gate holder** is the issue's assignee (unassigned → the author). When
the discussion feels settled — or immediately, if the recommendations look
right — end a comment with the single line:

```
summary
```

The agent condenses the whole thread into one summary: the user story,
acceptance criteria, who said what, every unanswered question resolved to its
recommendation and listed as an assumption, and every disagreement shown with
both sides. Corrections? Put them in the same comment, above the `summary`
line — the agent re-reads and posts a revised summary.

## 3. Apply the label — that IS the confirmation

Summary looks right? Apply the gate label:

- `status: ready-for-spec` — worth a debated spec first
- `status: ready-for-dev` — small and clear, build it directly

There is no approve keyword — **the label does the signing**, and only the
gate holder's hands ever touch these two labels. Something off? Reply
corrections — end with `summary` to re-read first, or label directly: the
final story folds in **your** words only.

## 4. The review conversation

When the work has passed its verdict, the issue carries
`status: in-user-review` and the agent hosts your review on the spec pull
request. Comment there like any code review: the agent answers from what the
artifacts already say, with links, and reads any change back to you in one
line before making it. **Nothing is built without your word; silence is never
consent.** Your three options: **merge it, change it, or send it back** to
the idea stage — starting over is a normal outcome, not a failure. The issue
leaves review when you merge.

## When the loop stops

An automated step that hits something it will not decide leaves the issue
with `status: blocked` and one comment titled `**[<command>] · blocked**`:
what happened and a recommended next step, evidence folded below. Its last
line before the evidence tells you the whole move — **To resume:** which
label to clear, which to apply, and where your answer goes. Do those and the
step re-runs; nothing else is needed.

## On spec pull requests

Agents post their open questions as review threads (each starts with `**[`).
Reply inside the thread like any code review — the agents fold answers into
the spec and resolve the threads. A top-level comment on the pull request is
read too, and a thread **you** open is an amendment request: the spec is
widened to cover it.

---

*Building your own agent for one of these loops? See
[protocol.md](protocol.md) — **protocol v1**: labels, markers, and the rules
that make agents interoperate.*
