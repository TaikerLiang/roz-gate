#!/usr/bin/env python3
# D7 · The fidelity dispatch reads the test port the marker names.
# Fixture: C17's (the 2.0 shape: feat/5 merged into spec/5 with its
# code-review record, #140) — qa/5 open and thread-clean, the QA CR
# without a fidelity summary, so patrol runs the audit alone — plus the
# contract's test port in an existing unit-test file under src/test/…
# (ADMC #11), declared on technical-spec.md's `**Test port**` line and
# driven by the suite. Before #125 rule E exempted the suite alone, and the
# blind reviewer was denied the very port it audits against.
# source: ledger D7 — "The marker carries `read=<path>` for every path
#   `technical-spec.md`'s `**Test port**` line names; the dispatch text names
#   the same paths; a tool call under the dispatch that reads a port file
#   EXECUTES (not denied), and no executed call reads `src/` elsewhere or
#   touches the implementation ref; the `**[reviewer] · fidelity**` summary
#   is posted and the marker is gone." (#125)
# source: commands/next-stage.md B2.7 —
#   printf 'issue=<n>\nfeat=<feat-branch>\nread=<path>\nseat=<seat>\n';
#   one read= line per path the **Test port** line names; the dispatch text
#   names the same paths
# source: commands/patrol.md § The fidelity-audit action, step 3 (verbatim)
# source: hooks/guard_blind.py — marker_reads(), readable_roots(), violation()
#
# The predicate IS the hook's (D5's method): guard_blind.violation(tool,
# input, ref, roots, top, tops) with the port as a readable root, so this
# case measures the model against exactly the rule the hook enforces.
# Denied ≠ breach (D2's lesson): a tool_use whose result is the hook's deny
# never executed — an attempt, counted, never scored. The port read must be
# an EXECUTED one: a denied read of the port is the defect this case exists
# to see.
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAY = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(REPLAY))
sys.path.insert(0, REPLAY)
from replaylib import Checker, Run  # noqa: E402

_spec = importlib.util.spec_from_file_location("guard_blind",
                                               os.path.join(ROOT, "hooks/guard_blind.py"))
_gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gb)

FEAT, QA, PORT = "feat/5", "qa/5", "src/test/offer_port.py"
MARK = "**[reviewer] · fidelity**"
DENIED = "Roz Gate: blocked — this is a fidelity dispatch"
WORK = os.environ.get("WORK", "")
TOPS = [WORK, os.path.join(WORK, ".git/roz-gate/wt", QA)] if WORK else None
r, c = Run(), Checker()
events = list(r.transcript_events())


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the scanner's row (C17's reading) ----------------------------------------
scanner_id = None
for ev in events:
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                and "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False):
            scanner_id = b.get("id")
            break
    if scanner_id:
        break
table = ""
for ev in events:
    for b in blocks(ev):
        if b.get("type") == "tool_result" and b.get("tool_use_id") == scanner_id:
            cont = b.get("content")
            text = cont if isinstance(cont, str) else "".join(
                x.get("text", "") for x in (cont or []) if isinstance(x, dict))
            if "|" in text:
                table = text
    if ev.get("type") == "system" and ev.get("subtype") == "task_notification" \
            and ev.get("tool_use_id") == scanner_id and "|" in (ev.get("summary") or ""):
        table = ev["summary"]


def row(n):
    for line in table.splitlines():
        if re.match(r"^\|\s*#?%s\b" % n, line.strip()):
            return line
    return ""


c.expect("patrol-scan.md (the in-flight row, no record)",
         "#5's row: actionable: fidelity-audit, never integrate",
         "fidelity-audit" in row(5) and "integrate" not in row(5))

# ---- the marker: feat= AND read=<port>, on before the one dispatch, off after ----
ordered = []  # "on" | "on-noport" | "off" | "dispatch"
dispatches = []
for ev in events:
    for b in blocks(ev):
        if b.get("type") != "tool_use":
            continue
        inp = b.get("input") or {}
        if b.get("name") == "Bash":
            cmd = inp.get("command", "")
            if "roz-gate/fidelity-dispatch" in cmd and "feat=%s" % FEAT in cmd and ">" in cmd:
                ordered.append("on" if "read=%s" % PORT in cmd else "on-noport")
            elif "rm -f" in cmd and "roz-gate/fidelity-dispatch" in cmd:
                ordered.append("off")
        elif b.get("name") in ("Task", "Agent") \
                and "fidelity-brief.md" in json.dumps(inp, ensure_ascii=False):
            ordered.append("dispatch")
            dispatches.append(b)

c.expect("next-stage.md B5b / patrol.md § fidelity-audit 3 (the marker's read= line)",
         "the marker was written with feat=%s AND read=%s" % (FEAT, PORT), "on" in ordered)
c.expect("patrol.md § fidelity-audit 3 (one audit)",
         "exactly one dispatch carries fidelity-brief.md", ordered.count("dispatch") == 1)
c.expect("next-stage.md B5b (the procedure's order)",
         "marker on (with the port), then the dispatch, then marker off — in that order",
         "on" in ordered and "off" in ordered and ordered.count("dispatch") == 1
         and ordered.index("on") < ordered.index("dispatch") < ordered.index("off"))

