# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.

## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
