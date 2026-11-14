# The Workflow Value pilot

Level 3 of the charter (`charter.md`): on real issues, what does the whole
Roz Gate loop catch that a capable agent without it misses, what does it
cost in human interruptions and compute, and was the trade worth it?

A pilot, in two phases. Phase A is built; Phase B is a protocol. **Nothing
here has been run** — the commands are in `judgment/README.md`, and the
spend is the maintainer's.

## The six answers (`charter.md § Rules for new eval work`)

1. **Level** — 3. It reuses the judgment tier's runner, fixtures and judge;
   the level is the question, not the runner.
2. **Product question** — the one above.
3. **Oracle** — each issue's retrospective record: what later mattered,
   what did not, picked by the gate holder and never taken from an arm's
   output. Both arms are judged on the same propositions by the same
   quote-verified judge; every count is mechanical.
4. **What a result shows** — per issue, which retrospective decisions each
   arm surfaced before a human was needed, and at what cost. There is no
   green.
5. **What it does not** — § What the pilot does not establish.
6. **Product decision and stopping rule** — § Decision rule.

## The issues

Real ADMC issues, each frozen at the moment before work began on it
(`judgment/cases/<F>/`, `judgment/README.md` § Contamination).

| fixture | value shape |
|---|---|
| F-63 | a spec ambiguity that materially changed the design |
| F-54 | a design finding spread across several threads |
| F-67 | a finding, not a question |
| F-51 | a case where questioning would be harmful |
| *(fifth)* | **not chosen** — the four cover no dependency or state case and no QA / harness case; the gate holder names it and freezes it (`judgment/README.md` § Adding a fixture) |

`cases/<F>/retrospective.json` is the gold record:

| field | |
|---|---|
| `value_shape`, `why_selected` | why this issue is in the pilot |
| `important` | the decisions that later changed the design or the outcome — the fixture's P criteria |
| `immaterial` | what looked ambiguous and did not matter — its N criteria |
| `known_rework` | rework that happened because a decision was missing or late |
| `accepted_outcome` | the contract and result finally accepted |
| `unknown` | every field the history does not settle. The word is `unknown`, never a guess |
| `reviewed_by`, `reviewed_on` | the gate holder's signature on the **whole record**. `null` until then; an unreviewed record is never paired |

## Phase A — to the first point a human is needed

Both arms, every issue, no simulated human.

| held equal | |
|---|---|
| repository | the same pin's tree, every later ref and object removed |
| forge | the same frozen state behind the same stub |
| model | the same `--sut` row; a pair is never mixed across models |
| tools | the same Claude Code tools and permissions |
| ordinary facts | how to test, where acceptance tests live, the forge — in both arms' `CLAUDE.md` |

| | treatment | baseline |
|---|---|---|
| plugin and hooks | Roz Gate, as shipped | none |
| `CLAUDE.md` | the loop's workflow section | the same file with that section removed and its ordinary commands kept (`## Project commands`) |
| history | the pin's history plus the overlay commit | one root commit carrying that tree (`Initial commit`): the pin's history names the loop, and an overlay commit's diff prints the removed section (ruling (b), 2026-11-14) |
| instruction | the fixture's command (`/roz-gate:next-stage <n>`, `/roz-gate:patrol`) | `judgment/baseline-prompt.md`: handle the issue; ask on the issue and stop if a human decision is needed; otherwise finish and open a pull request |
| stops | at its first human gate | when it asks, or when it has opened a pull request |
| judged surface | what it wrote on the spec CR or the issue | its comments on the issue, its pull requests' text, its final message |

The baseline may ask and is not told to. It is told nothing of specs,
stages, seats or gates (lint J3 holds a closed word list), and it is denied
nothing an engineer on the repository would know.

**What is recorded, per arm:**

- **important found / missed** — by id, the judge's verdict on each P
  criterion;
- **immaterial raised** — each N criterion the arm spent a question on.
  N10 ("silence was right") is raised exactly when the arm asked
  anything, in either arm; whether the loop's summary recorded its
  assumptions is the tier's precision, not this field;
