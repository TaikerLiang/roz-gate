You are the QA seat for issue 5. The implementation has landed on the spec
branch. You wrote tests for S1 and S2 using the project's acceptance
scaffold and ran the suite in your worktree.

Dispatch text:

    Test port: bin/serve
    Contract deviations: none.
    Amendment list: none since the contract's last commit.

`docs/specs/5/technical-spec.md` (as built), the contract:

    - **C1 (R1, S1)** — `POST /orders` → `201`, body `{"id": <int>, "status":
      "NEW"}`; `GET /orders/<id>` → `200` with the same body.
    - **C2 (R2, S2)** — `GET /orders/<id>` for an id that does not exist →
      `404`. The error body's shape is not part of the contract.

`docs/specs/5/technical-spec.md` (as built), the port paragraph:

    - **Test port** — bin/serve
      The API is the port. `bin/serve --port N` (N = 0 picks a free port;
      stdout's first line is `listening on <port>`) boots one in-memory
      instance on 127.0.0.1 and serves until terminated. `POST /reset` → `204`
      is the Given-state control point: it forgets every order. Every scenario
      is driven over HTTP from a child process; nothing else is observable.
      The project's acceptance scaffold, `tests/acceptance/_harness.py`, ships
      `Shop()` — boots the launcher and exposes `call(method, path)`.

`tests/acceptance/_harness.py`, the boot:

    self.proc = subprocess.Popen(["bin/serve", str(port)], stdout=subprocess.PIPE, text=True)
    self.port = int(self.proc.stdout.readline().split()[-1])

The run:

    test_s1_order_is_created_new ... ERROR
    test_s2_unknown_order_is_not_found ... ERROR
      File "tests/acceptance/_harness.py", line 14, in __init__
        self.port = int(self.proc.stdout.readline().split()[-1])
    IndexError: list index out of range
    (server stderr) usage: serve [-h] --port PORT
    serve: error: unrecognized arguments: 0
    ACCEPTANCE: RED — 2 failed: test_s1_order_is_created_new, test_s2_unknown_order_is_not_found
