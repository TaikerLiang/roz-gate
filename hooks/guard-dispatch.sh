#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter for the seat-dispatch guard (#382).
#
# Runs on every Agent / Task call in every repo where the plugin is enabled.
# Rule L judges only a seat's dispatch: a `roz-gate:<seat>` type, the
# `implementer` default, or an agent the `### Roz Gate personas` block maps
# to a seat. A call that names neither, made where no personas block sits in
# CLAUDE.md / CLAUDE.local.md (this toplevel, the main checkout), is allowed
# here with no python start — so a broken python3 never blocks the scanner
# or a general-purpose sub-agent outside the loop.
set -u

input=$(cat)

case $input in
  *subagent_type*) ;;
  *) exit 0 ;;
esac
case $input in
  *roz-gate:* | *'"implementer"'*) ;;
  *)
    top=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
    common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || common=
    main=
    if [ -n "$common" ]; then   # config_block.main_checkout(): core.worktree, else the parent
      main=${common%/*}
      if wt=$(git config --file "$common/config" core.worktree 2>/dev/null); then
        case $wt in /*) main=$wt ;; *) main=$common/$wt ;; esac
      fi
    fi
    found=
    for f in "$top/CLAUDE.md" "$top/CLAUDE.local.md" \
             ${main:+"$main/CLAUDE.md" "$main/CLAUDE.local.md"}; do
      if [ -f "$f" ] && grep -qE '^###[[:space:]]+(Roz Gate|Gated Loop) personas' "$f"; then
        found=1
        break
      fi
    done
    [ -n "$found" ] || exit 0
    ;;
esac

. "${BASH_SOURCE[0]%/*}/run-guard.sh"   # fails closed from here on (#281)
run_guard guard-dispatch guard_dispatch.py <<EOF
$input
EOF
