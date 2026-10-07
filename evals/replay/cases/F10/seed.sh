#!/usr/bin/env bash
# F10 sandbox: F7's repo (base = a sprint release branch, main and an older
# release branch also exist) plus a branch_template in the block —
# `{type}/{user}/{n}/{seq}` — and branch_user in the local file. Issue #5
# wears `type: fix` (state.json): the tempting wrong render for the SPEC
# branch is `fix/paul/5/1`; the right one is `spec/paul/5/1`. Issue #75:
# every seed before this one ran the default names.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
printf -- '- branch_template: {type}/{user}/{n}/{seq}\n' >> CLAUDE.md
grep -q '^- branch_template: {type}/{user}/{n}/{seq}$' CLAUDE.md
mkdir -p .claude && printf '{"default_branch": "release/20261006", "branch_user": "paul"}\n' > .claude/roz-gate.local.json
grep -q '"branch_user": "paul"' .claude/roz-gate.local.json
printf '.claude/roz-gate.local.json\n' >> .git/info/exclude
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "seed (branch_template; base release/20261006 is local, uncommitted)"
git checkout -qb release/20260926
echo "sprint 1" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20260926: sprint 1"
git checkout -qb release/20261006
echo "sprint 2" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20261006: sprint 2"
git checkout -q main
