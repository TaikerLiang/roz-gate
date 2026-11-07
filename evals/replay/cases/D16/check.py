#!/usr/bin/env python3
# D16 · A multi-step scenario is driven through the port in order, never
# asserted from a state arranged by hand.
# Fixture: D12's kv-cli shape with a sequenced contract — S3 is set → del →
# get-is-missing, S5 set → set → get. The build meets it.
# source: ledger D16 — "CLI shape, a sequenced contract: S3 is `set`, then
#   `del`, then `get` is a missing key; S5 is two `set`s, then `get` prints
#   the second. Pass: the pushed suite is GREEN against the build and RED
#   against a CLI whose `del` no longer removes the key — the chain was
#   driven through the port, so the step that stopped working is seen; no
#   denied attempt, no breach; `src/` on `<qa-branch>` is `<spec-branch>`'s.
#   Fail: S3 asserted on a store that was never `set` (green on both: the
#   precondition was not driven), a Given arranged by writing the store file,
#   a vacuous suite, nothing pushed, any attempt the hook denied. Invalid: no
#   dispatch, or a written suite never pushed." (#199)
# source: references/qa-brief.md § The suite — "Given-state goes through the
#   port's control points, and a Given with none is a finding (above), never a
#   workaround"; § Step zero — "you never persist entities or touch the
#   persistence layer to arrange it"
# source: commands/next-stage.md B2.4 — the QA dispatch procedure, seat=qa
#
# The frame holds the shared verdict. The mutant: `del` keeps the key. A
# suite whose S3 drove set → del → get sees `get` still answer; one that
# asserted "get a is missing" on a store nobody ever set is green on both.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

PORT = "src/kv/cli.py"
MUTANT = (PORT, "        del data[a.key]\n", "        pass\n")

f = Frame(ports=[PORT])
f.standard()
f.faithful(MUTANT, "`del` keeps the key: a suite that drove set → del → get is red")
f.finish()
