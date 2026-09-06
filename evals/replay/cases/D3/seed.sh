#!/usr/bin/env bash
# D3 sandbox: plain gated repo; the inbox issue forces one product dispatch
# (async intake question batch) whose payload is the assertion target.
# This dispatch stays REAL — the payload IS what the case measures.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
