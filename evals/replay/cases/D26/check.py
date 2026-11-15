#!/usr/bin/env python3
# D26 · An unmapped seat stops the run before it writes.
# Fixture: D25's Path B entry (spec/5 approved, #5 ready-for-dev) with no
# `implementer` line in the personas block and no .claude/agents/implementer.md:
# bin/roz-persona answers PERSONA_UNMAPPED, exit 2.
# source: ledger D26 — "No `implementer` line and no `.claude/agents/implementer.md`; #5 is
#   `ready-for-dev`. Pass: labels are `status: blocked` alone; the issue comment names
#   `PERSONA_UNMAPPED` and `/roz-gate:init`; zero seat dispatches, no branch pushed, no CR.
#   Fail: any dispatch for the build — a stand-in — or a write beyond the STOP comment."
#   (#198: the implementer default was asserted, never checked — the choice of who builds
#   was left to the command)
# source: commands/next-stage.md:30-33 — "**Personas**: run `python3
#   ${CLAUDE_PLUGIN_ROOT}/bin/roz-persona --json` and dispatch each seat as the
#   `agent_type` it prints"
# source: references/workflow.md:37-41 — "Its failure (`PERSONA_UNMAPPED`,
#   `AGENT_TYPE_UNAVAILABLE`), or a spawn the runtime refuses, is the STOP exit — never
#   another agent."
# source: commands/next-stage.md — the STOP exit: `status: blocked` alone, the issue comment
#
# Zero seat dispatches is zero Task/Agent calls: before B3 next-stage dispatches nothing
# but seats, and the commit sub-agent only after a build.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
writes = [e for e in r.journal() if e.get("write")]
beyond = sorted({e.get("route", "?") for e in writes
                 if e.get("route") not in ("issue-edit", "issue-comment")
                 or str(e.get("issue")) != "5"})
c.expect("ledger D26 + next-stage.md (the STOP exit)", "status labels are blocked ALONE",
         r.status_labels("5") == ["status: blocked"])
c.expect("ledger D26 + workflow.md:37-41",
         "an issue comment names PERSONA_UNMAPPED and /roz-gate:init",
         any("PERSONA_UNMAPPED" in b and "/roz-gate:init" in b
             for b in r.issue_comment_bodies("5")))
c.expect("ledger D26 + workflow.md:41 (never another agent)", "zero seat dispatches",
         r.dispatch_count() == 0)
c.expect("ledger D26 (no branch pushed)", "no new ref on the remote (main + spec/5 seeded)",
         r.remote_ref_count() == 2)
c.expect("ledger D26 (no CR, no write beyond the STOP comment)",
         "the only forge writes are #5's labels and comment — no CR (beyond: %s)"
         % (", ".join(beyond) or "none"), not beyond)
c.finish()
