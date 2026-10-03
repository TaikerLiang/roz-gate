#!/usr/bin/env bash
# F7 sandbox: a plain gated repo whose base is a sprint release branch.
# Three candidates exist — main, an older release branch, the current one
# — and the config names the current one. Issue #38: the loop had only
# ever been measured with default_branch: main.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak 's|^- default_branch: main$|- default_branch: release/20261006|' CLAUDE.md
rm CLAUDE.md.bak
grep -q '^- default_branch: release/20261006$' CLAUDE.md
git -c user.email=paul@example.com -c user.name=paul commit -qam "config: base is release/20261006"
git checkout -qb release/20260926
echo "sprint 1" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20260926: sprint 1"
git checkout -qb release/20261006
echo "sprint 2" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20261006: sprint 2"
git checkout -q main
