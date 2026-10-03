**[intake] · summary**

**User story** — As a shopper, I want expired offers excluded, so I am never charged a stale discount.

**Acceptance criteria**
- An offer past `expires_at` is not applied.
- Expiry takes effect without a deploy.

**Proposed track** — `track: spec`: user-facing behaviour.

**Assumptions**
- Q3 · Cap: (a) 10k rows, per the recommendation.

**Contested points**
- Q2 · Access: you (a), Kai (b); the summary takes (b) — one reply flips it.

Right? Apply `status: ready-for-spec` — the label is the confirmation. Context and the decision trail are folded below.

<details><summary>Supplement — context and decision trail</summary>

**Context** — offers live in the `offers` table; pricing happens at checkout.

**Decision trail**
- 2026-08-20 · Q1 (a) — paul
- 2026-08-21 · Q2 (b) — Kai
- 2026-08-22 · Q2 leaned (a) — paul
- 2026-08-23 · Q3 unanswered
- 2026-08-24 · scope: offers only — paul
- 2026-08-20 · cache flush: none — Kai
- 2026-08-21 · deploy: not required — paul
- 2026-08-22 · rounding: unchanged — Kai
- 2026-08-23 · audit log: out of scope — paul
- 2026-08-24 · sibling story: bulk expiry — parked
- 2026-08-20 · track: spec proposed — product
- 2026-08-21 · footer confirmed — paul

</details>
