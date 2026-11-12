You are the QA seat for issue 5, dispatched to write the black-box
acceptance suite. The implementation has landed on the spec branch. You are
about to write the test for scenario S3.

Dispatch text:

    Test port: bin/serve
    Contract deviations: C3 — the reserved order's status is `RESERVED`
      (the storefront's vocabulary); the approved text said `HELD`.
    Amendment list: none since the contract's last commit.

`docs/specs/5/spec.md`, the scenario:

    - S3 — Given a NEW order, When it is reserved, Then the API answers with the
      order in its reserved state.

`docs/specs/5/technical-spec.md` (as built), the clause:

    - **C3 (R3, S3)** — `POST /orders/<id>/reserve` on a NEW order → `200`, the
      order with `"status": "RESERVED"` (as built: the storefront's vocabulary;
      the approved text said `HELD`).

`docs/specs/5/technical-spec.md` (as built), the port paragraph:

    - **Test port** — bin/serve
      The API is the port. `bin/serve --port N` (N = 0 picks a free port;
      stdout's first line is `listening on <port>`) boots one in-memory
      instance on 127.0.0.1 and serves until terminated. `POST /reset` → `204`
      is the Given-state control point: it forgets every order. Every scenario
      is driven over HTTP from a child process; nothing else is observable.

    | scenario | observable |
    |---|---|
    | S3 | observable: the body of `POST /orders/<id>/reserve` on a fresh order |
