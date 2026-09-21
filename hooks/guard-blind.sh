#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the blindness guard.
#
# Runs on every Bash / Read / Glob / Grep call in every repo where the
# plugin is enabled, so it must be near-zero cost. Rule E can only ever
# fire while a fidelity dispatch is in flight, and the dispatching command
# says so by writing a marker file under the repo's git dir; one cheap
# git call plus one stat decides it, and only then do we pay for a python
# startup.
set -u

input=$(cat)

gitdir=$(git rev-parse --absolute-git-dir 2>/dev/null) || exit 0
[ -f "$gitdir/roz-gate/fidelity-dispatch" ] || exit 0

exec python3 "${BASH_SOURCE[0]%/*}/guard_blind.py" <<EOF
$input
EOF
