#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the acceptance-suite guard.
#
# Runs on every file-writing tool call in every repo where the plugin is
# enabled, so it must be near-zero cost. The rule can only ever fire on a
# spec branch — one cheap git call decides that, and only there do we pay
# for a python startup plus the config read.
set -u

input=$(cat)

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
case "$branch" in
  spec/*) ;;
  *) exit 0 ;;
esac

exec python3 "${BASH_SOURCE[0]%/*}/guard-acceptance.py" <<EOF
$input
EOF
