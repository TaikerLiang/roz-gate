#!/usr/bin/env python3
# F7 · A branch is cut from the configured base, not the trunk.
# Fixture: default_branch = release/20261006; main and release/20260926
# also exist on the remote (the older release branch is an ancestor of the
# current one, so "descends from the current one" is the only pass).
# source: ledger F7 — "`spec/<n>` descends from `origin/<default_branch>`
#   and the CR targets it — with `default_branch` naming a release branch
#   while `main` and an older release branch also exist." (the only base
#   ever exercised was `main`; a loop that always cut from the trunk
#   measured 100% — issue #38)
# source: commands/next-stage.md A2 — Create `spec/<n>` from `<default_branch>`
# source: commands/next-stage.md A5 — CR-OPEN from `spec/<n>` targeting `<default_branch>`
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

BASE = "release/20261006"
r, c = Run(), Checker()
rc, _ = r.git("rev-parse", "--verify", "-q", "refs/heads/spec/5")
c.expect("next-stage.md (A2/A4)", "spec/5 was pushed", rc == 0)
c.expect("next-stage.md (A2)", "spec/5 descends from %s — the configured base" % BASE,
         rc == 0 and r.remote_is_ancestor("refs/heads/%s" % BASE, "refs/heads/spec/5"))
prs = [p for p in r.state().get("prs", {}).values() if p.get("headRefName") == "spec/5"]
c.expect("next-stage.md (A5)", "exactly one CR opened from spec/5", len(prs) == 1)
c.expect("next-stage.md (A5)", "the CR targets %s, not the trunk" % BASE,
         len(prs) == 1 and prs[0].get("baseRefName") == BASE)
c.finish()
