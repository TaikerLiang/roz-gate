#!/usr/bin/env python3
# Smoke S1: the SUT can read a repo file through this harness
# Plumbing proof, not a behavioural assertion — no ledger source applies.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run
r = Run()
sys.exit(0 if ("XENOLITH" in r.result_text()) else 1)
