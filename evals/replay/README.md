# The replay tier

Run a roz-gate command against a frozen forge fixture and measure whether
the loop's rules hold. **This tier produces a measurement, not a gate**:
per-case observed rates with Wilson 90% intervals, no pass thresholds
anywhere. The number nobody has — *how often does the agent break its own
rules?* — comes first; what to gate on is decided from the baseline, not
in advance of it.

It is also a **model-portability benchmark**: the question is "is the
roz-gate protocol operable by other models, and at what compliance rate".
Claude Code is the runtime for every row; `--sut` swaps the model,
whole-stack — seats ride the same endpoint as the main agent, because
"the loop operated end-to-end by X" is the honest number.

## Running

```sh
evals/replay/run-replay.sh [--sut NAME] [--k N] [case ...]
```

- SUT rows live in `models.yaml`. `opus` is the fixed reference baseline;
  `fable` is the current operator. API rows (translation proxy) are a
  marked TODO — the resolution architecture accommodates them unchanged.
- **Baseline note, verbatim in every report**: the baseline measures the
  protocol's ceiling reference, not necessarily the production loop's
  current operator; the current operator appears as its own row.
- **Resumable**: every iteration persists to
  `report/<sut>/<case>/run-<i>/`; completed iterations are never re-run.
  A sweep interrupted at case 12 continues from case 12.
- **Never CI, never pre-push**: replay costs minutes and millions of
  tokens per sweep. CI runs the lint tier only. Replay is local,
  on-demand, pre-release manual.
- Cost: API-mode rows record dollars from response usage; subscription
  rows record tokens labeled quota, no dollar figure. Measured single-run
  costs (fable): a quiet patrol pass ≈ 209k in / 2.7k out; a review-turn
  pass ≈ 114k in.

## The smoke gate

Before any sweep spend, each SUT passes 3 trivial plumbing cases (read a
file, run a command, post a stub comment) at k=1. A row that fails is
marked **HARNESS-INCOMPATIBLE and is never scored 0** — a broken
translation adapter must not indict an innocent model. The smoke results
are each row's plumbing proof.

## Method

**The SUT** is headless Claude Code (`claude -p`) running the working-tree
plugin in a throwaway git repo, hooks included — the measurement covers
the guard layer, not the prose alone.

**The forge** is a stateful stub (`forge-stub/gh`) shadowing the real CLI
via PATH. Fixtures seed `state.json`; writes mutate state (commands read
back their own writes mid-run) and append to `journal.jsonl` — the
primary observation channel, alongside the session transcript
(dispatch payloads, Bash commands) and the sandbox repo with its local
bare remote (pushes are refs, nothing leaves the machine). An invocation
matching no route **invalidates the iteration** — invalid, never red: a
reach the fixture doesn't define is a fixture gap, not a model failure.
The same guard invalidates a session that never produced a result event,
so an empty run can never pass a zero-writes case vacuously.

**Blindness**: every assertion derives from the ledger case text and the
prose that owns the behaviour, cited inline (`# source:`) with the quoted
rule; the runner refuses an uncited checker, and the checkers land in a
distinct commit that precedes the first recorded baseline run — the
history is the proof they were not written from observed output.
Where a seat's return is fixture-given (E2's scripted implementer
double), that controls a variable; D3 keeps the real dispatch because
the payload is the assertion.

**pass^k**: every case runs k times (A–E k=5, F1–F5 k=10) and reports the
observed rate — never a boolean. F6 is instrument-only: a 12-turn session
measuring compliance at turns 1/3/5/8/12, producing a curve, no pass mark
(the published decay puts the median first omission around step four; a
three-step fixture measures nothing).

## What this tier cannot see

1. **A6 (notification) is deferred, untested** — the headless sandbox has
   no messaging channel connected, and patrol.md:148 makes silent skip
   *correct* there: the case measures nothing until a channel stub
   exists. An observability gap, not a spec gap.
2. **Semantic paraphrase**: text-shaped assertions (F4's claim wording)
   are regex-shaped; a paraphrased violation slips through, so every
   text-based rate is a **lower bound on violation**.
3. **D2's deep blindness**: the transcript proves no observable touch of
   `feat/<n>`; it cannot prove absence of in-context leakage from text
   already in the session.
4. **Judgment quality**: E1 stays in the judgment tier, deferred.
5. **Fixture shape bias**: one fixture per case measures the fixtured
   shape. The lint tier's sampling-bias statement applies verbatim: every
   case derives from defects observed in one repository, by one operator,
   on one atypical issue. Green proves no regression on work shaped like
   that; nothing about shapes never run.
6. **Headless vs attended**: `-p` with auto-approved permissions matches
   autonomous patrol, not attended operation.
7. **Command substitution**: a forge write whose body arrives via
   `$(...)` is invisible to the journal's body fields (the stub still
   records the write itself).
8. **Citation anchors are file:line + quoted text**, checked by eye, not
   mechanically re-anchored — a prose reshuffle can silently stale a
   citation. Content-anchored citation verification is a marked TODO.
