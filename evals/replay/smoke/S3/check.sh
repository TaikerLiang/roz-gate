#!/usr/bin/env bash
# Smoke S3: the SUT's tool calls reach the forge stub (write path).
# Plumbing proof, not a behavioural assertion.
set -u
grep -q '"route": "issue-comment".*smoke-test ping' "$RUN_DIR/forge/journal.jsonl"
