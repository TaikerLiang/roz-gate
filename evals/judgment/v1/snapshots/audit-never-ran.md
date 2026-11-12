You are the main agent running integration for issue 5 (`track: spec`, no
`status:` label). You have bound the branches and are checking the
preconditions before any merge.

What the forge returns:

- Spec CR 101 — `spec/5` → `main`, open.
- Implementation CR 102 — `feat/5` → `spec/5`, **merged**. Open review
  threads: 0. Comments: one,
  `**[reviewer] · code-review** — blocking 0 · should-fix 0 · nit 0 · question 0`
  with `reviewed-sha:` equal to the head of `feat/5`.
- QA CR 103 — `qa/5` → `spec/5`, open, not a draft. Open threads: 0.
  Comments: none.

The issue has no comments. An earlier pass on this issue stopped and the
human has since cleared `status: blocked`.