- **unscored** — a criterion the judge could not rule on (judge-invalid).
  It is neither found nor missed, and its run is never paired;
- **questions** — the treatment's distinct Q-ids; the baseline's *asking
  comments* (comments on the issue that contain a question). Two units,
  named in the report, never subtracted from one another;
- **outcome and round trips** — the treatment ends at a gate: one round
  trip, by construction, whether or not it asked anything. The baseline:
  `asked`, `finished`, both or neither; one round trip if it asked;
- **cost, secondary** — tokens, tool calls, agent dispatches, suite runs.
  Tokens are the runtime's own totals (`in`, `out`, `cache_read`); a run
  counted by the old counter (no `counter` in its `tokens`, #308) prints
  no figure, only "not comparable".

**The report** (`run_judgment.py --paired <sut>`) is one block per issue,
baseline above treatment, then the raw counts behind material-question
recall (important surfaced / important in the record) and precision's
complement (immaterial raised / immaterial in the record). **Nothing is
summed across issues.** An issue is UNPAIRED — listed with the reason,
contributing no number — when its record is unreviewed, when an arm has no
run, when an arm's run is INVALID (no result event, a session error, a
session whose init event shows a plugin or MCP server beyond what the arm
passes (#307), a forge call the stub cannot answer), or when a run has an unscored
criterion. Each of these is the instrument's failure, never the arm's.

## Phase B — the whole loop, on one or two issues

Not built. Run only if Phase A leaves a question that rework or final
defects would answer, on at most two issues the gate holder picks.

- **Qualifies:** an issue whose record has `known_rework` and
  `accepted_outcome` written (not `unknown`), and whose pair in Phase A was
  valid.
- **The scripted human** stands in for the gate holder in both arms, from
  the record alone:
  - a question the record answers → the historical answer, verbatim;
  - any other question → "your call — state your assumption and continue";
  - a gate → applied when the stage's output exists, with no comment;
  - it never volunteers anything, and never answers from what happened
    later than the record's decision point.
- **Measured:** re-spec and rework cycles; harness-only failures and repair
  loops; defects left unresolved against `accepted_outcome`; whether the
  final implementation satisfies it; every Phase-A field again, over the
  whole run.
- **INVALID:** the scripted human had to answer something the record does
  not cover *and* the arm's result turned on it; a session or stub failure;
  a toolchain failure (the build could not run in the sandbox).
- **Its own check first:** the scripted human is an instrument and needs a
  red-proof before any run — a question the record answers, one it does
  not, a gate with no output yet.

## Decision rule

The pilot exists to move a product decision, per gate and per seat:

- an important decision the treatment surfaces and the baseline misses, on
  an issue → evidence **for** the stage that surfaced it;
- a stage whose questions are mostly immaterial items on every issue it
  ran on → a candidate to merge or cut;
- an important decision both arms miss → a gap in the seat's brief, not an
  argument about the loop (the tier's standing P2 finding is one);
- the baseline finishing correctly with no round trip where silence was
  right, and the treatment spending one → the cost of that gate on that
  shape, stated as such.

**Stopping rule.** Phase A: every issue × 2 arms × k=1; a second run only
for a pair whose reading turns on one stochastic item. Phase B: at most two
issues. More issues are added only with a new value shape.

## What the pilot does not establish

- **Net value over a whole issue.** Phase A stops at the first human
  moment; rework, repair loops and final defects are Phase B's.
- **Anything general.** Five issues, one repository, one gate holder, one
  model per pair. No rate, no interval, no aggregate.
- **Independence.** These issues have shaped the loop's prose, and ADMC's
  threads are public: either arm may have seen the answers. A found item
  cannot be told from a remembered one.
- **A fair question count.** Q-ids and asking comments are different
  units.
- **That the baseline is the best baseline.** One instruction, no
  iteration on it; a better-prompted agent is a different comparison.
- **A model ranking.** The published treatment rows are opus; they are not
  paired with another model's baseline.
