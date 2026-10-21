#!/usr/bin/env bash
# Roz Gate — the worktree copy (#122), PostToolUse on Bash: layer 1, the prefilter.
#
# Runs after every Bash tool call in every repo where the plugin is enabled,
# so it must be near-zero cost: only a command that ran `git worktree add`
# pays for a python startup. The python side copies your gitignored local
# files (bin/roz-config's `worktree_copy`, default `.env`) from the main
# checkout into every loop worktree under `<git-common-dir>/roz-gate/wt/`
# that lacks them. It never blocks: the command has already run.
set -u

input=$(cat)

if ! printf '%s' "$input" | grep -qE 'worktree[[:space:]]+add'; then
  exit 0
fi

exec python3 "${BASH_SOURCE[0]%/*}/sync_worktree.py" <<EOF
$input
EOF