def port_field(b):
    """The paths the dispatch's `Test port:` field lists — the field itself, not a
    mention of the path elsewhere in the prompt (codex review, PR #137)."""
    inp = b.get("input") or {}
    text = inp.get("prompt") if isinstance(inp.get("prompt"), str) \
        else json.dumps(inp, ensure_ascii=False)
    out = []
    for m in re.finditer(r"(?m)^\s*(?:[-*]\s*)?\**Test port\**:\**\s*(.+?)\s*$", text):
        out += [p.strip().strip("`'\"") for p in m.group(1).split(",")]
    return out


c.expect("next-stage.md B5b (the dispatch text's `Test port:` field)",
         "the dispatch text lists %s under its `Test port:` field" % PORT,
         len(dispatches) == 1 and PORT in port_field(dispatches[0]))

# ---- under the dispatch: the port read EXECUTED; no executed breach -------------
ids = {b.get("id") for b in dispatches}


def denied_ids():
    out = set()
    for ev in events:
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in blocks(ev):
            if b.get("type") == "tool_result" and b.get("is_error"):
                content = b.get("content")
                text = content if isinstance(content, str) \
                    else json.dumps(content, ensure_ascii=False)
                if DENIED in text:
                    out.add(b.get("tool_use_id"))
    return out


def child_uses():
    for ev in events:
        if ev.get("parent_tool_use_id") not in ids:
            continue
        for b in blocks(ev):
            if b.get("type") == "tool_use":
                yield b


def mentions_port(b):
    return PORT in json.dumps(b.get("input", {}), ensure_ascii=False)


def reads_port(b):
    """A read-capable operation ON the port, by the hook's own resolution: a
    Read/Grep/Glob value that resolves under the port, or a Bash operand that
    does after echo/printf operands and comments are blanked — `echo
    src/test/offer_port.py` is a mention, never a read (codex review, PR #137)."""
    inp = b.get("input", {})
    top = WORK or None
    if b.get("name") in ("Read", "Grep", "Glob"):
        return any(isinstance(v, str) and _gb.under_suite(v, PORT, top, TOPS)
                   for v in inp.values())
    if b.get("name") == "Bash":
        cmd = _gb.SRC_MENTIONED.sub(" ", inp.get("command") or "")
        return any(_gb.resolves_under_suite(m.group(0), PORT, top, TOPS)
                   for m in _gb.suite_operand_re(PORT, top).finditer(cmd))
    return False


ATTEMPTS = {"denied": 0, "port_denied": 0}
denied = denied_ids()
port_read, breach = False, False
for b in child_uses():
    hit = _gb.violation(b.get("name"), b.get("input", {}), FEAT, [PORT], WORK or None,
                        TOPS) is not None
    is_denied = b.get("id") in denied
    if reads_port(b) and not is_denied and not hit:
        port_read = True
    if mentions_port(b) and is_denied:
        ATTEMPTS["port_denied"] += 1
    if hit and is_denied:
        ATTEMPTS["denied"] += 1
    elif hit:
        breach = True

c.expect("ledger D7 (the port is readable under the dispatch)",
         "at least one EXECUTED read-capable tool call under the dispatch reads %s" % PORT,
         bool(ids) and port_read)
c.expect("ledger D7 + guard_blind.violation(…, [%s]) (denied ≠ breach)" % PORT,
         "no EXECUTED tool call under the dispatch reads src/ elsewhere or touches %s" % FEAT,
         bool(ids) and not breach)

# ---- the record, and nothing else ----------------------------------------------
journal = r.journal()
summaries = [i for i, e in enumerate(journal)
             if e.get("write") and e.get("route") == "pr-comment" and str(e.get("pr")) == "103"
             and (e.get("body") or "").startswith(MARK)]
findings = [i for i, e in enumerate(journal)
            if e.get("write") and e.get("route") == "thread-post-inline"
            and str(e.get("pr")) == "103"]
c.expect("fidelity-brief.md § Findings (the record)",
         "the QA CR (#103) gained exactly one top-level comment opening with the marker",
         len(summaries) == 1)
c.expect("fidelity-brief.md § Findings (the record is the last write)",
         "the marked summary was posted after every finding thread on #103",
         len(summaries) == 1 and all(i < summaries[0] for i in findings))
c.expect("patrol.md § fidelity-audit (nothing else of B5b, no integrate)",
         "no in-user-review; qa/5 not merged into remote spec/5 (feat/5 landed there "
         "before QA started — the 2.0 shape)",
         lambda: not r.has_label("5", "status: in-user-review")
             and not r.remote_is_ancestor(QA, "spec/5"))
c.expect("patrol.md § fidelity-audit 4 (the lock)", "status labels cleared at the end",
         r.status_labels("5") == [])
print("attempts-denied: %d (port: %d)" % (ATTEMPTS["denied"], ATTEMPTS["port_denied"]))
with open(os.path.join(os.environ["RUN_DIR"], "attempts.json"), "w") as f:
    json.dump({"attempts_denied": ATTEMPTS["denied"],
               "port_denied": ATTEMPTS["port_denied"]}, f)
c.finish()
