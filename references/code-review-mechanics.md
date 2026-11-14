# Code review — the threads and the record

The inline-thread mechanics and the record of a code review (5), shared by
`next-stage` B5 (`references/next-stage-path-b.md`), C6
(`references/next-stage-path-c.md` — there the CR is the fast CR) and
patrol's `code-review` action. What the reviewer is dispatched with, and
each step's own exceptions, stay in the step that dispatches it.

- Post its findings as severity-graded inline threads on the implementation CR —
  THREAD-POST-INLINE, body starts
  `**[reviewer] · blocking|should-fix|nit|question**`, anchored to file:line.
  Rule/scenario IDs in a finding follow the citation convention (A3): first
  mention carries the ID's title and a link to its definition.
- **The record — posted last, even with zero findings**: one top-level
  CR-COMMENT opening with `**[reviewer] · code-review**`, carrying
  `reviewed-sha: <the CR head SHA reviewed>` on its own line and the finding
  count by severity (`blocking 1 · should-fix 0 · nit 2 · question 0`). It is
  the **record that the review ran**: zero threads because nobody reviewed
  is not zero findings (#95's lesson, now on the implementation side —
  #140 ruling 9). **Review-clean** is defined in `workflow.md` (5) and read
  everywhere else: the record present **and** its `reviewed-sha` equal to
  the CR head **and** zero open review threads. A head pushed after
  `reviewed-sha` without a re-check is a stale record — patrol's
  `code-review` action re-runs the review; its address-review re-check
  re-stamps `reviewed-sha` (COMMENT-EDIT) when the last thread resolves.
