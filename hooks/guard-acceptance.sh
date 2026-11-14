#!/usr/bin/env bash
# Roz Gate enforcement — layer 1 of the acceptance-suite guard: a thin
# wrapper since #277. The rule is about the edited file's worktree — its
# branch, its config block, its local file (.claude/roz-gate.local.json),
# here or in its main checkout — never the session's cwd: the loop runs
# from the main checkout and edits <common-dir>/roz-gate/wt/spec/<n>/… by
# absolute path, and the old cwd-based prefilter let every such edit
# through. Reading the payload's path, walking to the nearest existing
# directory and resolving the config are done once, in guard_acceptance.py,
# rather than twice in two languages that must agree. So with no prefilter,
# a missing python3 blocks every edit, everywhere the plugin is enabled —
# the visible direction, ruled on #281.
set -u
. "${BASH_SOURCE[0]%/*}/run-guard.sh"   # fails closed (#281)
run_guard guard-acceptance guard_acceptance.py
