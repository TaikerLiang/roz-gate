---
description: Live intake — clarify a use case into one-issue-one-story tracker issues; the product agent (under the intake brief) asks the questions, the main agent only relays and publishes
argument-hint: "[use case text or issue reference]"
---

Turn a use case into tracker issues, one per user story — stage (1) of the
Gated Loop. The main agent stays a thin **relay**: the clarification thinking
happens in a dispatched `product` agent, so the orchestrator's context stays
lean. Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Gated Loop config` block in the project's CLAUDE.md, then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the CAPITALIZED-OPs.
Missing config → stop; tell the user to run `/gated-loop:init`. Also read
`${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md` — it is the dispatch brief
for step 2.

## 1. Gather the use case

From `$ARGUMENTS` and/or the conversation. If the user passed an issue
reference, ISSUE-VIEW it and treat its body + comments as the raw idea.

## 2. The relay loop

Dispatch the **`product`** agent with: the intake brief, the raw idea, and the
full Q&A so far. Per the brief's contract it returns **either** one question
(with a recommendation) **or** the final proposal.

- **Question** → relay it to the user **verbatim** — do not answer it, soften
  it, or batch it with your own commentary. When the user answers, re-dispatch
  (continue the same agent when possible; otherwise include the accumulated
  Q&A) and repeat.
- **Proposal** → go to step 3.

The main agent adds no clarification content of its own. If you catch yourself
drafting acceptance criteria or debating scope inline, stop — that thinking
belongs in the dispatched agent.

## 3. Confirm with the user

Present each proposed issue exactly as the agent returned it: **title** +
**user story** + **acceptance criteria** + **proposed track**. Ask:
- Is this the right story — wrongly split or merged anything?
- Are the acceptance criteria complete and observable?
- Is the track right?

Corrections → re-dispatch the `product` agent with the correction folded in;
iterate until the user approves.

## 4. Publish

For each approved story: ISSUE-CREATE with the story template body (user story
/ acceptance criteria / context) and the **confirmed** `track:` label. Several
stories → sibling issues, no parent/child.

## 5. Report

Issue URL(s) + proposed next step. **The gate label is the user's**: remind
them to apply `status: ready-for-spec` (or `ready-for-dev` for fast track)
when they want the loop to pick it up. This command never applies a gate
label.

Tip worth repeating to the user once: away from the keyboard, they can skip
this command entirely — file a raw, label-less issue from the forge's mobile
app and patrol's async intake ((1b)) will run this same clarification in the
issue comments.
