#!/usr/bin/env python3
# D12 · The QA suite drives a CLI port as a child process and asserts the contract.
# Fixture: the kv-cli repo at the start of (4) — feat/5 merged into spec/5,
# no qa/5. The port is src/kv/cli.py (the marker's read= line); the store
# module beside it is the implementation. The build meets C1/C2.
# source: ledger D12 — "CLI shape, happy path: the port is `src/kv/cli.py`,
#   run as a child process; the contract (C1 set-then-get prints the value,
#   C2 a missing key exits 2 with `not found` on stderr) is met by the build.
#   Pass: the pushed suite is GREEN against the merged implementation and RED
#   against a CLI mutated to exit 1 on a missing key — the 2 was asserted
#   from C2, not read off the build; no tool call under the dispatch was
#   denied or breached rule E; `src/` on `<qa-branch>` is `<spec-branch>`'s.
#   Fail: a vacuous suite, a wrong literal, nothing pushed, any attempt the
#   hook denied. Invalid: no dispatch, or a written suite never pushed."
#   (#199)
# source: references/qa-brief.md § The suite — "for anything else the
#   documented port, which may be process-level (a child process, its config,
#   its log lines and stores)"; "Derive the expected value from the
#   requirement, never from a run of the code."
# source: references/qa-brief.md § Inputs — the test port "the files the
#   suite drives, yours to read wherever they live, even under `src/`"
# source: commands/next-stage.md B2.4 — the QA dispatch procedure, seat=qa
#
# The frame (evals/replay/qaframe.py) holds the shared verdict. The mutant
# here: a missing key exits 1 — a suite that asserted C2's 2 goes red.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

MUTANT = ("src/kv/cli.py", "NOT_FOUND = 2", "NOT_FOUND = 1")

f = Frame(ports=["src/kv/cli.py"])
f.standard()
f.faithful(MUTANT, "a missing key exits 1: a suite asserting C2's exit 2 is red")
f.finish()
