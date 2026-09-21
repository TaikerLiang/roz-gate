# Changelog

Generated from the GitHub releases (`gh release list`, `gh release view <tag>`), newest first, one entry per tag with its title and body verbatim. **The release note is canonical**; this file is a convenience copy — regenerate it, never edit it by hand. It exists because "why does this rule exist" is answered by the release that introduced it better than by any other document here.

## v1.16.2 — rule E: echo/printf only in command position — 2026-09-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.2>

Closes the post-merge codex finding on 1.16.1: echo/printf are recognized only as commands (segment start or after && || ; | ( $( {, optional env assignments), so a real read such as grep echo src/app.txt is denied again while string mentions stay allowed. Hook tests 99/99, lint 70/70.

## v1.16.1 — rule E: mentions in shell strings; D2 counts denied attempts — 2026-09-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.1>

guard-blind rule E no longer denies src/ mentioned inside echo/printf operands or # comments; the D2 checker pairs tool calls with results so a hook-denied attempt is counted as attempts-denied, not a breach; forge stub gains issue-view (REST) and review-comment-view routes. Known follow-up: echo/printf matched as words anywhere in a segment can blank a real read (codex, fixed in 1.16.2). Hook tests 92/92, lint 64/64.

## v1.16.0 — fidelity review is blind by mechanism (rule E) — 2026-09-17

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.0>

guard-blind rule E: while a fidelity dispatch is active (marker in .git/roz-gate/), Read/Glob/Grep on src/ and git operations on feat/<n> are denied with the remedy in the message; exclusion forms stay legal. Promoted from the opus baseline sweep (D2 4/5: a QA child ran cat src/app.txt under the dispatch). Rules enforced mechanically: 4 → 5. Hook tests 89/89, lint 59/59.

## v1.15.0 — open questions have one home (rule D) — 2026-09-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.15.0>

guard-gate rule D denies a git commit while any specs technical-spec.md carries an open-questions section; the lint tier backstops it at push. Promoted from the opus baseline sweep, where E2 measured 0/5 after the A6 prose was made explicit — the model copied and threaded the question every time and deleted the source section never. Rules enforced mechanically: 3 → 4. Also: review-comments-list read route in the forge stub. Hook tests 72/72, lint 47/47.

## v1.14.2 — relocate means move; sweep-autopsy instrument fixes — 2026-09-15

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.2>

Behavior: next-stage A6 now states that a question swept from another spec doc is MOVED into spec.md's Open Questions — deleted from the source, at most a one-line Q-ID pointer remains (ruling from the first opus baseline sweep: E2 5/5 and F3 2/5 copied instead of moving). Instrument: D2 exclusion syntax is not a touch; F2 counts answers, permits readbacks; C5 fixture carries a real test suite committed on main; forge stub gains pr-diff value flags and a comment-by-id read route. Lint 39/39, hooks 60/60.

## v1.14.1 — rule C per-segment classification — 2026-09-06

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.1>

guard-gate rule C now classifies per shell segment (tokenizer-emitted operators, glued forms included), fixing the compound-command -F false positive found while dogfooding. 60/60 hook tests. Also merged: the replay tier (evals/replay — 18 cases, stateful forge stub, multi-model runner; eval infrastructure, no behavior change).

## v1.14.0 — the quote-open guard (rule C) — 2026-08-23

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.0>

The B4 runaway — patrol reading a quote-opening agent comment as a human answer and replying to itself once per pass — now has mechanical enforcement. Guard-gate rule C denies any forge comment write whose body opens with a quote block (including after leading blank lines or whitespace) while carrying a roz-gate marker (`**[` / `✅ [`) anywhere. Static, no forge API call; the deny message states the remedy: marker on line one, quote below, or hand the text back to the human.

Scope is deliberate and honest: comment-shaped writes only (a CR or issue *body* may legitimately open by quoting); the marker condition keeps unmarked writes untouched; `--body-file` bodies are read back or heredoc-parsed and judged — the blocking review finding, since the long multi-line readback is exactly a `--body-file` body — and a body the guard cannot see fails closed only when the command itself shows a marker. Command-substitution bodies are structurally invisible to any static hook and stay on the prose rule, stated in the docstring rather than implied covered.

54/54 hook tests (15 new: 8 deny paths, 5 allow paths including the prescribed remedy, a no-API assertion, a scoping control), red-proofed by three mutations each caught by exactly its own test.

## v1.13.0 — the eval ledger's lint tier — 2026-08-23

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.13.0>

Ten static checks — the lint tier of the eval ledger — now gate every push: `evals/lint/run-lint.sh` (39 checks) plus the hook unit tests run from `.githooks/pre-push`, with `.github/workflows/checks.yml` as the CI backstop for `--no-verify`.

Every case guards failure mode 2: the rule itself is broken, so every stage faithfully executes it and reports green. Runtime-check cases get two layers — pattern proof against fixtures, and byte-for-byte source conformance — because the checks under test are greps a model executes from prose.

Building the suite found two shipped defects whose ledger annotations claimed them fixed:

- **B1** — the unverified-claim check still grepped only the bare literal `(unverified)`; 1.12.0 fixed the two-axis writing convention but never widened the pattern, so `(from Q4, unverified)` — the exact channel the false claim entered through — passed the check. Now `(^|[(,])[[:space:]]*unverified`, catching the merged and the wrap-split compound.
- **C6** — 1.11.0 documented the all-states CR query in both forge adapters, but no command ever invoked it: spec-answers §7's post-integration branch, which must tell *merged* from *absent*, was unreachable, and a shipped issue would have been sent back through implementation. The branch point now requires CR-FIND's all-states form.

In both, the fix landed where it was written and never where it was read — which is why conformance checks anchor on the site that reads the rule.

`evals/README.md` states what a green run proves and what it does not (every case derives from one repository, one operator, one atypical issue), and sets the red-proof requirement: a new case counts only once it has been demonstrated to fail legibly.

## v1.12.0 — the spec learns what kind of sentence it holds — 2026-08-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.12.0>

A field review of a full artifact set (spec.md / technical-spec.md / test-spec.md, lived-in end to end) surfaced three defects in how the spec stage writes. All three shared a shape worth naming: each was reported at the stage where it *appeared*, one stage narrower than where the failure class *lives*. The release fixes the classes.

### Rulings are not claims

Two kinds of sentence shared the spec's typography and its authority: rulings ("the role value is ignored" — true because the holder said so) and empirical claims ("neither run fails" — an assertion about reality, which was false, and a test was derived from it). The separator is now the **jurisdiction test**: *can the implementer be ordered to make this sentence true?* No → it describes pre-existing reality, and writing it down does not make it true.

Empirical claims carry evidence tags — `(measured, <date>, <scope>)` (the date says when; the scope is the falsifier), `(unverified)`, or the demotion `(assumed-empirical: <named risk>)` — enforced in three layers: the gate kit's attention list, the spec-answers promote report, and a **Path B entry STOP**: an `(unverified)` claim cannot be signed. The stop is coverage, not caution — a claim false only under conditions the acceptance run never produces goes green through validation, fidelity review, and the integration verdict, because *a faithful transcription of a falsehood satisfies fidelity*. Nothing downstream of the spec stage can reach that branch.

The holder's own answers are covered too: empirical content inside a ruling folds with both tags — **the holder is not an oracle about reality**, and the original false claim entered through exactly that channel.

### Questions have one home, and answers land where they bind

`spec.md`'s `## Open Questions` is the single collection point for every seat's questions — a question written into any other document has no route to the gate holder (the field case: four implementer questions stranded in the contract, one of them a timeout trap, saved by hand). Seats return their batches; the main agent appends and numbers them; the A6 sweep relocates strays. And folds now land in **the document the raising seat owns** — an implementer question's answer amends the contract QA tests against, or the pipe is one-way: question reaches the holder, answer never reaches the tests.

The mid-flight ambiguity route now covers every seat that can hit one: QA (as before), **the implementer at (3)** — stop and report, never decide unilaterally in code — and (5) review findings that are really contract ambiguities.

### The port declares what it can show, and the holder countersigns

When the implementer designs the test port it now walks every scenario once — observable, observable via which control point, or a limitation — as a table in the contract. A **limitation is a verdict exemption, and the implementer never grants its own**: every one surfaces on the spec-gate attention list for the holder to sign. QA still walks independently at (4); every mismatch, both directions, is a mandatory finding, and the fidelity review audits the reconciliation.

### Smaller

- **Resolved-question entries trim** to ruling + attribution + one-sentence rationale + fold pointers — the spec reads as current truth; the argument lives in the decision ledger and the thread.
- Scenario text is Given/When/Then only; guidance addressed to another seat is a rule, never a scenario.
- `technical-spec.md` gains `C<k>` clause numbering — anchor-free contract prose cannot be cited, audited, or kept current.
- Tag checks match opening tokens only (tags with free text wrap; a wrapped tag is present, never absent).
- B6's wording now matches patrol: a fresh implementation-blind reviewer resolves fidelity threads — the audited party never closes the audit's findings.

### Upgrading

No re-init needed — the project workflow template is unchanged.

## v1.11.0 — the review conversation — 2026-08-17

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.11.0>

Stage (7) had a reading surface and no hearing surface. `status: in-user-review` was a terminal-wait row in patrol's classification table, so the gate holder's comments on a spec CR were never read — three of them sat for a day. 1.10.0's gate kit made it sharper: a review page that works *generates* comments.

**(7) is now a discussion stage hosted by the main agent.** It answers what the artifacts already say — quoted, with a permalink at a SHA — dispatches a seat when the answer needs specialist judgment, and reads any change back to you in one line before making it. Nothing is built without your word; silence is never consent.

### What's new

- **`/roz-gate:review-answers`** — one turn of the conversation. Ranked above integrate in patrol (the person at the final gate never queues behind machine work); answer-only turns are exempt from the one-issue-per-pass rule, so a multi-day conversation can't starve the loop.
- **Three-channel detection** — inline threads, review summary bodies, and top-level CR comments. `REVIEWS-LIST` and `CR-COMMENTS-LIST` are new adapter ops on both forges: a body-only *changes requested* review used to scan clean, and a reply typed on a phone lands in the channel nobody read.
- **The agent-marker test is now `**[` / `✅ [`** — with the bracket. A human's own `✅ looks good` was the single highest-value message in the channel and the old predicate classified it as an agent comment. The same prefix invariant is the livelock brake: it is what stops the conversation answering itself.
- **Seat-on-edit** — any resolution that would edit a file gets one seat opinion before the readback. The trigger is the act you are about to take, not a judgment about what the comment implied. It is the only mechanism at (7) that puts a failure branch in front of you.
- **A new PreToolUse hook** — acceptance files are not editable on a `spec/*` branch. Branch and path only: no stage detection, no exemption list, so "the main agent is not exempt" is true by construction rather than by prose. At (7) the main agent hosts, authors, commits, runs the verdict and assembles the page you read — it is the one stage with no adversarial second party.
- **The hand-back rule**, named once and cited from both sites: any SHA wearing `in-user-review` has a captured green *full* acceptance and unit run at that SHA, with evidence cards regenerated wholesale. What it licenses is one sentence — *"green against the pre-rework spec, at SHA `<x>`"* — never "verified". A weaker claim needs fewer guards to stay true.
- **Back to intake as a first-class outcome** — strip `track:` and `status:` and the issue is a raw idea again, discussion intact. Redoing work is cheap; re-answering rulings you already made is not, so the decision ledger carries forward as prior answers to confirm.
- **(7) renamed Merge → Review** in the docs (the label is unchanged). "Nothing is left but your review" was never true and is now gone. (7) also has no `blocked` exit — the issue is already at your gate.

### Fixed

`/roz-gate:spec-answers` had no post-integration branch: an issue returning from (7) hit the first-pass path and was told it was "ready for your approval to move to implementation" when implementation was already done. That path becomes primary under this design.

### Upgrading

No re-init needed — the project workflow template is unchanged.

## v1.10.0 — the gate kit: gates a human can actually hold — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.10.0>

The first closed loop's gate holder drowned in R/S/G cross-references. This release gives each spec-track issue a **gate kit**: one comment on the spec CR, edited in place across the issue's life, assembled mechanically (extraction and quotation only — never synthesis) under hard rules: **quote-never-paraphrase, every claim links its line, no conclusions, exhaustive-or-say-so, the kit states its own blind spot, the CR diff stays primary, the top reads in 90 seconds.**

- **Attention list** — a computed **sort, never a filter** (the word "mechanical" never appears): `(assumed)`-provenance rules first (decisions made in your name you never made), then rules whose text changed after your ruling, then coverage gaps, then weak-assertion findings from the fidelity review.
- **Issue-delta instead of a summary** — "you asked for X; the spec adds these N things you didn't ask for and drops this one you did." A summary of the spec, by its authors, structurally can't show that.
- **Decision ledger** — your answer quoted verbatim **next to the fold the spec actually gained**; agent additions marked *interpretation:*. The gap between what you said and what got written is where expensive errors live.
- **Evidence cards** (final gate) — per scenario, four buckets (covered / partial / not covered / cannot-be-covered-black-box), assertion excerpts and **actual observed values from the green run's captured output** — "value not emitted — assertion only" where thin, never the expectation restated as an observation.
- **The since-you-approved diff** — your gate label stamps the spec SHA; the final gate shows exactly what changed since, hunk by hunk, annotated by cause. Approval that can silently expire is the most dangerous property a gate can have — the first closed loop exercised it.

New COMMENT-EDIT forge op (both adapters). Success metric, instrumented from day one: the **artifact-change rate at gates**, not the approval rate — a gate that only ever waves things through is decoration. Prose-only; tests 27/27.

## v1.9.0 — the verdict's source gets an auditor: QA fidelity review — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.9.0>

The integration verdict is the loop's headline claim, and the QA suite is the artifact it's computed from — until now, the loop's only unaudited node. A vacuous suite made a green verdict silently forgeable. New stage **(5q)** closes it.

- **A second, implementation-blind reviewer dispatch** audits the QA suite's fidelity to the spec — run on a `qa/<n>` checkout, so the same branch topology that makes QA blind makes the auditor blind (a fidelity reviewer who has seen the implementation rates tests faithful *because they pass* — the exact bias to remove). Contract: the new `references/fidelity-brief.md`.
- **Four questions**: does each test assert what its scenario says; vacuous assertions (a 12-item static checklist); is `test-spec.md`'s coverage claim honest; and **over-assertion** — a test requiring behaviour no spec text states produces a false RED, which costs the verdict its credibility.
- **Evidence, never a verdict**: every finding carries two verbatim quotations side by side — the spec clause and the assertion excerpt ("S5 says ghosts are logged **by name**; the test asserts `len(skipped) == 2`"). No citations ⇒ QA declines the finding. Plus the origin rule: an expected literal with no origin in spec text was almost certainly read off the implementation.
- **Contract-currency step zero**: amendments agreed in threads but not folded into the contract block the review — a fidelity audit against a stale contract launders the staleness as verified.
- **Wired into the existing machinery**: findings are QA-CR threads; patrol's address-review now drives both CRs (qa addresses, a fresh blind dispatch re-checks); integrate gains the symmetric precondition — both CRs thread-clean before the verdict runs.
- **`test-spec.md` gets a required shape**: the scenario→test map must be derivable from machine-readable trace markers in the test source (config `trace_marker`, or qa declares one) — hand-maintained trace matrices are complete, tidy, and stale.

Prose-only (commands/references/personas); no hook, marker, or label changes. Tests 27/27.

## v1.8.1 — suite layout is the project's call — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.8.1>

The rule "tests are a living, feature-organized suite — never per-issue folders/tags" conflated two things: the invariant and a default. Unbundled:

- **The invariant stays hard**: tests are a *living suite* — maintained and evolving, never write-once per-issue snapshots. Black-box information flow and branch topology are untouched.
- **The layout becomes a project-overridable default**: suite organization is project-layer philosophy, like the test runner or lockfile commands — so it now follows the same pattern they do: an optional config key, `acceptance_layout` (absent = feature-organized, the default; e.g. `one folder per issue, shared fixtures in support/`). QA and the workflow read the project's declared convention — **a project-sanctioned layout is never a violation to flag**.

Born from real usage: the first closed loop shipped a per-issue layout pinned by its technical spec, and the QA seat correctly followed the contract while flagging tension with prose that had no business being hard. Prose-only; tests 27/27.

## v1.8.0 — make the existing loop honest — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.8.0>

First fruits of the first fully-closed spec-track loop (run by a real project): a four-seat evaluation of the resulting proposal package surfaced two defects in shipped commands and two enablers. This release is the "fix and enable" slice; the audit (QA fidelity review) and gate-holder legibility slices follow under separate rulings.

- **The reviewer now receives the claim.** The stage-(5) dispatch attached only the code diff — the spec docs live on the branch the diff excludes, so the independent reviewer was reviewing code against its own inference of intent. It now gets `spec.md` + `technical-spec.md` (fast track: the issue's story + AC).
- **Integration REDs gain the missing third class: the contract itself was false.** "Harness issue" is tightened to failures where the test never reached its assertion; a faithful assertion that reality disproves is a **contract defect** → STOP, amend the contract, QA re-derives. New command law: *an integration RED is never resolved by editing a QA assertion to match observed behaviour* — that would rewrite the verdict into an echo of the implementation.
- **Numbered rules with provenance.** `spec.md` enumerates story-level rules exhaustively (`R<k> · <title>`), each annotated `(from Q<j>)` / `(from AC-<j>)` / `(assumed)` — the human can now see which decisions were made in their name that they never made, and downstream audits get an honest denominator.
- **Titled ID citations.** First mention of any rule/scenario/question ID in a comment, thread, or report carries its title and a definition link — never a bare code. The reader may be on a phone with no lookup table in their head.

Prose-only (commands/references); no hook, marker, or label changes. Tests 27/27.

## v1.7.1 — the README catches up: agent identity and the hook, surfaced — 2026-08-11

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.7.1>

Docs-only patch. v1.7.0's biggest feature was invisible to anyone who didn't read the release notes — and it turned out v1.5.0's enforcement hook had never made the README either.

- **README · Agent identity**: new section — user mode (default, zero setup) vs bot mode (GitHub App / GitLab project access token), why it matters (you can tell who's speaking; the agent's questions actually notify you — posting under your own account suppresses every ping; your credentials stay out of its hands), the `a bot never holds a gate` invariant, and the three config keys with a link to `references/identity-github-app.md`.
- **README · Labels**: the two human-only rules are tool-layer enforced by the bundled PreToolUse hook, fail-closed. *Prompt discipline is the manners; the hook is the law.*
- **Interactive guide**: both additions, bilingual, in the labels section.

No behavior changes; tests 27/27.

## v1.7.0 — agent identity separation: the agent gets its own face — 2026-08-11

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.7.0>

The agent now acts under its **own forge identity** — a GitHub App (`<slug>[bot]`) or a GitLab project access token bot — instead of the human's session. Opt-in via `agent_identity: bot` in the config block; absent keys keep user mode, bit for bit.

**Why it matters**: the human finally gets notified (an agent posting under your own account suppresses every ping — async intake's "from anywhere" promise was half missing); identity becomes author structure instead of text convention; personal tokens stay out of agent hands.

- **Two new invariants**: a bot never holds a gate (bot-created issues are born with a human assignee; bot-authored unassigned issues have no gate holder), and authority checks compare authors, not markers.
- **Hook**: config-driven bot mode — bot logins excluded from gate-holder resolution, and "a summary was already posted" now requires the poster to *be* the bot (a human quoting the marker no longer counts). Login comparison normalizes the `app/` prefix and `[bot]` suffix — the same App surfaces three ways across API paths (live-verified).
- **Adapters**: per-invocation tokens only (never exported), HTTPS push with per-command git author flags, GitLab JSON-body and async-`diff_refs` corrections from the live spike.
- **Setup**: `references/identity-github-app.md` (GitHub App + GitLab project token, human-created — verified on gitlab.com free tier) and `scripts/gh-app-token.sh` (installation-token minting).
- **Intake polish**: question batches hard-capped at 5, and the batch header now says it: recommendations all look right? Apply the gate label directly — that alone confirms them.
- **Init**: creates `acceptance_dir`/`specs_dir` at bootstrap (a configured path must exist from day one).

Test suite: 27 cases (4 new bot-mode). No re-init needed — plugin update is the whole upgrade.

## v1.6.1 — spec open questions adopt the intake batch format — 2026-08-09

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.6.1>

Format-only patch, born from the first real stage-(2) run: the spec CR's question threads were hard to read and answer as single bold paragraphs.

- `spec.md`'s `## Open Questions` items now use the intake batch shape — title line `**[<role>] · Q<k> · <label>**` (with `(story-level)` folded into the title), one-sentence question, (a)/(b) option bullets with `← ✅ recommended`, one italic why.
- A6 posts each item **verbatim** as its inline thread body (single source of truth: A3 defines the shape once); story-level items end with the italic mirror note.
- The `**[` marker that `/roz-gate:spec-answers` relies on is satisfied by the title line by construction — no behavior change, no hook change, no re-init.

## v1.6.0 — one-comment intake convergence: the label folds in the holder's words only — 2026-08-09

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.6.0>

Async intake gets a single authorization invariant: **every word that reaches the issue body was either said by the gate holder or seen by them.**

- **One-comment summary requests**: the trigger is now a comment whose first or last line is exactly `summary` — corrections and the request ride together, no more two-comment dance. Mid-sentence mentions, quoted `> summary` lines, and `Summary:` headings don't trigger; the bare one-word form still works.
- **The gate label folds in the holder's words only**: finalize reuses the latest `**[intake] · summary**` verbatim unless the *holder* commented after it — then it regenerates from the holder's words alone (bystander comments are thread discussion: context, never content, folded in solely through the holder's explicit endorsement). The regenerated summary is posted as a comment before the body edit — the paper trail for after-the-fact review. This closes an authority leak: bystander input can no longer enter the gated body unseen under the holder's label.
- The confident-holder shortcut (label without ever asking for a summary) stays, now with a single meaning: "build the story from everything I said."
- Hook updated in lockstep (`is_summary_request()` line rule); test suite grows to 23 cases.

No re-init needed — plugin update is the whole upgrade.

## v1.5.0 — hook-enforced gates: intake-summary triggers and human-only gate labels — 2026-08-08

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.5.0>

The protocol's two highest-stakes human-only decision points are now enforced at the tool layer by a PreToolUse hook, not just by prompt text:

- **Rule A — intake-summary trigger**: an `**[intake] · summary**` comment posts only when a gate label is present or the gate holder's latest comment is `summary` (with no summary posted since). Anything else is blocked with a message pointing at the protocol.
- **Rule B — gate labels are human-only**: agents can no longer `--add-label` `ready-for-spec` / `ready-for-dev` (removal, list filters, and `label create` are unaffected).

Design: a zero-cost bash prefilter escalates to a python validator only when a guarded pattern appears; forge API failures fail closed with a distinct retry message; no bypass variable — the legitimate unlock is the protocol itself. Covers both `gh` and `glab`. Ships with a 19-case test suite (`hooks/tests/run-tests.sh`).

Enforcement arrives on plugin update — no re-init needed.

## v1.4.0 — three-beat intake: ask once, summarize on demand, the label confirms — 2026-08-06

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.4.0>

## Highlights

### 🧹 Async intake, radically simplified
The intake state machine collapses into **three beats**:

1. **Ask once.** Patrol posts a single batched questions comment (numbered, options with a marked recommendation, background collapsed) — then steps back. No re-batching, no reply grammar required: the thread belongs to the humans. Free-form discussion, open to the whole team, from any device.
2. **Summarize on demand.** When the discussion settles — or immediately, if the recommendations look right — the **assignee comments `summary`**. The agent condenses the issue body + all comments into one `[intake] · summary`: story + acceptance criteria + proposed track + an attributed decision trail, with two honest sections: **assumptions** (every unanswered question, resolved to its recommendation and stated plainly) and **contested points** (disagreements shown both-sides; one reply flips them).
3. **The label confirms.** No `approve` keyword. The assignee applies the gate label, and the choice itself confirms the track: `ready-for-spec` ⇒ `track: spec`, `ready-for-dev` ⇒ `track: fast`. Patrol then rewrites the body and the loop takes over. Confident? Skip `summary` and label directly — patrol summarizes before finalizing either way.

**Everything before the label is input; the label is the decision.** Gone: the `approve` keyword, the digest comment type, re-batch rounds, and answer-parsing rules — patrol's async intake is now a three-trigger route.

### 📖 Guide updated
The [interactive guide](https://taikerliang.github.io/roz-gate/) tells the new story end to end: the simulator walks the free discussion, the `summary` comment, the contested point a teammate wins, and the single label that closes intake and opens gate one; the wizard and label cards follow suit.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

No re-init needed — the new flow lives entirely in the plugin's brief and commands.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.3.0...v1.4.0

## v1.3.0 — team-ready intake: reply grammar + gate-holder authority — 2026-08-05

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.3.0>

## Highlights

### 💬 A reply grammar built for phones
Async intake batches now follow a fixed, skimmable format: numbered questions with 2–3-word labels, option bullets with the recommendation marked, a one-line *why*, and long background collapsed into `<details>`. Answering is one line from any device:

- `all recs` — take every recommendation, done
- `1a 2b` — answer per number
- free text — always works

### 👥 Gate-holder authority — intake goes multi-player
Intake threads are open to the whole team, but authority never drifts:

- **Gate holder = the issue assignee** (unassigned → the issue author). A native forge field on both GitHub and GitLab — zero new config.
- Anyone may reply; every answer is folded **attributed**. Only the gate holder's answers settle questions, and only their `approve` files the proposal — an `approve` from anyone else is noted, never triggered.
- **Conflicts are never resolved by the agent.** Disagreeing replies come back as an `[intake] · digest` @-mentioning the gate holder — who said what, the trade-offs, the agent's recommendation — and the holder's reply is the decision of record.
- The proposal cites the decision trail: who proposed, who decided. The MOU gets a signature page.

### 📖 Guide updated
The [interactive guide](https://taikerliang.github.io/roz-gate/) now tells the team story: the issue-life simulator includes a teammate's conflicting reply and the digest the assignee settles, and the "what should I do now?" wizard knows the gate-holder rule.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

Existing projects need no re-init for this release — the new rules live in the plugin's brief and commands.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.2.0...v1.3.0

## v1.2.0 — persona seats: bring your own agent team — 2026-08-05

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.2.0>

## Highlights since v1.0.0

### 🪑 Persona seats — link your existing agents into the loop (1.2.0)
The five role names (product, em, implementer, qa, reviewer) are now **fixed seats** with swappable occupants. Already have a `backend.md` you've tuned for months? `init` links it into a seat (`implementer: backend`) — your file stays yours, unmoved and unrenamed; unlinked seats fall back to the plugin defaults.

- New `### Roz Gate personas` block in the project CLAUDE.md maps each seat to the subagent actually dispatched.
- **Persona is swappable; the contract never is**: every dispatch attaches the seat's Owns/Never contract, and `init` lints a linked persona against it at link time — a qa that wants to "read the code first" doesn't get seated.
- Fully backward compatible: projects without the block keep plugin defaults; patrol flags when a re-init would help.

### 🚪 Clean exits: `/roz-gate:uninit` (1.1.0)
The inverse of `init`: refuses to run while anything is in flight, removes exactly what `init` installed (CLAUDE.md section, implementer persona — asked first, idea template), keeps forge labels by default (deleting them erases closed-issue history), and never touches work products — specs and the acceptance suite become ordinary project assets. Run it in every project **before** `/plugin uninstall roz-gate`.

### 📖 Interactive guide
A bilingual (EN/中) one-page guide at **https://taikerliang.github.io/roz-gate/** — the MOU→contract mental model, the team's seats, a clickable loop map with the three gates, a label reference, a step-through "life of an issue" simulator (with the change-order detour), and a "what should I do now?" wizard mirroring patrol's classification table.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

Existing projects: update the plugin, then re-run `/roz-gate:init` — it refreshes the workflow pointer and walks you through seating the team.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.0.0...v1.2.0

## v1.0.0 — 2026-08-04

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.0.0>

Plugin renamed from **gated-loop** to **roz-gate** (repo moved to TaikerLiang/roz-gate). Marketplace name is now `roz-gate-marketplace`; commands are now `/roz-gate:*`. Existing installs must re-add the marketplace and re-run `/roz-gate:init` in each project.

## v0.6.1 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.6.1>

- **The workflow prose now ships with the plugin, not with each repo** — `/gated-loop:init` writes only a short pointer section + config block into the project's CLAUDE.md, referencing `references/workflow.md` inside the plugin. A plugin upgrade now takes effect in every bootstrapped repo at once, no re-init needed
- Fix: the CLAUDE.md stamp tracks the template version, not the plugin version
- Docs: init writes a workflow pointer, not the workflow itself

## v0.6.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.6.0>

- **Propagate plugin upgrades into installed workflow sections** — groundwork for keeping repos bootstrapped on older plugin versions in sync

## v0.5.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.5.0>

Docs release — sharpen the workflow's mental model:

- **The MOU-vs-contract model for intake and spec**: intake produces a memorandum of understanding (story + AC), the spec stage produces the binding contract
- Expand it into the owner–contractor–inspector table mapping the roles

## v0.4.1 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.4.1>

- **Exempt inbox triage from patrol's one-issue-per-pass rule** — a patrol pass acts on one in-loop issue, then triages the whole inbox; since intake is comment-only, every batch of questions lands in a single pass
- Docs: note patrol triages the whole inbox each pass

## v0.4.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.4.0>

- **Batch async-intake questions into one comment per patrol pass** — a comment round trip costs a day, not seconds, so the inbox's intake now posts every open question at once (numbered, each with a recommendation) instead of one question per pass
- README: describe batched inbox questions

## v0.3.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.3.0>

- **Route all intake through the product agent via a shared intake brief** — clarification thinking lives in the specialist, never the orchestrator; `/gated-loop:to-issues` and patrol's async intake now share one brain (`references/intake-brief.md`)
- Add a pre-push hook enforcing plugin version bumps
- README: document `/gated-loop:to-issues` and the shared intake brief

## v0.2.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.2.0>

Initial public cut of the Gated Loop plugin: the role-driven, human-gated development workflow — spec debate, blind black-box QA, independent review, integration verdicts, and a patrol scheduler — for GitHub (gh) and GitLab (glab).

