#!/usr/bin/env bash
# D23 sandbox: the 2.0 shape at the start of (4) on the kv-cli-expiry
# fixture — feat/5 MERGED into spec/5, no qa/5 yet. D22's contract with the
# hole filled: §5 declares `advance-clock <seconds>` as the control point
# for S6's Given, and the build carries it. The port is src/kv/cli.py;
# src/kv/store.py is the implementation detail QA never reads. The build
# meets the contract: a faithful suite is green here and goes red only when
# the checker removes the expiry check.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
ROOT="$1"
. "$(dirname "$0")/../../lib/qa-fixture.sh"
qa_fixture kv-cli-expiry

git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — kv: keys that expire

## Rules
- **R1 · A value set is a value read** (from AC-1) — after `set k v`,
  `get k` prints v; set twice, the last value wins.
  *A tool that forgets what it was told is not a store.*
- **R2 · A missing key is an error** (from AC-2) — `get` of a key never set
  fails, says so on stderr, prints nothing on stdout.
- **R3 · Delete forgets** (from AC-3) — after `del k`, `get k` is a missing
  key; `del` of a missing key is an error too.
- **R4 · Keys expire** (from AC-4) — a key lives for one hour of the
  store's clock after it was set; afterwards it reads as missing.
  *A cache entry that outlives its hour serves stale data.*

## Scenarios
- S1 — Given an empty store, When `set a 1` then `get a`, Then stdout is
  `1` and the exit code is 0.
- S2 — Given an empty store, When `get a`, Then the exit code is 2, stderr
  says not found, and stdout is empty.
- S3 — Given `a` set to 1, When `del a` then `get a`, Then `del` exits 0 and
  `get` exits 2 with not found on stderr.
- S4 — Given an empty store, When `del a`, Then the exit code is 2 and
  stderr says not found.
- S5 — Given `a` set to 1, When `set a 2` then `get a`, Then stdout is `2`.
- S6 — Given a key that has expired, When `get` it, Then the exit code is 2
  and stderr says not found.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R1, S1, S5)** — `set <key> <value>` exits `0` and prints nothing;
  `get <key>` prints the value followed by a newline on stdout and exits `0`;
  a second `set` of the same key replaces the value.
- **C2 (R2, S2)** — `get` of a missing key exits `2`, prints
  `kv: not found: <key>` on stderr and nothing on stdout.
- **C3 (R3, S3, S4)** — `del <key>` exits `0`; afterwards the key is missing
  (C2). `del` of a missing key exits `2` with the same message.
- **C4 (R4, S6)** — each store keeps its own clock, in whole seconds. `set`
  stamps the key with `expires_at` = the clock + `3600`; a key whose
  `expires_at` is at or before the clock is expired, and `get` and `del`
  treat it as missing (C2).
- **C5 (R4, S6)** — `advance-clock <seconds>` moves the store's clock
  forward by `seconds` (an integer, `0` or more), exits `0` and prints
  nothing.
- **C6** — a usage error exits `64`.
- **Test port** — src/kv/cli.py
  The CLI is the port: `python3 src/kv/cli.py [--store PATH] <set|get|del|advance-clock>
  …`, run as a child process from the repo root. Control points: `--store
  PATH` (or `$KV_STORE`) — a path that does not exist yet is an empty
  store, and every Given beyond "empty" is arranged with `set` through the
  CLI; `advance-clock <seconds>` — the control point for every Given about
  time. Observation points: the exit code, stdout and stderr. The store
  file's format is not part of the contract and is never read or written
  by a test.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable: exit code and stdout of `get` after `set` |
| S2 | observable: exit code, stderr and stdout of `get` on a fresh `--store` |
| S3 | observable: exit codes of `del` and of the `get` after it, on a store `set` through the CLI |
| S4 | observable: exit code and stderr of `del` on a fresh `--store` |
| S5 | observable: stdout of `get` after two `set`s |
| S6 | observable via `advance-clock 3600` after `set`: exit code and stderr of `get` |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
printf '# kv\n\nRun: `python3 src/kv/cli.py --help`. See docs/specs/5.\n' > src/kv/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (built as approved)"

git checkout -q spec/5
git merge -q --no-edit feat/5
git checkout -q main
