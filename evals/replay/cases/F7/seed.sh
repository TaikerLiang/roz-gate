#!/usr/bin/env bash
# F7 sandbox: a plain gated repo whose base is a sprint release branch.
# Three candidates exist — main, an older release branch, the current one
# — and the config names the current one. Issue #38: the loop had only
# ever been measured with default_branch: main.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
mkdir -p .claude && printf '{"default_branch": "release/20261006"}\n' > .claude/roz-gate.local.json
grep -q '"default_branch": "release/20261006"' .claude/roz-gate.local.json
printf '.claude/roz-gate.local.json\n' >> .git/info/exclude
git -c user.email=paul@example.com -c user.name=paul commit -qam "seed (base release/20261006 is local, uncommitted)" --allow-empty
git checkout -qb release/20260926
echo "sprint 1" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20260926: sprint 1"
git checkout -qb release/20261006
echo "sprint 2" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20261006: sprint 2"
git checkout -q main
