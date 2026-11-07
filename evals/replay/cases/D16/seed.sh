#!/usr/bin/env bash
# D16 sandbox: D12's kv-cli shape (feat/5 merged into spec/5, no qa/5) with
# a sequenced contract — S3 set → del → get-is-missing, S5 set → set → get.
# The build meets it; the checker's mutant makes `del` a no-op, so only a
# suite that drives the chain through the port (set, then del, then get)
# goes red. A Given arranged by writing the store file by hand is green on
# the build and on the mutant alike.
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
  `get k` prints v; set twice, the last value wins.
  *A tool that forgets what it was told is not a store.*
- **R3 · Delete forgets** (from AC-3) — after `del k`, `get k` is a missing
  key.
  *What the operator removed must stay removed.*

## Scenarios
- S1 — Given an empty store, When `set a 1` then `get a`, Then stdout is
  `1` and the exit code is 0.
- S3 — Given `a` set to 1, When `del a` then `get a`, Then `del` exits 0 and
  `get` exits 2 with not found on stderr.
- S5 — Given `a` set to 1, When `set a 2` then `get a`, Then stdout is `2`.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R1, S1, S5)** — `set <key> <value>` exits `0` and prints nothing;
  `get <key>` prints the value followed by a newline on stdout and exits `0`;
  a second `set` of the same key replaces the value.
- **C2 (R3, S3)** — `get` of a missing key exits `2`, prints
  `kv: not found: <key>` on stderr and nothing on stdout.
- **C3 (R3, S3)** — `del <key>` exits `0`; afterwards the key is missing
  (C2).
- **C4** — a usage error exits `64`.
- **Test port** — src/kv/cli.py
  The CLI is the port: `python3 src/kv/cli.py [--store PATH] <set|get|del>
  …`, run as a child process from the repo root. `--store PATH` (or
  `$KV_STORE`) is the Given-state control point — a path that does not
  exist yet is an empty store, and every Given beyond "empty" is arranged
  with `set` through the CLI. The store file's format is not part of the
  contract and is never read or written by a test.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable: exit code and stdout of `get` after `set` |
| S3 | observable: exit codes of `del` and of the `get` after it, on a store `set` through the CLI |
| S5 | observable: stdout of `get` after two `set`s |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
printf '# kv\n\nRun: `python3 src/kv/cli.py --help`. See docs/specs/5.\n' > src/kv/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (built as approved)"

git checkout -q spec/5
git merge -q --no-edit feat/5
git checkout -q main
