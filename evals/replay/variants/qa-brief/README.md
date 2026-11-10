# QA-brief variants

Frozen rewrites of `references/qa-brief.md` for the instruction-regression
benchmark (#199). A **variant** is the whole brief as the QA seat would
receive it — one file, swapped in for `references/qa-brief.md` and nothing
else — so a replay case can measure what the seat does under each wording
on the same fixture, the same command and the same model
(`evals/replay/README.md` § Variants).

| variant | file | what it is | sha256 (frozen 2026-11-07) |
|---|---|---|---|
| **A** | `references/qa-brief.md` (the checkout's) | the brief as shipped — never copied here, so there is one A | `ddcf3547db029d9c6bbdcfa4ffb798bbd6b394b59d5226d6da85fa38ceb00a45` |
| **B** | `B.md` | the STE *rule* rewrite from #139 (2026-11-06): the blindness paragraph split into a list, the red's two dispositions as separate sentences | `ae6003c95d5dd57f188f8cdf73f13119465ef095b45f1855958dcd5a194464ce` |
| **C** | `C.md` | the STE *full* rewrite from #139 (2026-11-06): B plus lexical substitution in the same two sections — with one sentence corrected before freezing: "after the implementation is merged" → "after the implementation lands on `<spec-branch>`" (QA is stage (4); the merge is after (7); the drift was not STE's and would have been a confound) | `5fd7c7faba77a132958ceb7686f703a9b94d4b165e5a220d9eb3131e478ec5f1` |
| **A0** | `A0.md` | the shipped brief **before #261** (post-#243, `main` at aa72c3d), frozen 2026-11-10 as #261's control: A vs A0 differs only by the blindness rule's split into **Invariant.** / **Allowed.** / **Forbidden.** — the same permissions, the same semantics (#261 rulings) | `f015f592ad6646425009bd41f11f273fc9e26ef9252b9390c1a35e945cf4b026` |
| **A1** | `A1.md` | the shipped brief **after #261, before #262** (`main` at a52dce8), frozen 2026-11-10 as #262's control: A1 vs A2 differs only by step zero's questioned → drivable → undrivable → wait chain as four numbered decisions | `2b2c46350e42419e73e591f18e0eaefe2541a1689bc42967551f4d623f825708` |
| **A2** | `A2.md` | the shipped brief **after #262** — byte-identical to `references/qa-brief.md` at the #262 brief commit, frozen 2026-11-10 as #262's treatment so a later change to A keeps the A1 vs A2 comparison | `cebb5721e003b60fd1e40f1aae9837d87893a10d2fa95a81a84dd091198e55c9` |

Facts to keep in view when reading results: the headings and every
backticked literal are identical across A, B and C; A→B changes 48 lines
and B→C 38, all inside *Inputs — and the blindness rule* and *Run the suite
— and what a red means*; STE lint counts 38 → 31 → 31, so C is B plus
lexical substitution, not a further structural pass.

## How a variant is used

```sh
python3 evals/replay/run_replay.py --sut haiku55 --k 1 --variant B D10   # one case under B
```

The runner copies the plugin root to a temp dir (no `.git`, no `evals/`),
replaces only `references/qa-brief.md` there and runs the session with that
dir as `--plugin-dir`; the checkout is never written. Every `result.json`
records `variant` and `brief_sha256` — the hash of the file **read back from
the plugin dir the session ran** — beside `plugin_sha` and `case_fp`. The
report counts a run whose hash differs from the variant file's current one
as `stale`, exactly as it does a fingerprint mismatch; so a later edit to
any of the three files retires the runs made under the old text instead of
leaving them current. The QA persona (`agents/qa.md`) is constant across
variants and stamped as `persona_sha256` (#267): editing it retires every
variant's runs of a `"seats": ["qa"]` case alike. Runs under a variant live in
`report/<sut>/<case>@<V>/`; A's stay in `report/<sut>/<case>/`.

## Adding a variant

Drop `<V>.md` beside this file — one capital letter (or `A<n>`, a frozen
earlier A), the whole brief — and
add its row above with the hash (`shasum -a 256 <V>.md`). Nothing else
registers it: the runner finds the file by name and records the hash it
loaded. A variant is frozen once a run has been recorded under it; a
changed text is a new letter, never an edit (the old runs would go stale
and the comparison would lose its control).

The variants are written **blind** — the author sees the brief, never a
case (#199 ruling 3) — and the cases are frozen before the first A/B/C
comparison; nothing in this directory is tuned on results.
