You are the QA seat for issue 5. The implementation has landed on the spec
branch. You wrote the test for scenario S1 from the contract and ran the
acceptance suite in your worktree.

Dispatch text:

    Test port: src/pricing.py
    Contract deviations: C2 added — `now` is the caller's clock (as built).
    Amendment list: none since the contract's last commit.

`docs/specs/5/spec.md`:

    # Spec #5 — Offer expiry enforcement

    ## Rules
    - **R4 · Expired offers don't count** (from AC-1) — an offer past
      `expires_at` is excluded from price calculation at read time.
      *The discount is a promise with a deadline; past it, the shopper pays list.*

    ## Scenarios
    - S1 — Given an offer expired yesterday, When the cart is priced, Then the
      offer is not applied.

    ## Open Questions
    (none)

`docs/specs/5/technical-spec.md` (as built):

    # Technical spec #5

    ## Contract
    - **C1 (R4, S1)** — `price(cart, now)` sums item costs; an item's offer
      discount is excluded once `expires_at < now`.
    - **C2 (R4)** — `now` is the caller's clock, never read from a store: the
      port stays pure (as built).
    - **Test port** — src/pricing.py
      `price(cart, now)` is the front door the acceptance suite drives: a cart
      is a list of `{"cost": int, "offer": {"discount": int, "expires_at": int} | None}`;
      the control point is the `now` argument, the observation point the return.

    ## §5 Port observability

    | scenario | observable |
    |---|---|
    | S1 | observable via `price(cart, now)` with `now` past `expires_at` |

Your test, `tests/acceptance/pricing/test_expiry.py`:

    def test_s1_expired_offer_is_not_applied(self):
        cart = [{"cost": 10, "offer": {"discount": 3, "expires_at": 1}}]
        self.assertEqual(price(cart, now=2), 10)   # C1: excluded once expires_at < now

The run:

    test_s1_expired_offer_is_not_applied ... FAIL
    AssertionError: 7 != 10
    ACCEPTANCE: RED — 1 failed: test_s1_expired_offer_is_not_applied
