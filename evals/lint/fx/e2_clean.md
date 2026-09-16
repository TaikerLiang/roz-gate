# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
  (open questions on the clock source: spec.md Q9 — the pointer A6 allows)

## §5 Port observability
| Scenario | Observability |
|---|---|
| S1 | observable; the open questions about TBD ports are threaded on the CR |
