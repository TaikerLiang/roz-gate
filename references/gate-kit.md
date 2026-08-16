# The gate kit

Assembly instructions for the **human-first review page** posted at the
two human gates of a spec-track issue. Spec track only — the fast track
has no spec artifacts to summarize. The kit is assembled **mechanically
by the main agent** — extraction and quotation only, no clarification
thinking, no synthesis, no judgment.

Two kits, both living as **one top-level comment on the spec CR, edited
in place** (COMMENT-EDIT — one canonical URL, no trail of stale copies;
never posted into a review thread):

- the **spec-gate kit** — posted when the spec CR opens (A7), updated by
  `/roz-gate:spec-answers` after each fold; read at `in-spec-review`.
- the **final-gate kit** — the same comment, extended at integration's
  green finalize; read at `in-user-review`.

## Binding rules (violating any of these deletes the kit's reason to exist)

1. **Quote, never paraphrase.** Every claim the human might act on is a
   verbatim excerpt. Paraphrase is where a summary silently replaces the
   artifact.
2. **Every claim links its exact line.** IDs follow the citation
   convention (title + definition link on first mention).
3. **No conclusions.** No "looks good", no top-line score, no verdict
   line, nothing that argues for approval. The kit directs attention;
   the human supplies the judgment.
4. **Exhaustive, or say so.** Every scenario and rule appears; where
   evidence is thin the kit says "no observable value — assertion only"
   rather than omitting the row. A kit complete-but-ugly is trustworthy;
   a uniformly pretty one is hiding something.
5. **State the blind spot.** The kit opens with one line: *"Generated
   from the same artifacts by the same team that wrote them — it can be
   wrong in the same direction they are. A map of where to look, not a
   verdict."*
6. **The CR diff stays primary.** The kit is a comment on the artifacts,
   never a replacement for opening them.
7. **The top is readable in 90 seconds** and contains everything needed
   to say *no*; everything else sits below the fold in
   `<details>` blocks.

## Sections

**1. Attention list** — the top of the kit: the highest-sorted 2–3 items
as named judgment calls, then the full list in spec order below the
fold. **Sort, never filter**, on computed properties only — never the
assembler's confidence, and the word "mechanical" never appears
("not flagged" is the honest weaker claim). Sort keys, in order:

1. rules with `(assumed)` provenance — decisions made in the holder's
   name that they never made;
2. rules whose spec text changed **after** the holder's ruling on them
   (re-folds, amendments — compare fold commits to thread dates);
3. rules/scenarios in coverage buckets *not covered* or *partial*;
4. rules carrying weak-assertion findings from the fidelity review (5q);
5. everything else, spec order, below the fold.

**2. Issue-delta** — instead of a summary (a summary of the spec, made
from the spec, by its authors, cannot reveal drift from the *ask*):
computed from provenance against the issue's acceptance criteria —
*"You asked for X (AC quoted verbatim). The spec commits to X, adds
these N rules you didn't ask for (`(from Q<j>)` / `(assumed)` — quoted),
and drops this one you did (AC with no covering rule)."*

**3. Decision ledger** — one entry per ruled question: the question
(one line), **the holder's answer quoted verbatim**, and **the fold** —
the spec text that resulted, quoted verbatim with its link. Anything the
folding agent wrote beyond the literal answer is marked distinctly:
*interpretation:* — the gap between what was said and what got written
is where expensive errors live, and it is invisible without adjacency.

**4. Evidence cards** *(final kit only — they need a verdict to exist)* —
one card per scenario, grouped into **four buckets** so absence of
evidence is a visible item: **covered · partial · not covered ·
cannot-be-covered-black-box** (bucket membership from the trace-marker
map; the last bucket names why). A card: the scenario sentence; the
assertion excerpt (verbatim, file:line); the **actual observed values
from the green run's captured output** where the test emits them —
"2 ghosts logged: `alice@…`, `bob@…`", never the expectation restated in
the observation slot; where nothing is emitted: *"value not emitted —
assertion only."* Target rendering where output allows: observed values
substituted inline into the scenario sentence, expected-vs-actual in
place, detail collapsed behind `<details>`.

**5. Since-you-approved diff** *(final kit only)* — the approved SHA is
stamped into the kit when Path B starts (the gate label is the approval
of `spec/<n>` at that commit). At finalize:
`git diff <approved-sha>..HEAD -- <specs_dir>/<n>/`, **each hunk
annotated with the thread or amendment that caused it**; if empty, say
so: *"the spec you approved is byte-identical."* Approval that can
silently expire is the most dangerous property a gate can have.

## Instrumentation

The package's success metric is the **artifact-change rate at gates**,
not the approval rate. Cheap day-one signal: when Path B starts, record
in the report whether the spec changed after the kit's last update —
a gate that only ever waves things through is decoration.
