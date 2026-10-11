#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the acceptance-suite guard.
#
# Runs on every file-writing tool call in every repo where the plugin is
# enabled, so it must be near-zero cost. The rule can only ever fire on a
# spec branch — one cheap git call decides that, and only there do we pay
# for a python startup plus the config read. A repo whose block sets
# `branch_template` (references/branch-names.md) may name its spec branch
# anything, so there the one extra grep hands every branch to python,
# which matches HEAD against the rendered template. The block has two
# homes — CLAUDE.md, else CLAUDE.local.md — in this toplevel or in the main
# checkout (the parent of the common git dir: CLAUDE.local.md is untracked
# and absent in a linked worktree); hooks/config_block.py is the python
# side of the same lookup (#94).
set -u

input=$(cat)

out=$(git rev-parse --abbrev-ref HEAD --show-toplevel 2>/dev/null) || exit 0
branch=${out%%$'\n'*}
top=${out#*$'\n'}
case "$branch" in
  spec/*) ;;
  *) main=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
       || main=$(git rev-parse --git-common-dir 2>/dev/null)
     grep -qs '^- *branch_template:' "$top/CLAUDE.md" "$top/CLAUDE.local.md" \
       "$main/../CLAUDE.md" "$main/../CLAUDE.local.md" || exit 0 ;;
esac

exec python3 "${BASH_SOURCE[0]%/*}/guard_acceptance.py" <<EOF
$input
EOF
