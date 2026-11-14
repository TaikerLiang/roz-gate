#!/usr/bin/env bash
# C26 sandbox: F13's repo shape (the spec branch behind #5's CR, the local
# key `inbox_label: discuss`) plus the local key `patrol_issues_per_pass: 2`
# (#204). state.json: three `track: fast` issues at `status: ready-for-dev`
# (#6, #8, #9), each gate label applied by paul (`type` User) on a known
# date; #5 in-user-review and quiet; #7 a raw inbox idea. A pass may act on
# two of the three and must leave the third as seeded, with its wait in the
# report.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# What #6, #8 and #9 presuppose (#293): an HTTP client pinned below 3.2, a
# server whose responses carry no X-Request-Id, and the two ping routes. On
# a base without them a seat that stops (#213) is right, and the N is never
# reached.
mkdir -p src/server
printf 'httpclient==3.1\n' > requirements.lock
cat > src/server/app.py <<'PY'
"""The HTTP server: a route table and one handler."""

ROUTES = {
    "/ping": lambda: (200, "pong"),
    "/v0/ping": lambda: (200, "pong"),  # legacy
}


def handle(path, headers=None):
    """-> (status, response headers, body)."""
    route = ROUTES.get(path)
    if route is None:
        return 404, {}, "not found"
    status, body = route()
    return status, {}, body
PY
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "server: /ping, /v0/ping; HTTP client pinned at 3.1"
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
python3 "$1/bin/roz-config" patrol_issues_per_pass 2 > /dev/null
grep -q '"patrol_issues_per_pass": "2"' .claude/roz-gate.local.json
