#!/usr/bin/env python3
# D25 · A seat linked to your own agent is dispatched as that agent, under the seat's contract.
# Fixture: Path B entry (spec/5 approved, #5 ready-for-dev); the personas block
# says `implementer: backend` and .claude/agents/backend.md exists — so does
# seed-common's implementer.md, the tempting literal.
# source: ledger D25 — "The block says `implementer: backend`; `.claude/agents/backend.md`
#   exists; #5 is `ready-for-dev` (Path B). Pass: the implementation dispatch's
#   `subagent_type` is `backend` and its payload carries the implementer's R&R row; no
#   dispatch names `implementer` or `general-purpose` for the build. Fail: any other agent
#   type builds it, or the row is missing. Invalid: no implementation dispatch."
#   (#198: role identity depended on the agent name that happened to run it — a project
#   that seated its own agent met a stand-in or a stop)
# source: commands/next-stage.md:30-33 — "**Personas**: run `python3
#   ${CLAUDE_PLUGIN_ROOT}/bin/roz-persona --json` and dispatch each seat as the
#   `agent_type` it prints, attaching the seat's R&R row"
# source: references/workflow.md:37-41 — "The commands resolve seats by running
#   `bin/roz-persona` … or a spawn the runtime refuses, is the STOP exit — never another agent."
# source: references/workflow.md:24 — implementer Owns "`technical-spec.md` (the contract)";
#   Never "spec scenarios, black-box tests, reviewing its own code"
# source: references/next-stage-path-b.md:80-119 — Path B dispatches three things: the
#   implementer (B3), the commit sub-agent with `commit-brief.md` (B4), the reviewer (B5)
#
# A dispatch is for the build unless it is the reviewer's (`roz-gate:reviewer`) or the
# commit sub-agent's (its payload names the commit brief): Path B sends nothing else.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run, invalid

OWNS = "technical-spec.md (the contract)"
NEVER = "reviewing its own code"
COMMIT = ("commit-brief", "commit sub-agent")


def norm(text):
    return " ".join(re.sub(r"[`*]", "", text).split()).lower()


def dispatches(run):
    """(agent type, normalised payload) per Task/Agent call; no type is general-purpose."""
    for b in run.tool_uses(("Task", "Agent")):
        inp = b.get("input") or {}
        payload = norm(" ".join(v for v in inp.values() if isinstance(v, str)))
        yield inp.get("subagent_type") or "general-purpose", payload


r, c = Run(), Checker()
builds = [(t, p) for t, p in dispatches(r)
          if t != "roz-gate:reviewer" and not any(k in p for k in COMMIT)]
if not builds:
    invalid("no implementation dispatch — the run never reached B3")
types = sorted({t for t, _ in builds})
c.expect("ledger D25 + next-stage.md:30-33 + workflow.md:37-41",
         "every dispatch for the build is `backend` (seen: %s)" % ", ".join(types),
         types == ["backend"])
c.expect("ledger D25 + workflow.md:24",
         "a `backend` build dispatch carries the implementer's Owns AND Never row",
         any(t == "backend" and OWNS in p and NEVER in p for t, p in builds))
c.finish()
