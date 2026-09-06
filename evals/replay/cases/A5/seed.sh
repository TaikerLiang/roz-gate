#!/usr/bin/env bash
# A5 sandbox: fast-track repo — a fast/5 branch with the change, no spec
# branch anywhere (the case's point: the CR must resolve to fast/<n>).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb fast/5
echo "fixed banner" > src/banner.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "fast: fix banner typo (#5)"
git checkout -q main
