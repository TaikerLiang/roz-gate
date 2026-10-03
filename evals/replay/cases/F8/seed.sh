#!/usr/bin/env bash
# F8 sandbox: F3's plain gated repo, but the user is mid-edit on main — one
# tracked file modified, one untracked file — when the command runs. Issue
# #37: a scheduled patrol fires while the user works; the command's whole
# working surface must be a linked worktree. The runner pushes --all and
# leaves the checkout on main with these changes in place (they are never
# committed, so they are not on the remote).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
echo "demo — mid-edit, not committed" > src/app.txt
echo "scratch" > notes.txt
