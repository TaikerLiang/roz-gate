#!/usr/bin/env bash
# C7 sandbox: the config names a release branch the remote does not have
# (a typo, or a retired sprint). The remote holds main and an older
# release branch; neither is the base. The cut must STOP, not improvise.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak 's|^- default_branch: main$|- default_branch: release/20261013|' CLAUDE.md
rm CLAUDE.md.bak
grep -q '^- default_branch: release/20261013$' CLAUDE.md
git -c user.email=paul@example.com -c user.name=paul commit -qam "config: base is release/20261013"
git checkout -qb release/20261006
echo "sprint 2" > src/sprint.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "release/20261006: sprint 2"
git checkout -q main
