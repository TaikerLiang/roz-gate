#!/usr/bin/env bash
# F3 sandbox: a plain gated repo; the spec round builds everything itself.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
