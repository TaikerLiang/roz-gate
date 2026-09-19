--- [thread-post-inline] ---
**[em] · Q1 · Boundary instant**

When the pricing instant is exactly equal to `expires_at`, is the offer expired or still live?
- (a) Expired — `now >= expires_at` (offer is gone the moment its expiry is reached) ← ✅ recommended
- (b) Still live — `now > expires_at` (the expiry second itself still honours the offer)

*Off-by-one-second here decides whether S3 passes or fails and whether an "expires 23:59:59" campaign is honoured at 23:59:59; R4 currently assumes (a).*

--- [thread-post-inline] ---
**[em] · Q2 · Propagation latency (story-level)**

Does "takes effect without a deploy or cache flush" (AC-2) mean every pricing call must read the live `expires_at`, or is a short automatic staleness window acceptable?
- (a) Immediate — each pricing call decides against the current `offers` row; no staleness window ← ✅ recommended
- (b) Bounded — a TTL-based cache is allowed provided expiry is honoured within N seconds (N to be set, e.g. 60 s)

*AC-2 only forbids manual intervention, not staleness; (a) is what "never charged a stale discount" literally requires, but it constrains the implementer's caching options and drives M2. R7 assumes (a).*

*If your decision changes the user story, I will mirror a note to issue #5.*

--- [thread-post-inline] ---
**[em] · Q3 · Mid-checkout expiry (story-level)**

If an offer expires between the shopper viewing the cart total and the final charge, is the charge recalculated without the offer, or is the viewed price honoured?
- (a) Recalculate at the final charge; shopper sees the new total before being charged ← ✅ recommended
- (b) Honour the price the shopper last saw, within a short grace window (length to be set)

*Option (b) is a deliberate, bounded exception to AC-1 that some businesses want for conversion reasons; the story as written implies (a). R2/R3 and S6 assume (a).*

*If your decision changes the user story, I will mirror a note to issue #5.*

--- [thread-post-inline] ---
**[em] · Q4 · Null expires_at**

How should an offer with no `expires_at` value be treated by pricing?
- (a) Never expires — unaffected by this feature ← ✅ recommended
- (b) Treated as invalid and excluded from pricing

*Column nullability has not been checked; if NULL is impossible this is moot, but if it is possible the two readings produce opposite cart totals. R5 and S4 assume (a).*

--- [thread-post-inline] ---
**[product] · Q5 · Applying expired code**

When a shopper attempts to add or apply an already-expired offer to their cart, is it accepted and silently excluded at pricing, or rejected at apply time?
- (a) Accepted; excluded at every pricing per R9 — apply-time rejection is a separate story ← ✅ recommended
- (b) Rejected at apply time with an error

*R9 and the out-of-scope list point to (a), but a shopper who "applies" a code and sees no discount with no feedback is the most likely support ticket this feature creates; naming the choice keeps S1/S12 and any future apply-time story consistent.*

--- [thread-post-inline] ---
**[product] · Q6 · Exclusion reason visible**

Should the pricing result let the checkout caller distinguish "offer excluded because expired" from "offer does not exist", or are they indistinguishable as R1 states?
- (a) Indistinguishable — the offer is simply absent from the applied list (R1/R9 as written) ← ✅ recommended
- (b) The result carries an excluded-for-expiry marker so the UI can explain the changed total

*The AC does not ask for it and messaging is out of scope, but S6/S12 produce a total that silently drops a discount the shopper saw; ruling now avoids a contract change later if (b) is wanted.*

--- [thread-post-inline] ---
**[implementer] · Q7 · Clock source**

Which clock does `now` come from — the DB's or the API caller's?
- (a) API caller passes it ← ✅ recommended
- (b) DB `NOW()`

*why: determines whether expiry is testable with a frozen clock.*

--- [pr-comment] ---
## Spec-gate kit — #5 Offer expiry enforcement

