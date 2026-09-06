#!/usr/bin/env python3
# Smoke S3: the SUT's tool calls reach the forge stub (write path)
# Plumbing proof, not a behavioural assertion — no ledger source applies.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run
r = Run()
sys.exit(0 if (any(e.get("route")=="issue-comment" and "smoke-test ping" in e.get("body","") for e in r.journal())) else 1)
