#!/usr/bin/env bash
# F1 sandbox: a plain gated repo. All conversation state lives in the forge
# fixture; nothing in the repo is pending.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
