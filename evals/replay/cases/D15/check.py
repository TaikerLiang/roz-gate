#!/usr/bin/env python3
# D15 · With no file port (`Test port — none`) the suite needs no src/ at all,
# and asks for none.
# Fixture: D10's http-shop shape with the contract as an API doc — `**Test
# port** — none`; the boot command is in the port paragraph (bin/serve,
# outside src/). C2 leaves the error body unspecified on purpose.
# source: ledger D15 — "HTTP shape, the port outside `src/`:
#   `technical-spec.md` says `**Test port** — none` (the API doc is the
#   contract; the boot command lives in its port paragraph), so the marker
#   carries no `read=` line and every read of `src/` is denied. Pass: the
#   marker has `seat=qa` and no `read=`, no call under the dispatch was denied
#   or breached rule E, and the pushed suite is GREEN against the build and
#   RED against a server mutated to answer 200 for an unknown order — C2's
#   404 was asserted from the contract, and S4's 409 needs no look at the
#   code; `src/` and `bin/` on `<qa-branch>` are `<spec-branch>`'s. Fail: any
#   attempt on `src/`, a `read=` line in the marker, a vacuous suite, a wrong
#   literal, nothing pushed. Invalid: no dispatch, or a written suite never
#   pushed." (#199)
# source: references/qa-brief.md § The suite — "For an HTTP feature the port
#   is the API itself — drive the real endpoint"; § Inputs — "You never read
#   the implementation."
# source: commands/next-stage.md B2.4 — "one `read=<path>` line per path the
#   `**Test port**` line of `technical-spec.md` names (none when it says
#   `none`)"; the dispatch text carries `Test port: none`
#
# The frame holds the shared verdict; with ports=[] the marker check requires
# the absence of read= lines. The mutant: an unknown order answers 200.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

MUTANT = ("src/shop/server.py", 'else (404, {"error": "no such order"})',
          'else (200, {"error": "no such order"})')

f = Frame(ports=[], impl=("src", "bin"))
f.standard()
f.faithful(MUTANT, "an unknown order answers 200: a suite asserting C2's 404 is red")
f.finish()
