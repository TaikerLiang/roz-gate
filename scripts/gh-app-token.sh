#!/usr/bin/env bash
# Mint a short-lived GitHub App installation token.
#
#   gh-app-token.sh <app-id> <private-key.pem> [owner/repo]
#
# Prints the token on stdout — pass it per invocation (GH_TOKEN=… gh …),
# never export it. With owner/repo, resolves that repo's installation;
# without, uses the App's first (only) installation.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <app-id> <private-key.pem> [owner/repo]" >&2
  exit 64
fi
APP_ID=$1 KEY=$2 REPO=${3:-}

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

now=$(date +%s)
header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' $((now - 60)) $((now + 540)) "$APP_ID" | b64url)
sig=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$KEY" -binary | b64url)
jwt="$header.$payload.$sig"

api() { curl -fsS -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" "$@"; }

if [ -n "$REPO" ]; then
  inst=$(api "https://api.github.com/repos/$REPO/installation" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
else
  inst=$(api "https://api.github.com/app/installations" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
fi

api -X POST "https://api.github.com/app/installations/$inst/access_tokens" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])'
