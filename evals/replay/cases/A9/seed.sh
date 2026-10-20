#!/usr/bin/env bash
# A9 sandbox: the common seed and nothing else — two track-less inbox issues
# (state.json), both authored by kai and assigned to paul (the gate holder),
# each with its questions batch posted. #7: kai answers Q1 and opens a new
# question after the batch. #8: only `github-actions[bot]` (`type` Bot)
# spoke after it. User mode: no `bot_login`, so the agent's own comments are
# told from paul's by their marker alone.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
