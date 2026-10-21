#!/usr/bin/env bash
# Roz Gate — the worktree copy (#122), PostToolUse on Bash: layer 1, the prefilter.
#
# Runs after every Bash tool call in every repo where the plugin is enabled,
# so it must be near-zero cost: only a command that mentions `worktree` pays
# for a python startup — the word alone, so `git worktree \<newline>add`
# (a shell continuation, raw in the hook's JSON) still escalates (codex
# review, PR #184). The python side copies your gitignored local
# files (bin/roz-config's `worktree_copy`, default `.env`) from the main
# checkout into every loop worktree under `<git-common-dir>/roz-gate/wt/`
# that lacks them. It never blocks: the command has already run.
set -u

input=$(cat)

if ! printf '%s' "$input" | grep -q 'worktree'; then
  exit 0
fi

exec python3 "${BASH_SOURCE[0]%/*}/sync_worktree.py" <<EOF
$input
EOF
