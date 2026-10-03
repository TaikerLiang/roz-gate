#!/usr/bin/env python3
# F8 · A command leaves the user's checkout as it found it.
# Fixture: F3's shape; the checkout is on main with src/app.txt modified
# and notes.txt untracked before the command starts.
# source: ledger F8 — "HEAD is still main, the uncommitted edit and the
#   untracked file are intact, no linked worktree is left behind, and
#   spec/<n> reached the remote." (every earlier seed ran in a clean clone,
#   where a checkout in the user's tree is invisible — issue #37)
# source: references/workflow.md — The main agent → The workspace
# source: commands/next-stage.md A2 / A6c — worktree add, worktree remove
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

WORK = os.environ["WORK"]


def git(*args):
    p = subprocess.run(["git", "-C", WORK, *args], capture_output=True, text=True)
    return p.returncode, p.stdout


r, c = Run(), Checker()
c.expect("workflow.md (The workspace)", "the user's checkout is still on main",
         git("rev-parse", "--abbrev-ref", "HEAD")[1].strip() == "main")
with open(os.path.join(WORK, "src", "app.txt"), encoding="utf-8") as f:
    edit = f.read()
c.expect("workflow.md (The workspace)", "the uncommitted edit to src/app.txt is intact",
         edit == "demo — mid-edit, not committed\n")
c.expect("workflow.md (The workspace)", "the untracked notes.txt is intact",
         os.path.isfile(os.path.join(WORK, "notes.txt")))
c.expect("workflow.md (The workspace)", "git status shows exactly the user's two changes",
         sorted(git("status", "--porcelain")[1].splitlines()) == [" M src/app.txt", "?? notes.txt"])
wts = [ln for ln in git("worktree", "list", "--porcelain")[1].splitlines()
       if ln.startswith("worktree ")]
c.expect("next-stage.md (A6c)", "no linked worktree is left behind", len(wts) == 1)
rc, _ = r.git("rev-parse", "--verify", "-q", "refs/heads/spec/5")
c.expect("next-stage.md (A4)", "spec/5 reached the remote", rc == 0)
c.finish()
