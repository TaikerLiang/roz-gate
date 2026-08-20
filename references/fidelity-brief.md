# The fidelity brief

Dispatch instructions for the `reviewer` seat when it audits **the QA
suite's fidelity to the spec** — stage (5q), run at B5 alongside the code
review, in a **separate dispatch**. The QA suite is the artifact the
integration verdict is computed from and, without this pass, the loop's
only unaudited node: a vacuous suite makes a green verdict silently
forgeable. Your output is **cited evidence for the human — never a
pass/fail verdict**: models judge oracle correctness worse than they
write oracles, so you present adjacent quotations and let the spec argue.

## Inputs — and the blindness rule

Work from a `qa/<n>` checkout **only**: `spec.md`, `technical-spec.md`,
`<acceptance_dir>/<feature>/`, `test-spec.md`. That branch structurally
contains no implementation code — the same topology that makes QA blind
makes you blind. **You never read the implementation** (`feat/<n>`), and
this dispatch must not continue a context that has: a fidelity reviewer
who has seen the implementation rates tests faithful because they pass —
the exact bias this audit exists to remove. If your context has touched
`feat/<n>`, abort and say so.

Your authority is `spec.md` and `technical-spec.md`, nothing else.
"Weaker than the scenario states" is a legal finding; "missing" is legal
only when the missing thing is written in a scenario or contract clause.
Anything beyond that is you writing tests by proxy.

## Step zero — contract currency

Before reading a single test: enumerate every amendment agreed in
spec-CR threads, implementation-CR threads, and issue comments **since
`technical-spec.md`'s last commit**, and confirm each is folded into the
contract text. An unfolded amendment is a **blocking finding routed to
the main agent** (the contract's owner), and the review stops there — a
fidelity review against a stale contract is worse than none, because it
launders the staleness as verified.

## The four questions

1. **Scenario fidelity** — does each test assert what its scenario
   says? The scenario says ghosts are logged *by name*; does the test
   assert the names, or just count skips?
2. **Vacuous assertions** — the checklist below.
3. **Coverage honesty** — regenerate the scenario→test map from the
   trace markers in the test source (see test-spec.md's declared marker)
   and compare it against `test-spec.md`'s claim. Report defects as an
   **itemized list**, never folded into the fidelity count. For every
   `uncovered / not testable through the port` row, **check
   `technical-spec.md` §5's control and observation points yourself** —
   a scenario reachable through the port as specified but marked
   unobservable is a finding, and a `test-spec.md` §4 verbatim-identical
   to the implementer's §5 walk with no reconciliation trace is itself a
   finding (self-certification laundered through QA).
4. **Over-assertion** — does any assertion require behaviour that no
   scenario and no contract clause states? A toothless test lets a bug
   through; an over-asserting test produces a **false RED** at
   integration, which costs the verdict its credibility.

**The origin rule** (cheap, high-yield): every expected literal in an
assertion must have an origin in spec or contract text. A literal with no
origin was almost certainly read off the implementation — the
actual-behaviour oracle, the exact failure mode of generated tests.

## Vacuous-assertion checklist

1. **No assertion at all** — exercises the system and ends.
2. **Tautological** — asserts a value against itself or against output of
   the same call under test.
3. **Asserts the double** — checks a stub returned its configured value,
   or that a mock was called, where the scenario names an observable
   outcome.
4. **Weaker than the scenario** — "not 200" where it says "403 and no
   record created"; truthiness where it names a value; substring where it
   names exact state.
5. **Unreachable or skipped** — skip/xfail, commented out, after an early
   return, in a branch never entered.
6. **Exception-swallowing** — bare catch-all, or `raises(Exception)`
   where the scenario names a specific error.
7. **Self-fulfilling setup** — arrange writes the exact state assert
   reads, no system call between.
8. **Wrong subject** — asserts an adjacent entity, wrong field, or a
   stale local copy instead of re-reading observable state.
9. **Missing negative half** — the scenario's "and no notification is
   sent" clause has no assertion. The most common blind-QA miss.
10. **Order- or time-blind** — the scenario specifies sequence or expiry;
    the test asserts final state only.
11. **Cannot fail given the port** — asserts a shape the port can only
    ever return.
12. **Mapping defects** — a `test-spec.md` row citing a test that asserts
    a different scenario; two rows citing one test; a "covered" scenario
    whose test is skipped.

## Findings — format and routing

- Every finding carries **two verbatim quotations, adjacent**: the spec
  or contract clause relied on, and the assertion excerpt with
  `file:line`. "S5 says ghosts are logged **by name**; the test asserts
  `len(skipped) == 2`." A finding without citations is unsubstantiated by
  construction — QA declines it.
- Post findings as inline threads on the **QA CR** (THREAD-POST-INLINE,
  body starts `**[reviewer] · blocking|should-fix|nit|question**`,
  anchored to the test file:line), plus **one top-level summary comment**:
  fidelity as a count ("29/32 faithful — look at these 3, here's why"),
  coverage defects itemized separately. **Never post into an existing
  unresolved thread** — patrol classifies threads by their last comment,
  and an agent comment there flips the issue to waiting-on-user.
- Judgment calls go out at `question` severity, not `blocking`.
- **Three dispositions, not two**: a test can be wrong, or the scenario
  can be **unassertable as written** — that is a spec finding misfiled as
  a test finding; report it to the main agent, don't route it to QA.
  Same class: a rule asserting a property the implementer cannot be
  ordered to produce (a claim about pre-existing reality) that carries no
  `(measured, …)` tag is a **spec finding** — the claim check the loop
  runs at stage (2) evidently missed it; a faithful transcription of a
  falsehood satisfies fidelity, so you are the last reader who can flag
  it.
- **Scenario-meaning disputes are spec ambiguities**: they route to a
  spec-CR thread through the main agent (the (2a) machinery) — never
  settled reviewer-to-QA on the QA CR.

Findings change QA's tests; they never pass or fail the feature. The
verdict belongs to integration; the gate belongs to the human.
