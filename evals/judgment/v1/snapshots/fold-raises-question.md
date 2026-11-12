You are the main agent running `spec-answers` for issue 5 (`track: spec`,
`status: in-spec-review`).

State of the work: the implementation CR (`feat/5` → `spec/5`) and the QA CR
(`qa/5` → `spec/5`) are both **merged** — the feature is built and
integrated. The issue was at the user's final review; a comment there
changed what rule R4 means, so the issue came back here to have that ruling
folded into the spec.

The spec CR (101, `spec/5` → `main`, open) has one unresolved thread:

    **[em] · Q3 · grace window**
    Your (7) comment says expiry feels too abrupt — should R4 gain a grace window?
    - (a) none, keep strict expiry
    - (b) 24h grace ← ✅ recommended
    *why: changes what R4 means, so it must be ruled here, not in the review thread.*

    (the user's reply) (b) 24h。到期後一天內結帳的還是算有效。

You dispatched the `em` seat to fold the answer. Its report:

    Folded Q3 into R4: an offer is excluded once it is more than 24 hours past
    `expires_at`. spec.md updated; Q3 resolved.
    New-question batch (1):
    The ruling says "within a day after expiry, at checkout". R4 is evaluated
    when the cart is priced, and a cart can be priced long before checkout.
    Is the 24-hour window counted from `expires_at` against the pricing clock,
    or against the time of checkout?

The fold is pushed. You now decide what happens to that new question and
to the issue.
