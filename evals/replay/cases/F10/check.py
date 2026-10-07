#!/usr/bin/env python3
# F10 · A branch is cut by the configured template.
# Fixture: branch_template = {type}/{user}/{n}/{seq}; branch_user = paul;
# default_branch = release/20261006 (main and release/20260926 also exist);
# issue #5 wears `type: fix` — the tempting wrong render for the SPEC
# branch, whose {type} is always `spec`.
# source: ledger F10 — "`spec/paul/5/1` descends from `origin/<default_branch>`,
#   the CR's head is that branch and targets the base, no `spec/5` and no
#   `fix/paul/5/1` exists on the remote." (every seed before this one ran
#   the default names — issue #75)
# source: references/branch-names.md § Expand — `{type}`: spec branch → `spec`;
#   `{user}` ← branch_user; `{seq}` ← 1 + the Lookup count
# source: commands/next-stage.md A2 — Create `<spec-branch>` from `<default_branch>`
# source: commands/next-stage.md A5 — CR-OPEN from `<spec-branch>` targeting `<default_branch>`
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

BASE = "release/20261006"
BRANCH = "spec/paul/5/1"
r, c = Run(), Checker()
rc, _ = r.git("rev-parse", "--verify", "-q", "refs/heads/%s" % BRANCH)
c.expect("branch-names.md (Expand) + next-stage.md (A2/A4)", "%s was pushed" % BRANCH, rc == 0)
c.expect("next-stage.md (A2)", "%s descends from %s — the configured base" % (BRANCH, BASE),
         rc == 0 and r.remote_is_ancestor("refs/heads/%s" % BASE, "refs/heads/%s" % BRANCH))
for wrong in ("spec/5", "fix/paul/5/1", "spec/paul/5/2"):
    c.expect("branch-names.md (the template, not the default; {type} is spec; first attempt is 1)",
             "no %s on the remote" % wrong,
             r.git("rev-parse", "--verify", "-q", "refs/heads/%s" % wrong)[0] != 0)
prs = [p for p in r.state().get("prs", {}).values() if p.get("headRefName") == BRANCH]
c.expect("next-stage.md (A5)", "exactly one CR opened from %s" % BRANCH, len(prs) == 1)
c.expect("next-stage.md (A5)", "the CR targets %s, not the trunk" % BASE,
         len(prs) == 1 and prs[0].get("baseRefName") == BASE)
c.expect("ledger F10 (no CR from any other name)", "no CR opened from another branch",
         all(p.get("headRefName") == BRANCH for p in r.state().get("prs", {}).values()))
c.finish()
