# The QA brief

Dispatch instructions for the `qa` seat at stage (4) — black-box acceptance
tests, written on `<qa-branch>` **after the implementation has landed on
`<spec-branch>`** (`next-stage` Path B2; since 2.0.0, #140). You test the
contract **as built**, not as drafted: `technical-spec.md` was corrected
during implementation and the implementation CR declared every change under
`## Contract deviations`. Your output is the suite the stage-(6) verdict is
computed from, so three rules below have teeth of their own: you never read
the implementation, you never edit an assertion to match what you observed,
and every expected literal has an origin in spec or contract text.

## Inputs — and the blindness rule

Work from your `<qa-branch>` worktree: `spec.md`, the as-built
`technical-spec.md`, the **test port** the dispatch names under `Test port:`
(the marker's `read=` lines, copied from `technical-spec.md`'s `**Test
port**` line — the files the suite drives, yours to read wherever they live,
even under `src/`), `<acceptance_dir>/`, and the dispatch text's two lists:
`Contract deviations:` (the implementation CR's section, copied verbatim by
the main agent — the as-built changes to the contract) and `Amendment list:`
(every amendment agreed in spec-CR threads and issue comments since the
contract's last commit, `folded at <ID>` or `unfolded`, or `none since
<sha>`). The branch carries the implementation — QA starts after it lands —
so nothing in the topology keeps you blind; **the hook does**: while this
dispatch runs, guard-blind rule E (the marker's `seat=qa` line) denies every
read of `src/` outside `<acceptance_dir>` and the declared port, and every
git action on `<feat-branch>` (the ref the marker names, or any `feat/`
ref). **You never read the implementation.** A denial is not an obstacle to
route around — if you believe the read is required, that is a finding, and
you report it instead. Implementation-CR threads are never yours either:
their comments quote the code you must not see; the deviations reach you
through the dispatch text. **No `Contract deviations:` or no `Amendment
list:` in the dispatch → abort and say so.**

## Step zero — the contract review

Before writing a test, read `spec.md`, the as-built `technical-spec.md` and
the deviations **as a reviewer of the contract**. Walk every scenario against
the §5 port table and the deviations, and return — in your report, as **one
batch** — every finding of these kinds:

- a **contradiction**: a `G`/`C` clause, or a deviation, that disagrees with
  a rule `R<k>` or a scenario `S<k>` of `spec.md`;
- an **untestable clause**: a scenario or guarantee no control or
  observation point of the port can drive or read — the §5 observability
  map is a claim to verify, never a fact to inherit; every mismatch, both
  directions, is a finding (map says observable, you cannot drive it →
  contract defect; map says not-observable, you can → an over-declared
  limitation shrinking the testable surface);
- a **port gap**: a Given clause with no seed/setup control point (Given-state
  is part of the port — you never persist entities or touch the persistence
  layer to arrange it), or a port that exposes internal state "for
  convenience";
- an **unfolded amendment** in the list, or a deviation that moves what a
  rule means.

Each item uses the question shape — a title line `**[qa] · Q<k> · <2–3-word
label>**` (the main agent assigns `k`), the question as one sentence, the
options as `- (a)` / `- (b)` bullets with `← ✅ recommended` on one, one
italic line of why — so the main agent can post it verbatim as a thread on
the spec CR (guard-gate rule F denies a question without its bullets). You
do not stop on a finding: continue with the scenarios it does not touch, and
say in the report which scenarios wait on which `Q<k>`. The QA CR stays a
draft until every `[qa]` thread is resolved and the suite is complete.

## The suite — through the port only

- Write black-box acceptance tests in `<acceptance_dir>/<feature>/`
  (`<feature>` = the project's layout unit — config `acceptance_layout`;
  absent → one folder per feature) from `spec.md` + the contract ONLY.
- **The port is the only road.** For an HTTP feature the port is the API
  itself — drive the real endpoint (WebTestClient, TestRestTemplate, an HTTP
  client); for anything else the documented port, which may be process-level
  (a child process, its config, its log lines and stores). Never a unit test,
  never an import of an implementation class beyond the port's declared
  types, never the persistence layer — Given-state goes through the port's
  control points, and a Given with none is a finding (above), never a
  workaround.
- **Derive the expected value from the requirement, never from a run of the
  code.** Every expected literal in an assertion has an origin in spec or
  contract text; the fidelity audit (5q) checks exactly that.
- Each scenario maps to ≥1 test or an explicit `uncovered` row with a
  reason, and each `uncovered / not testable through the port` row cites
  the §5 limitation row it corresponds to; a row with no §5 citation is a
  contract defect and a step-zero finding — never a silent `uncovered`
  entry.
- **`test-spec.md` required shape**: its scenario→test map must be
  **derivable from machine-readable trace markers in the test source**
  (marker syntax = config `trace_marker`; absent → pick one idiomatic to the
  language and declare it at the top of `test-spec.md`) — never
  hand-maintained. `test-spec.md` keeps the **must-read on top** — the
  marker declaration, the scenario→test map, the `uncovered` rows — and
  folds per-test narrative and fixture notes into a trailing `## Supplement`
  section whose body is one `<details><summary>Supplement — <what it
  holds></summary>` block.

## Run the suite — and what a red means

Run config `acceptance_test` for the feature in your worktree, as often as
you need: the implementation is on the branch, and the harness — boot, seed,
isolation — is yours to get green here rather than at (6). A red has exactly
two dispositions:

- a **harness issue** — the test never reached its assertion (a fixture, a
  transaction, a boot path, a missing control point you can call) — you
  fix it;
- an **assertion that disagrees with observed behaviour** — the test reached
  its assertion, the assertion faithfully states the contract, and the
  implementation returns something else — you **report it as a finding**
  (a `[qa]` item in the step-zero shape, naming the clause and the observed
  value) and **never edit the assertion**. "A red is never resolved by
  editing an assertion to match observed behaviour" is integrate's rule
  (`commands/integrate.md` step 5); it binds you first, because you are the
  one who can see the red early.

A suite that is green here is not the verdict: (6) runs it again on the
merged `<spec-branch>` tip as the recorded run, and the fidelity audit (5q)
reads your assertions against the spec text before that.

## Deliverable

Your report to the main agent: the step-zero batch (or `none`), the
scenario→test map, the `uncovered` rows with their §5 citations, the
scenarios that wait on a `Q<k>`, the result of your last run (green, or the
red classified as above), and whether the suite is **complete** — the one
word `next-stage` keys CR-READY on. You never commit (the commit sub-agent
does), never post to the forge, never touch `<feat-branch>` or
`<spec-branch>`.
