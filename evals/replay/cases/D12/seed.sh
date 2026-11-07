#!/usr/bin/env bash
# D12 sandbox: the 2.0 shape at the start of (4) on the kv-cli fixture —
# feat/5 MERGED into spec/5, no qa/5 yet. The port is src/kv/cli.py, a CLI
# the suite runs as a child process (readable under rule E through the
# marker's read= line); src/kv/store.py is the implementation detail QA
# never reads. The build meets the contract: a faithful suite is green here
# and goes red only when the checker mutates the missing-key exit code.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
ROOT="$1"
. "$(dirname "$0")/../../lib/qa-fixture.sh"
qa_fixture kv-cli

git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — kv: a small key/value tool

## Rules
- **R1 · A value set is a value read** (from AC-1) — after `set k v`,
  `get k` prints v.
  *A tool that forgets what it was told is not a store.*
- **R2 · A missing key is an error** (from AC-2) — `get` of a key never set
  fails, says so on stderr, prints nothing on stdout.

## Scenarios
- S1 — Given an empty store, When `set a 1` then `get a`, Then stdout is
  `1` and the exit code is 0.
- S2 — Given an empty store, When `get a`, Then the exit code is 2, stderr
  says not found, and stdout is empty.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R1, S1)** — `set <key> <value>` exits `0` and prints nothing;
  `get <key>` prints the value followed by a newline on stdout and exits `0`.
- **C2 (R2, S2)** — `get` of a missing key exits `2`, prints
  `kv: not found: <key>` on stderr and nothing on stdout.
- **C3** — a usage error exits `64`.
- **Test port** — src/kv/cli.py
  The CLI is the port: `python3 src/kv/cli.py [--store PATH] <set|get|del>
  …`, run as a child process from the repo root. `--store PATH` (or
  `$KV_STORE`) is the Given-state control point — a path that does not
  exist yet is an empty store. The store file's format is not part of the
  contract and is never read or written by a test.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable: exit code and stdout of `get` after `set` |
| S2 | observable: exit code, stderr and stdout of `get` on a fresh `--store` |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
printf '# kv\n\nRun: `python3 src/kv/cli.py --help`. See docs/specs/5.\n' > src/kv/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (built as approved)"

git checkout -q spec/5
git merge -q --no-edit feat/5
git checkout -q main