*Generated from the same artifacts by the same team that wrote them — it can be wrong in the same direction they are. A map of where to look, not a verdict.*

Artifacts: [spec.md](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md) · [technical-spec.md](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/technical-spec.md) · kit SHA `cae89841cc4b72eee0fbfb64b8a897ac3634b7c6`

### Attention list — top 3

1. **8 of 10 rules are `(assumed)`** — decisions made in your name that you never made. Each has a thread: [R3 · Evaluated at pricing instant](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L41) → Q7; [R4 · Boundary is exclusive](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L44) → Q1; [R5 · Null expiry never expires](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L47) → Q4; [R7 · Propagation is immediate](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L53) → Q2; [R8 · Expiry updates honoured both ways](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L56), [R9 · Silent exclusion, no error](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L59) → Q5/Q6; [R10 · Timestamps compared in UTC](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L62) — no thread asks about R8 or R10.
2. **Two `(assumed-empirical: …)` facts nobody measured** — [R5](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L48): "*schema may not permit NULL, in which case this rule is vacuous*"; [R6 · No deploy, no flush](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L51): "*any cache of offer rows in the checkout path would violate this unless expiry is checked on the live value*". Your action: order a measurement or accept the risk.
3. **§5 observability walk covers 1 of 12 scenarios** — [technical-spec.md §5](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/technical-spec.md#L6) lists only `S1 | observable`; S2–S12 have no row. No limitation rows to countersign, but also no evidence the port can drive them. The contract has no `G<k>`/`C<k>` anchors — the single clause is [`price(cart, now)` excludes offers with `expires_at < now`](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/technical-spec.md#L4), which uses `<` where [R4](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L45) says `now >= expires_at` — the two documents disagree on the boundary (Q1).

<details><summary>Full attention list (spec order)</summary>

| Item | Provenance / property | Thread |
|---|---|---|
| [R1 · Expired offers excluded](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L35) | from AC-1 | — |
| [R2 · Applies to every calculation](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L38) | from AC-1 | — |
| [R3 · Evaluated at pricing instant](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L41) | (assumed) | Q7 |
| [R4 · Boundary is exclusive](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L44) | (assumed) | Q1 |
| [R5 · Null expiry never expires](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L47) | (assumed) + (assumed-empirical: schema may not permit NULL) | Q4 |
| [R6 · No deploy, no flush](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L50) | from AC-2 + (assumed-empirical: cache in checkout path) | Q2 |
| [R7 · Propagation is immediate](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L53) | (assumed) | Q2 |
| [R8 · Expiry updates honoured both ways](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L56) | (assumed) | none |
| [R9 · Silent exclusion, no error](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L59) | (assumed) | Q5, Q6 |
| [R10 · Timestamps compared in UTC](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L62) | (assumed) | none |
| [S1](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L67) | §5: observable | — |
| [S2](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L75)–[S12](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L142) | §5: no row | — |

</details>

### Issue-delta

You asked for:
- AC-1: "*An offer past its `expires_at` is not applied to any price calculation.*" → covered by [R1](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L35), [R2](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L38).
- AC-2: "*Expiry takes effect without a deploy or cache flush.*" → covered by [R6](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L50).

The spec adds **8 rules you didn't ask for** (all `(assumed)`): R3, R4, R5, R7, R8, R9, R10 — quoted in the table above — plus the boundary/clock/null/staleness/mid-checkout/apply-time/marker questions Q1–Q7. No AC is dropped.

### Decision ledger

_(empty — intake carried no rulings.)_

### Open threads
Q1 · Boundary instant · Q2 · Propagation latency (story-level) · Q3 · Mid-checkout expiry (story-level) · Q4 · Null expires_at · Q5 · Applying expired code · Q6 · Exclusion reason visible · Q7 · Clock source — all inline on this CR at [spec.md → Open Questions](https://github.com/acme/demo/blob/cae89841cc4b72eee0fbfb64b8a897ac3634b7c6/docs/specs/5/spec.md#L160).
