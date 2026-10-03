---
name: plan-issue
description: Turn one roz-gate issue into an implementation plan for THIS repository — grill first (never guess), write the rulings back to the issue, then a plan in five sections (main, eval, doc, release, done-when). Use when the user pastes an issue number or link with notes, or says /plan-issue.
argument-hint: "<issue number or URL> [notes]"
---

# /plan-issue — one issue, one plan, nothing guessed

This repository does **not** run its own loop: issues are the backlog, work
ships as one PR per issue straight to `main`, and the maintainer's PR
review is the gate. This skill is how an issue becomes that PR's plan.
The plan is a deliverable, not a start signal — **implementation begins
only when the maintainer says so** ("開工" / "go").

## 0. Read before asking

- `gh issue view <n> --json title,body,comments,labels` — body and every
  comment; earlier rulings may already be recorded there.
- The code the issue touches: `commands/`, `references/`, `hooks/`,
  `evals/` as relevant. `evals/LEDGER.md` for cases that already cover the
  area. `git log --oneline -20 -- <path>` for how it got this way.
- `CHANGELOG.md` for the release that introduced the rule in question —
  "why does this exist" lives there.

A question the codebase answers is never asked.

## 1. Grill — the `grill-me` skill, one question at a time

Invoke the `grill-me` skill via the Skill tool if available; otherwise
apply its pattern — one sharp either/or question at a time, each with a
recommendation (the fallback `agents/em.md` uses; the skill is the
maintainer's, not this repository's). Every question carries a
recommended answer. Walk the
decision tree until every branch is settled: scope, the behaviour that
changes for a target repo, what is explicitly out of scope, who holds
each decision (human vs agent), and which tier proves it (step 3).

Stop grilling when a further question would not change the plan.

## 2. Write the rulings back to the issue

One `gh issue comment` titled **Scope (rulings from <name>, <date>)**:
each ruling as a bullet, in the words agreed, plus the explicit
not-in-scope list. The plan is written from this comment, never from
memory; a later session must be able to rebuild the plan from the issue
alone.

## 3. The plan — post it as a second issue comment

Five sections, in this order. Empty sections are stated as empty, never
omitted.

### main

- What changes, file by file (`commands/*.md`, `references/*.md`,
  `hooks/*.py`, `templates/`), each line traceable to a ruling.
- **Tier decision** (`evals/CONTRIBUTING.md` § Pick the tier): a rule
  decidable from one tool call is a **hook**; provable by reading the
  source is **lint**; about what a model does with the prose is
  **replay**; a judgment of meaning is **judgment**. A rule that can be a
  hook should be one.
- **Out of scope** — the list from step 2, verbatim.

### eval

- Which existing cases **cannot** see this defect, and why (e.g. every
  `next-stage` seed carried `default_branch: main`).
- New or changed cases by ID (`LEDGER.md` family rules; numbers never
  reused), each with its ledger text drafted here.
- Every new replay case ships `redproof.py`; every hook change ships
  `hooks/tests/` cases; every lint case is red-proofed by mutation (old →
  new, both directions) and the mutation recorded in the commit message.
- Whether a **baseline SUT run** is needed, by tier: a replay case —
  `python3 evals/replay/run_replay.py --sut opus --k 5 <ID>`; a judgment
  fixture — `python3 evals/judgment/run_judgment.py --redproof` first
  (green under the current judge fingerprint), then `--sut opus --k 2
  <F-id>` (`evals/judgment/README.md` § Running). That spends quota: name
  it as a decision for the maintainer, never start it in the plan.
- **Order**: the checker (and its red-proof) is committed in a **distinct
  commit before any recorded run** — the blindness commit
  (`evals/CONTRIBUTING.md` § Before the first recorded run). A baseline
  run from an uncommitted working tree loses the history-based proof that
  the checker was not written from observed output; the plan states the
  commit as the baseline's prerequisite.
- Forge-stub routes the case needs that the stub lacks (an UNKNOWN
  invalidates the iteration).

### doc

Scan **all** of these, every time — list each with "changed" or
"checked, no change":

| surface | what to look for |
|---|---|
| `README.md` | the section that states the rule; the config block; the command table |
| `docs/index.html` | stage cards, label cards, wizard, simulator; the inlined `images/loop-stage-map.svg` (lint L1 holds it byte-identical) |
| `docs/onboarding.html` | the config builder (keys, presets, hints), the first-issue walkthrough, the stop shapes |
| `docs/learn/quiz.json` | any question whose answer the change flips |
| `references/workflow.md` | the stage prose and the label state machine |
| `commands/*.md` the change touches | the executable prose — every statement of the rule, not only the first |
| `references/forge-github.md` / `forge-gitlab.md` | an op the new prose calls must exist in **both** |
| `hooks/README.md` | rule table, if a hook changed |
| `evals/LEDGER.md`, `evals/CONTRIBUTING.md`, `evals/README.md` | new case rows; the case count |
| `docs/releasing.md` | only if the release procedure itself changes |

Then one grep across `README.md commands references templates docs` for
vocabulary the change retires (the way `approve` outlived 1.4.0 in the
idea template). `CHANGELOG.md` is never edited by hand.

### release

- **Version**: minor or patch, by `docs/releasing.md` § Minor or patch,
  with the one-sentence reason. Any change under `agents commands
  references templates` needs a bump (pre-push refuses otherwise).
- **Release-note block**, written now in `docs/releasing.md`'s layout
  (runtime-impact line first, then Behavior / Evals / Hooks / Tooling /
  Docs bullets with bold subjects, code formatting for every path and
  placeholder). It goes into the PR body under `## Release note`, so the
  release is assembled from PR bodies, never reconstructed.
- **Verification line** the PR must carry: hook tests, lint, red-proofs,
  naming, ruff, `judgment --check` — counts on the final commit.
- **PR shape**: one PR, base `main`, never stacked on another open PR
  (#44 merged into its base 12 s after the base merged and needed a
  carry-over). Expect one Codex review round; every finding is answered
  — fixed with a 👍, or refuted in a reply.

### done-when

The evidence that closes the issue, as checks a reader can run: which
lint case is green, which red-proof went red-then-green, which replay
case has a baseline and what it measured, which page shows the new text.
Without this section "done" is only a claim.

## 4. Stop

Post the plan, link it, and stop. Do not branch, do not edit, do not
start the baseline. On the go signal: worktree under the scratchpad,
never the main checkout; one branch per issue; the `done-when` list is
the PR's checklist.
