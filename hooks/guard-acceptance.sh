#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the acceptance-suite guard.
#
# Runs on every file-writing tool call in every repo where the plugin is
# enabled, so it must be near-zero cost. The rule can only ever fire on a
# spec branch — one cheap git call decides that, and only there do we pay
# for a python startup plus the config read. A repo whose block sets
# `branch_template` (references/branch-names.md) may name its spec branch
# anything, so there the one extra grep hands every branch to python,
# which matches HEAD against the rendered template.
set -u

input=$(cat)

out=$(git rev-parse --abbrev-ref HEAD --show-toplevel 2>/dev/null) || exit 0
branch=${out%%$'\n'*}
top=${out#*$'\n'}
case "$branch" in
  spec/*) ;;
  *) grep -qs '^- *branch_template:' "$top/CLAUDE.md" || exit 0 ;;
esac

exec python3 "${BASH_SOURCE[0]%/*}/guard_acceptance.py" <<EOF
$input
EOF
