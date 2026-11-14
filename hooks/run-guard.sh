# Roz Gate enforcement — sourced by the three PreToolUse guard shims once
# their prefilter has decided the call needs the Python side (#281).
#
# A guard that cannot finish its check blocks the call, never lets it
# through: Claude Code reads any exit but 2 as "allow" (exit 1 is a
# non-blocking error), so a missing python3 (127), an interpreter that
# cannot start (126), an uncaught exception (1) or a signal would each
# have been a silent pass. The guards themselves exit only 0 (allow) or
# 2 (deny); anything else is a tool failure, and the message says so —
# not a protocol block.

# run_guard <hook name> <script beside this file>; the payload is on stdin.
run_guard() {
  local name=$1 script=$2 rc
  if ! command -v python3 >/dev/null 2>&1; then
    echo "roz-gate $name: python3 not found on PATH — the guard could not check this call, so it is blocked. This is a tool failure, not a protocol block: install python3 (or fix PATH) and retry." >&2
    exit 2
  fi
  python3 "${BASH_SOURCE[0]%/*}/$script"
  rc=$?
  case $rc in 0|2) exit "$rc" ;; esac
  echo "roz-gate $name: the guard could not start or did not finish its check (exit $rc), so the call is blocked. This is a tool failure, not a protocol block — the lines above say what failed (hooks/$script); fix it and retry." >&2
  exit 2
}
