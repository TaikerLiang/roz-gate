# The eval ledger

Three tiers of evidence that the workflow's rules hold.

| Tier | Cases | Status | Cost class |
|---|---|---|---|
| **lint** | 13 | built — `lint/run_lint.py` | static text checks, milliseconds, deterministic |
| **replay** | 18 | built — `replay/run-replay.py` | needs a running loop and pass^k over repeated runs |
| **judgment** | 7 items / 4 fixtures | built — `judgment/run-judgment.py`, k pending calibration | a real repo per iteration plus an opus judge; the only tier that measures whether the spec stage earns its cost |

Two failure modes exist, and only one of them is what people expect:

1. **A rule is not followed.** Replay-tier work catches this. Stochastic,
   needs repeated runs.
2. **The rule itself is broken.** No amount of compliance testing catches
   this — every stage faithfully executes the broken rule and reports
   green.

Everything in the lint tier is class 2, and each case is either a defect
that actually shipped (version annotated in the runner) or a preventive
check on the identical shape. These checks are proofs, not samples: a lint
that reports "no occurrence" has enumerated the space.

## What a green run proves — and what it does not

**Every case in this ledger derives from defects observed in one
repository, by one operator, on one atypical issue** — a one-time CLI
migration with no UI, no API surface, no multi-person collaboration. A
fully green suite proves *this loop does not regress on work shaped like
that issue*, and nothing about shapes never run. Do not read the badge as
"the rules work".

## Language

The suite is Python end to end — a design constraint, not a preference:
the suite's owner reads Python, not shell, and a check list its owner
cannot read gives him no control over the rule corpus, which defeats
the suite's purpose. Everything runs under one uv project
(`evals/pyproject.toml`, stdlib-only; plain `python3` works
identically). The one deliberate exception is `hooks/tests/` — the
HOOK suite, not an eval tier: bash testing a Python hook through its
stdin/exit-code contract, exactly the interface Claude Code invokes.

## Method: linting rules that a model executes

The checks under test are not code — they are grep commands and
conventions written into prose that a model executes at runtime. A lint
cannot execute prose, so every case that guards a runtime check gets two
layers:

- **Pattern proof** — the canonical pattern lives once in `run-lint.sh`
  and runs against positive AND negative fixtures (`fx/`). Proves the
  pattern behaves.
- **Source conformance** — the plugin source must carry that same pattern
  byte-for-byte. Proves the prose the model executes is the pattern that
  was proven.

Either layer alone is a hole: pattern-only proves a pattern nobody ships;
conformance-only ships an unproven pattern. Cases whose subject IS the
source text (B3, C6, D1, E3, E4) are conformance-only by nature.

**Brittleness policy.** Every conformance check anchors on a load-bearing
literal — a grep pattern, a filename, a CLI flag, a marker token — never a
sentence. A rewording that breaks a check is a cheap false red (the
failure message names the anchor and the file; move the anchor). The
failure to design against is the silent green — hence the mandatory
positive fixtures. A check whose anchor has to move more than twice earns
hoisting its literal into a shared reference file.

Why conformance must read the source and never the release notes: both
shipped-defect annotations this suite was built from that were checked
against release notes turned out wrong (B1, C6) — in each, **the fix
landed where it was written and never where it was read**. The adapter
documented the merged-CR query; the consumer never invoked it. The
writing convention was fixed; the check pattern never widened. A lint
anchors on the site that *reads* the rule, or it proves nothing.

**Red-proof requirement.** A suite nobody has seen fail is a decoration.
Every new case must be demonstrated red before it counts: mutate the
source it guards (flip the flag, plant the near-miss, append the unknown
label), watch it fail *legibly* — the message names what tripped — then
restore. Record the mutation in the case's commit message.

**The alternative with teeth.** C4 (`track: fast` + `ready-for-spec`
refused) is in the case list but has no lint: it is enforced by
`hooks/guard-gate` and proven in `hooks/tests/run-tests.sh`, which the
same release gate runs. It is the worked example of the stronger option —
when a rule can be a hook, make it a hook. B4 was promoted in 1.14.0 (rule
C). E2 was promoted in 1.15.0 (rule D) on the replay tier's evidence: the
prose said "relocate", 5/5 copied; the prose was made as explicit as prose
gets ("move … delete it from the source document"), 5/5 still left the
section behind. Lint E2 keeps the hook, the replay checker and the proof on
one literal and sweeps this repo's specs tree at push time. D2 was
promoted in 1.16.0 (guard-blind rule E) at 4/5 — one QA child read
`src/app.txt` under the fidelity dispatch — because that failure is
invisible at the gate: the class that gets teeth regardless of rate. Lint
D2 holds the hook's three regexes byte-identical to the replay checker's.

## The gate

`.githooks/pre-push` (wired via `core.hooksPath`) runs this suite
(`python3 evals/lint/run_lint.py`) and the hook unit tests on **every
push** and blocks on red. "Must pass before
every version bump" is a subset of that; unconditional is simpler and the
cost is milliseconds. `git push --no-verify` is the documented human
override; `.github/workflows/checks.yml` is its backstop.

Run locally:

```sh
python3 evals/lint/run_lint.py     # or: cd evals && uv run lint/run_lint.py
```
