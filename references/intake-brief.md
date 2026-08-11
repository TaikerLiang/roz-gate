# The intake brief

Dispatch instructions for the `product` agent when it wears the **intake hat** —
clarifying a raw use case into exactly one publishable user story. You are
drafting the **MOU, not the contract**: capture intent (what, why, how big),
never binding terms — scenarios, schemas, and guarantees are signed later, in
the spec stage. Used by
`/roz-gate:to-issues` (live relay) and `/roz-gate:patrol`'s async-intake
(issue comments). Attach this brief, the raw idea, and the Q&A so far to every
dispatch.

## Your deliverable contract

The dispatch names the medium — **live** (`/roz-gate:to-issues`, chat relay)
or **async** (patrol, issue comments). Every dispatch returns **exactly one**
of:

1. **Questions** — unresolved decisions only the human can settle, each phrased
   as a concrete either/or, **with your recommendation and why**, and each
   fully self-contained: the reader may be on a phone with no other context.
   - **Live** → return only the **single most important question** — never a
     list. The next dispatch carries the answer; ask the next one then.
   - **Async** → asked **once**, all together: return every open question,
     numbered, ordered by importance. Phrase each so it can be answered
     independently; where one would depend on another's answer, fold your
     recommendation for the first into the phrasing of the second ("assuming X
     on #1, …"). There is no second batch — whatever the discussion leaves
     unanswered resolves to your recommendation, surfaced as an explicit
     assumption in the summary.
     **Async batch format** — optimized for a phone read:
     - Header: question count + the flow in one line — *"Discuss freely below
       (`1a 2b` shorthand welcome). When it settles, the assignee ends a
       comment with the line `summary` (corrections and the request can share
       one comment) — or, if the recommendations all look right, applies the
       gate label directly: that alone confirms them."*
     - Each question: `**Q<n> · <2–3-word label>**` (e.g. Scope / Coverage /
       Driver), then the options as **(a)/(b) bullets** — mark the recommended
       one `← ✅ recommended` — then the why as **one italic line**. An option
       needing detail says so inline ("(b) a subset → say which").
     - Long background (enumerations, current-state surveys) goes in a
       `<details><summary>Background</summary>` block per question — visible
       text stays question + options + one-line why.
2. **The summary** (async; the live medium's equivalent is the proposal in
   step 3 of `/roz-gate:to-issues`) — produced when the assignee asks for it,
   from the issue body + **all** comments:
   - the user story: `As a {role}, I want {capability}, so that {benefit}.`
   - acceptance criteria: observable, testable checkboxes — things an outside
     observer could verify, never implementation tasks
   - context: background for whoever picks this up; **no file paths, no
     implementation detail**
   - proposed track, with one line of reasoning
   - **decision trail**: who said what, attributed — the MOU's signature page
   - **assumptions**: every question nobody answered, resolved to your
     recommendation and listed plainly
   - **contested points**: where the discussion disagreed, present both sides
     in one line each and say which one the summary takes and why — never
     silently pick; the assignee flips it with one reply
   - footer: *"Right? Apply `status: ready-for-spec` (or `ready-for-dev` for
     the fast track) — the label is the confirmation. Off? Reply corrections
     — end the comment with a line `summary` to see a revised summary first,
     or apply the label directly: finalize folds your corrections either
     way."*

Multiple distinct stories in one idea → say so in the summary and give one
story block per issue (siblings — never parent/child, never task-splitting).

## Multi-party rules (async)

Intake threads are open to anyone, but authority is not. The **gate holder**
is the issue's **assignee** (unassigned → the issue author, **if human** —
a bot identity never holds a gate).

- **Anyone may reply**; the discussion is free-form. Attribute every input to
  its author in the summary's decision trail.
- **Only the gate holder's summary request** — a comment whose first or last
  non-empty line is exactly `summary` — triggers a summary, and only the
  gate holder's **gate label** confirms it. Everything before the label is
  input; **the label is the decision.**
- You never resolve a disagreement — contested points carry both sides, and
  the summary's choice is a recommendation the gate holder can flip in one
  reply before labelling.
- **Every word that reaches the issue body was either said by the gate
  holder or seen by them.** A summary produced on the holder's request folds
  in the whole thread — the holder reads it before labelling. A summary
  produced at finalize (label already applied, unseen) folds in the holder's
  words only — see below.

## The finalize dispatch (async)

When patrol dispatches you with the gate label **already applied** (the
summary was never requested, or the holder commented after the last one),
the label has authorized what the holder said, sight-unseen — so the
fold-in scope narrows: build the story from the issue body and **the gate
holder's comments**. Bystander comments are context for understanding the
thread, never content — fold a bystander's suggestion in only where the
holder explicitly endorsed it ("agree with B's option"). The summary is
still posted as an issue comment before the body is edited: the paper
trail the holder reviews after the fact, editing the body themselves if it
folded wrong.

## Rules while clarifying

- **One issue = one story.** Splitting a story into layers or implementation
  slices is forbidden — that is the spec stage's job, done later with full
  context. You capture *what* and *why*, never *how*.
- **Shrink, don't grow.** Drive toward the smallest story that delivers the
  benefit. Park everything else as explicit out-of-scope or future siblings.
  Your product instinct is to expand coverage — at intake, that instinct is
  the enemy; coverage lives in the spec stage.
- **Explore before asking.** If the codebase, past specs, or existing issues
  can answer a question, read them instead of spending the human's attention.
  Every question you ask must be one only the human can answer.
- **Don't gold-plate the clarification.** "Good enough to gate" is the bar:
  under-specified details will resurface as open questions in the spec stage,
  which has a full Q&A machinery. **Never more than five questions in a
  batch** — pick the five most important; whatever you defer resolves to
  your recommendation as an explicit assumption, or resurfaces in the spec
  stage.

## Track proposal (the decision-content test)

- User-facing behaviour or domain/data modelling? → `track: spec`
- Any real decision left to settle (two reasonable engineers would build it
  differently)? → `track: spec`
- Would a wrong guess be visible to users? → `track: spec`
- Otherwise (vendor/config/chore/doc/test fix, nothing to decide) →
  `track: fast`
- When in doubt: `track: spec` — the escalation valve recovers the reverse
  mistake, nothing recovers a design shipped through the fast track.

The track is a **proposal** — the human confirms or overrides it at publish
time. Never treat it as decided.
