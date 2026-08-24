#!/usr/bin/env bash
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
echo "code word: XENOLITH" > NOTES.md
git add -A && git -c user.email=t@t -c user.name=t commit -qm notes
