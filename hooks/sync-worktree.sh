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

# Without python3, or when the copy itself fails (#281), nothing was copied:
# say so to the agent — additionalContext, the channel the copy reports on —
# with the way back. Still never a block: the command has already run.
rc=127
if command -v python3 >/dev/null 2>&1; then
  python3 "${BASH_SOURCE[0]%/*}/sync_worktree.py" <<EOF
$input
EOF
  rc=$?
fi
[ "$rc" = 0 ] && exit 0
printf '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' \
  "[roz-gate] worktree_copy did not run (python3 missing, or the copy failed: exit $rc) — no file was copied into the loop worktrees. Install python3, then run any git worktree command (git worktree list) to copy them, or copy the worktree_copy files (default .env) from the main checkout by hand."
exit 0
