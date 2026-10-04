#!/usr/bin/env bash
# C10 sandbox: spec/5 still exists from a previous attempt whose spec CR was
# closed unmerged (state.json: PR 101 CLOSED); the issue wears ready-for-spec
# again. The cut must STOP and hand the human the delete command.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5 — first attempt\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5 (first attempt)"
git checkout -q main
