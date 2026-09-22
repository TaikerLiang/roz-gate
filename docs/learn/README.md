# docs/learn — the newcomer learning path

Human-facing (never loaded by the agent). Source of the interactive learner
page and its 50-question quiz. Paul's mandate 2026-09-21; rulings 2026-09-22.

## Files

- `quiz.json` — the bank: 50 questions across 8 modules (M1 loop → M8 how we
  work), each with `bg` (background), `q` (stem), `o` (options), `a` (answer
  index / indices / order), `why` (explanation), `src` (source pointer), plus
  `_meta.stages` (the loop's stage map, rendered from README § The loop in
  one page) and `_meta.glossary`.
- `../../images/loop-stage-map.svg` — the stage map (generated, not prose;
  the pages inline a theme-aware copy).
- `index.html`, `content.json` — the learner page and its data (phase 2;
  built by `tools/build_learn.py`, which also runs the real hooks to
  precompute the hook simulator's verdict table and checks every `src`
  pointer still resolves).

## Anti-leak rules (the bank must stay this way)

- **Length**: within an item, option lengths stay within ~30% of each other
  and the correct option is not systematically the longest — a wrong belief
  argued well is the L3 shape. The rationale lives in `why`, not in the
  correct option.
- **Position**: options are stored in a seeded-shuffled order (the JSON
  order is not a tell) and the learner page re-shuffles per attempt (seed =
  attempt id), including the presented sequence of ordering items. The
  review artifact shows JSON order with the answers marked; the learner
  page ships no answer key in its source (hashed answers; grading and
  results in the artifact's shared data, visible to all viewers).
- **Stage numbers** are never used bare: every mention carries its name
  inline, and the stage map is pinned above the questions.
- **Terms before taught**: a module may only use vocabulary an earlier
  module (or the glossary) introduced.

## Pass

≥ 80% overall AND ≥ 60% in every module AND ≥ 8 of the 12 L3 items.
