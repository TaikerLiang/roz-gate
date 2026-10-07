#!/usr/bin/env bash
# C11 sandbox: C10's shape under a branch_template with {seq}. spec/paul/5/1
# still exists from a previous attempt whose spec CR was closed unmerged
# (state.json: PR 101 CLOSED); the issue wears ready-for-spec again. The
# cut must NOT stop: the template counts attempts, so the next pass cuts
# spec/paul/5/2 and leaves spec/paul/5/1 exactly as it was.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
printf -- '- branch_template: {type}/{user}/{n}/{seq}\n' >> CLAUDE.md
grep -q '^- branch_template: {type}/{user}/{n}/{seq}$' CLAUDE.md
mkdir -p .claude && printf '{"branch_user": "paul"}\n' > .claude/roz-gate.local.json
grep -q '"branch_user": "paul"' .claude/roz-gate.local.json
printf '.claude/roz-gate.local.json\n' >> .git/info/exclude
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "seed (branch_template)"
git checkout -qb spec/paul/5/1
mkdir -p docs/specs/5
printf '# Spec #5 — first attempt\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5 (first attempt)"
git checkout -q main
