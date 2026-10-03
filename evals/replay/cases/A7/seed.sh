#!/usr/bin/env bash
# A7 sandbox: fast-track repo whose fast/5 is already merged into main by
# the human (the (7) signature). The forge did not close the issue — #41's
# GitLab symptom; patrol must finish it.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb fast/5
echo "fixed banner" > src/banner.txt
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "fast: fix banner typo (#5)"
git checkout -q main
git merge -q --no-ff --no-edit fast/5
# #6: spec/6 merged too; GitHub closed the issue on `Closes #6` but its
# loop labels stayed on — the other shape the close-out must finish.
git checkout -qb spec/6
mkdir -p docs/specs/6 && echo "# Spec #6" > docs/specs/6/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #6"
git checkout -q main
git merge -q --no-ff --no-edit spec/6
