#!/usr/bin/env python3
# C11 · A template with {seq} re-enters by the next sequence.
# Fixture: branch_template = {type}/{user}/{n}/{seq}, branch_user = paul;
# spec/paul/5/1 exists on the remote from a first attempt; its CR #101 is
# CLOSED (unmerged); the issue wears ready-for-spec again after the human
# amended it. C10's shape — but the template counts attempts, so the
# non-destructive route exists and the cut must take it.
# source: ledger C11 — "`spec/paul/5/2` is cut and its CR opened;
#   `spec/paul/5/1` still points at the first attempt; nothing deleted,
#   nothing force-pushed; no STOP comment, labels end at `in-spec-review`."
#   (issue #75)
# source: references/branch-names.md § Re-entry — closed unmerged, or no CR →
#   it carries `{seq}` → Expand renders the next sequence and the cut proceeds
# source: commands/next-stage.md A2 — It carries `{seq}` → `<spec-branch>` is
#   the next sequence (Expand); the previous attempt stays on the remote
# source: references/workflow.md — an agent never deletes or force-pushes a
#   remote branch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

OLD, NEW = "spec/paul/5/1", "spec/paul/5/2"
r, c = Run(), Checker()
rc, _ = r.git("rev-parse", "--verify", "-q", "refs/heads/%s" % NEW)
c.expect("next-stage.md A2 (the next sequence)", "%s was pushed" % NEW, rc == 0)
c.expect("next-stage.md A2 (cut from the base)", "%s descends from main" % NEW,
         rc == 0 and r.remote_is_ancestor("refs/heads/main", "refs/heads/%s" % NEW))
prs = [p for p in r.state().get("prs", {}).values()
       if p.get("headRefName") == NEW and p.get("state", "OPEN").upper() == "OPEN"]
c.expect("next-stage.md A5", "exactly one open CR from %s, targeting main" % NEW,
         len(prs) == 1 and prs[0].get("baseRefName") == "main")
c.expect("next-stage.md A7 (not the STOP exit)", "labels end at in-spec-review, never blocked",
         r.status_labels("5") == ["status: in-spec-review"])
c.expect("next-stage.md A2 (no delete remedy — there is nothing to delete)",
         "no comment carries `git push origin --delete`",
         not any("push origin --delete" in b for b in r.issue_comment_bodies("5")))
# The first attempt: still there, still the first attempt's content.
c.expect("workflow.md (never deleted by the agent)", "%s still exists on the remote" % OLD,
         r.git("rev-parse", "--verify", "-q", "refs/heads/%s" % OLD)[0] == 0)
c.expect("workflow.md (never force-pushed)", "%s still points at the first attempt" % OLD,
         (r.remote_file(OLD, "docs/specs/5/spec.md") or "").startswith("# Spec #5 — first attempt"))
c.expect("ledger C11 (refs: the two seeded plus the new one)",
         "exactly three refs on the remote", r.remote_ref_count() == 3)
c.finish()
