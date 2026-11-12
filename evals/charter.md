# The evaluation charter

What Roz Gate's eval program is trying to prove: a taxonomy and a decision
rule for eval work, not an evaluator. A **tier** (lint, hook, replay,
judgment) is how evidence is produced; a **level** is the product claim
that evidence may support. The two are independent.

## Terms

- **Verification** — deterministic proof that repository code, text or
  instrumentation satisfies a known invariant. It measures no model.
- **Compliance eval** — stochastic evidence that an agent follows a known
  behavioural rule.
- **Judgment eval** — evidence about the quality and materiality of an
  agent's semantic decision.
- **Workflow-value eval** — evidence about the net engineering value of the
  complete loop against a baseline.

## Level 1 — Compliance

*Can the agent reliably execute a known rule or component contract?*

- Prefer deterministic enforcement: a rule that can be a hook is a hook.
- A new compliance case comes from an observed production or eval defect,
  never to raise the case count.
- Green proves the protected behaviours hold. **A fully green Level-1 suite
  does not prove Roz Gate improves engineering outcomes.**

## Level 2 — Judgment

*Does the agent make the right engineering decision under ambiguity?*

- Decisions: `BLOCK`, `FLAG_AND_CONTINUE`, `NO_FINDING`, against
  human-reviewed gold from historical decisions.
- Metrics, always together: material-decision recall, material-decision
  precision, false-block / unnecessary-question rate, reason-category
  correctness. Recall alone rewards asking everything.
- Deterministic checks carry the oracle where they can; an LLM judge scores
  only bounded rationale. Definitions: #258.

## Level 3 — Workflow value

*Does the full loop beat a credible baseline at acceptable cost?*

- The same historical issue: a capable agent without the loop against
  current Roz Gate.
- Outcomes: important decisions found and missed, unnecessary human
  questions, human round trips, re-spec and rework cycles, harness-only
  failures, unresolved contract or design defects.
- Tokens, tool calls, suite runs: secondary cost, never the value metric
  alone. Definitions: #259.

## Current usage

Existing tiers have a current default mapping, but the level is determined
by the product question and experimental claim, not by the runner or
directory. A Level-3 question asked through the replay runner is Level 3.

| instrument | today |
|---|---|
| `lint/`, `hook` rows and `hooks/tests/`, red-proofs, the ledger check, shadow-signal checks | Verification, primarily supporting Level 1 |
| `replay/` | mostly Level-1 Compliance — including #199, a QA component regression / prose ablation, not the repository's AI-eval score |
| `judgment/` | Level 2 — a seed, and V1's ten development decisions (`judgment/v1/`); no holdout yet |
| — | Level 3: no experiment yet (#259) |

## Rules for new eval work

The issue that adds an eval states:

1. the level it belongs to;
2. the product question it answers;
3. why its oracle is trustworthy;
4. what a green result proves;
5. what a green result does **not** prove;
6. the **product decision** — what changes if it goes red, and if green —
   and the **stopping rule** — when the evidence is enough and no more runs
   or cases are added. (#199: adopt a prose variant or not; stop when
   repeated trials tell the variants apart.)

An eval that cannot name its product decision is not added for coverage.
