#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the acceptance-suite guard.
#
# Runs on every file-writing tool call in every repo where the plugin is
# enabled, so it must be near-zero cost. The rule can only ever fire on a
# spec branch — one cheap git call decides that, and only there do we pay
# for a python startup plus the config read. A clone whose local file
# (.claude/roz-gate.local.json, bin/roz-config's) sets `branch_template`
# (references/branch-names.md, #165) may name its spec branch anything, so
# there the one extra grep hands every branch to python, which matches HEAD
# against the rendered template. The file is read in this toplevel or in
# the main checkout (core.worktree when set, else the parent of the common
# git dir: the file is untracked and absent in a linked worktree), the
# lookup hooks/config_block.py does for the block (#94).
set -u

input=$(cat)

out=$(git rev-parse --abbrev-ref HEAD --show-toplevel 2>/dev/null) || exit 0
branch=${out%%$'\n'*}
top=${out#*$'\n'}
case "$branch" in
  spec/*) ;;
  *) gitdir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
       || gitdir=$(git rev-parse --git-common-dir 2>/dev/null)
     # core.worktree: the one hint a separate git dir leaves (config_block.py).
     if wt=$(git config --file "$gitdir/config" core.worktree 2>/dev/null) && [ -n "$wt" ]; then
       case "$wt" in /*) main=$wt ;; *) main="$gitdir/$wt" ;; esac
     else
       main="$gitdir/.."
     fi
     grep -qs '"branch_template" *: *"[^"]' "$top/.claude/roz-gate.local.json" \
       "$main/.claude/roz-gate.local.json" || exit 0 ;;
esac

exec python3 "${BASH_SOURCE[0]%/*}/guard_acceptance.py" <<EOF
$input
EOF
