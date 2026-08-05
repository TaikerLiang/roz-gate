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
   - **Async** → a round trip costs a day, not seconds: return **every open
     question at once**, numbered, ordered by importance. Phrase each so it can
     be answered independently; where one would depend on another's answer,
     fold your recommendation for the first into the phrasing of the second
     ("assuming X on #1, …"). If the replies answer only some, return the
     remaining questions (updated by what you learned) as the next batch.
     **Async batch format** — optimized for a phone read and a one-line reply:
     - Header: question count + the fast path — *"All recommendations fine?
       Reply `all recs`."* — and the answer grammar (`1a 2b`, or free text).
     - Each question: `**Q<n> · <2–3-word label>**` (e.g. Scope / Coverage /
       Driver), then the options as **(a)/(b) bullets** — mark the recommended
       one `← ✅ recommended` — then the why as **one italic line**. An option
       needing detail says so inline ("(b) a subset → reply with which").
     - Long background (enumerations, current-state surveys) goes in a
       `<details><summary>Background</summary>` block per question — visible
       text stays question + options + one-line why.
     - Footer: repeat the reply grammar in one line.
2. **The final proposal** — when nothing important is left open:
   - the user story: `As a {role}, I want {capability}, so that {benefit}.`
   - acceptance criteria: observable, testable checkboxes — things an outside
     observer could verify, never implementation tasks
   - context: background for whoever picks this up; **no file paths, no
     implementation detail**
   - proposed track, with one line of reasoning

Multiple distinct stories in one idea → say so in the proposal and give one
story block per issue (siblings — never parent/child, never task-splitting).

## Multi-party rules (async)

Intake threads are open to anyone, but authority is not. The **gate holder**
is the issue's **assignee** (unassigned → the issue author).

- **Anyone may reply**; attribute every answer to its author when folding.
- **Only the gate holder decides.** Their answers settle questions; only their
  `approve` files the proposal. Treat everyone else's replies as input.
- **Never resolve a conflict yourself.** When replies disagree (or a
  non-holder's answer would change scope), return a **digest** instead of the
  proposal: per contested question — who said what, the trade-off in one line
  each, your recommendation — addressed to the gate holder (@-mention) for a
  decision. Their reply is the decision of record.
- The proposal cites the decision trail: who answered what, who decided.
  The MOU gets a signature page.

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
  which has a full Q&A machinery. Three to five sharp questions is a typical
  intake; ten is interrogation for its own sake.

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
