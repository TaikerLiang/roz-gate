#!/bin/sh
# One-time setup for developing the plugin itself: point git at the repo's
# own gates. Without this a fresh clone has silently inert pre-commit and
# pre-push hooks — the instrument looks present but isn't; CI's lint tier
# is the only backstop. Idempotent; run from anywhere inside the clone.
set -e
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "core.hooksPath = $(git config core.hooksPath) — pre-commit (naming) and pre-push (suites + version bump) are live."
