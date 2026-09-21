# The judgment tier

Not "did the agent follow a rule" — **"did the agent surface the thing that
changed the human's mind."** LLM-as-judge: the expensive, unreliable tier,
and the only one that measures whether the spec stage earns its cost.

Corpus: seven graded items from ADMC's real history, harvested by the ADMC
session and picked by Paul — **P1 P2 P8 P12** (the human changed the
design because the agent raised it) and **N1 N5 N10** (raising it cost
precision, or asking nothing was right). They collapse into four fixtures,
each a real issue at the moment before the loop ran on it.

| fixture | command | pin (main at T) | freeze T | graded |
|---|---|---|---|---|
| F-63 | `/roz-gate:next-stage 63` | `d188a20` | 2026-08-12T16:16:16Z | P1 P2 · N1 N5 |
| F-54 | `/roz-gate:next-stage 54` | `d2ded12` | 2026-08-09T06:14:57Z | P8 (graded on the batch) |
| F-67 | `/roz-gate:patrol` (intake) | `d188a20` | 2026-08-14T14:07:30Z | P12 — a finding, near-zero questions |
| F-51 | `/roz-gate:patrol` (intake) | `d2ded12` | 2026-08-08T10:40:53Z (inclusive of the human's `Summary`) | N10 — correct silence |

The pins are the **parents** of the historical spec-refinement commits:
the mandate's original SHAs were the refinement commits themselves, whose
trees already hold the questions in `specs/<n>/`. Caught at design time.

## Running

```sh
python3 evals/judgment/run-judgment.py --check       # fixtures frozen? no tokens
python3 evals/judgment/run-judgment.py --redproof    # judge red-proof, 28 judge calls (cached; --rejudge to re-ask) — first, always
python3 evals/judgment/run-judgment.py --sut opus --k 1 F-63   # one iteration
python3 evals/judgment/run-judgment.py --sut opus --k 2        # the sweep (k=2 ruled after calibration)
```

- Never CI, never pre-push: a spec-refinement iteration on a real repo is
  hundreds of thousands of tokens. Local, on-demand, pre-release manual.
- Resumable like replay: `report/<sut>/<case>/run-<i>/result.json` is
  never re-run; a quota banner stops the sweep (exit 4).
- The runner refuses to spend SUT tokens until `--redproof` has run green
  **under the current judge fingerprint** — a hash of the prompt, model,
  quote policy, criteria, expectations and every red-proof document. Any
  change to those makes the stored red-proof stale: cached verdicts miss,
  `--redproof` re-judges, and the sweep refuses until it is green again.
- `--sut` (replay's `models.yaml`) is the SUT only; **the judge is opus on
  every row**, including the opus SUT row.

## Contamination is the whole game

Every comment after T contains the answer. So:

- **The repo** is the machine-local ADMC checkout (`sources.yaml`) cloned
  with `--no-hardlinks`, `main` reset to the pin, every other ref and the
  reflog dropped so nothing after T is reachable by name, then one overlay
  commit. Never network.
- **The overlay** restores the Roz Gate config block to `CLAUDE.md`
  (ADMC's PR #62 moved it to an untracked `CLAUDE.local.md`; the hooks and
  commands read `CLAUDE.md`), from the last commit that carried it in git,
  restamped with the current template stamp; F-63/F-67 add the two
  identity lines because those dates were already in bot mode. The overlay
  SHA is recorded in every `result.json`.
- **The forge** is replay's stub with `state.json` **frozen at T** by
  `materialize.py` (run once at build, outputs committed): the issue body
  verbatim, comments `created_at ≤ T`, **labels and assignee replayed from
  the issues timeline** (the live labels carry the aftermath; the
  historical run's own `status: processing` lock landed minutes before T
  and is removed — the SUT takes its own), plus every issue/PR the body
  cross-references, frozen the same way. Bodies are mutable on GitHub;
  the GraphQL edit history is checked and any edit after T is recorded as
  a fixture caveat (none today).
- **Freeze check**: `--check` (and lint J1, on every push) refuses any
  state whose timestamps exceed T. Red-proofed by planting one post-T
  comment: it names the fixture, the issue, and the comment id.
- **Inbox scope**: the intake fixtures carry the fixture's issue ONLY.
  At F-67's T the inbox also held #51 (summary posted, no track label)
  and #55–#59 (unanswered batches); at F-51's T, #54 sat with answered
  questions and #55–#59 were fresh. Patrol would sweep all of them — 5×
  the tokens and question batches on issues that are not graded. The
  tradeoff: the fixture measures intake on one issue, not patrol's full
  pass.

## The judge

`claude -p`, opus, `--tools ""`, in an empty temp dir, one file of prompt
(`judge-prompt.md`) with two slots: one **criterion** (a checkable
proposition from `criteria.json`) and the **document** — the SUT's
human-facing output only: for a spec refinement, every write on the spec
CR plus `spec.md`'s Open Questions at the pushed head; for intake, every
comment written on the issue. The judge never sees the human's reply, the
design change, the thread URL, or the criterion's polarity.

It answers `{"answer": yes|no, "quote": …}`. **The quote is verified
mechanically** — whitespace-normalized, ≥40 chars, a substring of the
document. A `yes` whose quote fails is re-asked once with the failure
stated; a second failure is **judge-invalid** — never yes, never no —
counted in its own column. A `no` needs no quote (absence cannot be
quoted). Question count is mechanical, never judged: **distinct** Q-ids on
title lines (`**[role] · Q<k> · label**` or `**Q<k> · label**`) — the
spec-cr surface carries each item twice (thread body + spec.md, verbatim
by A6), and a `**Q6**.` cross-reference inside a body is not a question;
the red-proof's count check on the real F-63 output caught both (18 for 8).

## Scoring — two numbers, never blended

Per valid run (invalid exactly as replay: no result event, quota banner,
UNKNOWN route):

- **recall** = P items answered yes / P items in the fixture.
- **precision** = N items NOT raised (judge says no; N10 = zero questions
  AND a summary posted AND the judge finds recorded assumptions) / N
  items, **and** question count ≤ the fixture's cap: F-63 16, F-54 20
  (2× historical), **F-67 1** (the historical five were moot — the
  finding was the value), **F-51 0**.

**The historical reference row prints first in every report** — the real
run's own score, computed from the same criteria on the same judge (§
red-proof): F-63 recall 2/2, precision 0/2 (it DID raise N1 and N5),
count 8; F-54 P8 yes, count 10; F-67 P12 yes, count 5 → cap fail; F-51
count 0, summary with assumptions. That row is what "did the current loop
do better" is read against.

## Judge red-proof — runs before any SUT token

Committed expectations (`redproof/expected.json`), three directions:

- **(a) the real historical outputs** (`redproof/historical/`, fetched
  at build: the 8 root threads of PR #64 + `specs/63/spec.md` Open
  Questions at the refinement commit; PR #60's 10 + `specs/54`; the two
  intake comments) → every P criterion yes with a verified quote, and
  F-63's N1/N5 yes.
- **(b) an unrelated output** (`redproof/unrelated.md`: the E2 replay
  fixture's real spec threads, offer expiry) → every criterion no.
- **(c) paraphrases** (`redproof/paraphrase.json`, hand-written): two
  rewordings per P item → yes; one near-miss → no.

A mismatch fails the red-proof and the runner refuses to start the sweep.

## Cost (subscription quota; the calibration run replaces the estimate)

Anchors: replay E2 130–230k in/iteration on a tiny fixture; a quiet
patrol pass ≈209k. ADMC is a real Java repo and three seats read it —
estimate F-63/F-54 ≈600k, F-67 ≈250k, F-51 ≈200k → ≈1.65M per k; judge
≈11k per criterion call, measured (the red-proof's 28 calls: 309k in). Paul's sequence: red-proof → ONE F-63
calibration iteration → measured cost reported → k ruled. Fixture-gap
UNKNOWNs on a real repo are expected on the first runs (~0.5M allowance);
every UNKNOWN prints in the report so routes are added in one batch.

## Results — k=2, opus SUT, opus judge, plugin v1.16.2 (2026-09-20/21)

| fixture | run | recall | precision | questions | cap | verdicts |
|---|---|---|---|---|---|---|
| F-51 | 1, 2 | — | 1/1, 1/1 | 0, 0 | ok | N10 yes, yes |
| F-54 | 1 | 1/1 | — | 12 | ok | P8 yes |
| F-54 | 2 | 0/1 | — | 19 | ok | P8 no |
| F-63 | 1 | 1/2 | 0/2 | 14 | ok | P1 yes · P2 no · N1 yes · N5 yes |
| F-63 | 2 | 1/2 | 1/2 | 15 | ok | P1 yes · P2 no · N1 no · N5 yes |
| F-67 | 1, 2 | 1/1, 1/1 | — | 5, 4 | **fail** (cap 1) | P12 yes, yes |
| *historical* F-63 | | 2/2 | 0/2 | 8 | | |
| *historical* F-67 | | 1/1 | | 5 | fail | |

Zero judge-invalid across 9 valid runs; one invalid iteration (F-67, stub
route `gh api user`, fixed in the same week). Measured cost per run:
F-51 ≈ 110–120k in, F-54 ≈ 670k, F-63 ≈ 320–560k, F-67 ≈ 135–150k; judge
≈ 10–25k per fixture.

**Reading.** F-51 is perfect: when the right move is silence, opus is
silent. P1 (the user↔workspace relation) surfaces 3/3 including
calibration; P12 (the Makefile already exists) 2/2. **P2 never surfaces —
0/3** — the one item whose historical answer required reading the
trigger implementation (`command-timeout-seconds`); the 2026-08 run asked
it, the current loop does not look there. N5 is asked 3/3 (the human
dismissed it in one letter). F-67 reproduces the historical shape exactly:
the finding plus moot questions. Question counts run higher than the
historical run (14–15 vs 8; 19 on the F-54 miss). The consistent recall
gap is a stage-(2) brief question, not a sampling one; it is the first
thing this tier has told us that the replay tier could not.

## What this tier cannot see

1. **Training-data contamination**: ADMC's threads are public; the SUT may
   have seen P1's answer. Unmeasurable. A P item surfaced in wording close
   to the historical thread cannot be told from recall-from-memory.
2. **Judge paraphrase recall is a lower bound**: red-proof (c) samples it
   with two rewordings per item; it does not bound it.
3. **Sampling bias**: four fixtures, one repo, one operator, one month —
   the same statement as the other tiers.
4. **Precision is operator-relative by construction**: N1/N5 cost
   precision because THIS gate holder dismissed them; another might have
   wanted them asked.
5. **P8 is graded on the batch**: one criterion, yes if any thread
   surfaces the split — coarser than the historical three-thread cluster.
6. **Intake fixtures freeze the inbox to one issue**: patrol's multi-issue
   pass is not what is measured.
7. **Stub coverage on a real repo**: routes the historical runs used that
   the stub lacks show up as UNKNOWN → invalid, iterate; the first sweep
   is partly fixture debugging.
8. **Toolchain**: the config names `./mvnw`; stage (2) and intake should
   never run it, but a seat that does hits Maven and the network and times
   out → invalid, not scored.
9. **Opus judging opus** on the opus row (separate session, no tools) —
   self-grading bias possible, unmeasured.
10. **Clock**: the SUT's date is later than the fixtures'. Harmless unless
    a seat reasons about dates.
