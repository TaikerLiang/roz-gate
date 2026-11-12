You are the main agent running integration for issue 5 (`track: spec`, no
`status:` label). You have bound the branches and are checking the
preconditions before any merge.

What the forge returns:

- Spec CR 101 — `spec/5` → `main`, open.
- Implementation CR 102 — `feat/5` → `spec/5`, **merged**. Open review
  threads: 0. Comments: one,
  `**[reviewer] · code-review** — blocking 0 · should-fix 0 · nit 0 · question 0`
  with `reviewed-sha:` equal to the head of `feat/5`.
- QA CR 103 — `qa/5` → `spec/5`, **merged**. Open threads: 0. Comments: one,
  `**[reviewer] · fidelity** — 1/1 faithful. S1's test asserts the exclusion
  the scenario states; coverage map matches test-spec.md.`

The issue has no comments.
