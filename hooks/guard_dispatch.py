#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: a seat dispatch carries its contract (#382).

Invoked by guard-dispatch.sh on an Agent / Task call the prefilter escalated.
One rule, the mechanical form of references/workflow.md § Seats and personas:

  L. Every dispatch of a seat attaches the seat's contract — its R&R row
     (Owns / Never) and the line ``Plugin root: <dir> — plugin paths resolve
     here; never search for plugin files.`` The 2026-11-17/18 sweep measured
     both misses: D3 pointed the product seat at its row instead of
     attaching it (1/3, after 2/3 the sweep before), and 9 of 245 seat
     dispatches had no ``Plugin root:`` line — every sandbox leak of that
     sweep came from one of the 9 (the seat ran ``find /`` for workflow.md).

A seat is the agent type ``bin/roz-persona`` resolves for it — its
``resolve()``, its ``LINE`` and ``SEATS``, loaded from the file, never
copied: a ``roz-gate:<seat>`` type, or the agent the ``### Roz Gate
personas`` block maps to a seat (``implementer: backend``), or the
``implementer`` default when ``.claude/agents/implementer.md`` exists. Any
other type — the commit helper, the scanner, ``general-purpose`` — is not a
seat and is never judged. A repo with no config block is not a roz-gate
project: allowed.

The predicate, on every string of the tool input:
  - a ``Plugin root:`` followed by an absolute directory that holds
    ``references/workflow.md``;
  - every Owns and Never term of the seat's row, read from this plugin's
    ``references/workflow.md`` at call time, never written here. A term is a
    comma / semicolon / dash / ``+`` separated piece of the cell, with
    parentheticals, markdown and ``<placeholders>`` dropped; it is found
    when its words appear in order, each word opening a word of the prompt
    (case and punctuation ignored, so ``impl tests`` is found in
    "implementation tests"). The deny message prints the row to paste.

Fail direction: a payload the guard cannot parse, or a workflow.md whose
table it cannot read, is a tool failure — denied (#281). A continuation ping
to a seat is a seat dispatch: it carries the contract too.
Stdlib only, Python 3.9-compatible, like the other guards.
"""

import json
import os
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

HOOKS = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HOOKS)
WORKFLOW = os.path.join(PLUGIN, "references", "workflow.md")
sys.path.insert(0, HOOKS)
from config_block import find_block, main_checkout  # noqa: E402

sys.dont_write_bytecode = True                 # never a __pycache__ in bin/
_PERSONA = os.path.join(PLUGIN, "bin", "roz-persona")
_spec = spec_from_loader("roz_persona", SourceFileLoader("roz_persona", _PERSONA))
persona = module_from_spec(_spec)
_spec.loader.exec_module(persona)

DENY_OPEN = "Roz Gate: blocked — a seat dispatch without its contract"
FAILED = ("roz-gate guard-dispatch: %s, so the dispatch is blocked. This is a tool failure, "
          "not a protocol block — fix it and retry.")
ROW = re.compile(r"^\|\s*\*\*([\w ]+)\*\*\s*\|(.*)\|\s*$", re.M)
ROOT = re.compile(r"Plugin root:\**[ \t]*([^\n]*)")
WORD = re.compile(r"[a-z0-9]+")


def deny(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def rows():
    """{seat: (owns cell, never cell)} from workflow.md's R&R table."""
    try:
        with open(WORKFLOW, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        deny(FAILED % ("cannot read %s" % WORKFLOW))
    out = {}
    for name, rest in ROW.findall(text):
        cells = [x.strip() for x in rest.split(" | ")]
        if len(cells) == 2:
            out[name.strip()] = tuple(cells)
    return out


def terms(cell):
    """The cell's terms, each a list of lowercase words. A parenthetical or a
    placeholder ends a term: `points (§5) every` is two."""
    s, prev = cell, None
    while s != prev:                                   # nested parentheticals
        prev, s = s, re.sub(r"\([^()]*\)", ",", s)
    s = re.sub(r"<[^<>]*>", ",", s).replace("**", "").replace("`", "")
    return [w for w in (WORD.findall(p.lower()) for p in re.split(r"[,;+—]", s)) if w]


def found(term, words):
    n = len(term)
    return any(all(words[i + j].startswith(term[j]) for j in range(n))
               for i in range(len(words) - n + 1))


def missing_terms(cells, text):
    words = WORD.findall(text.lower())
    return [" ".join(t) for cell in cells for t in terms(cell) if not found(t, words)]


def root_ok(text):
    """A `Plugin root:` whose rest of line opens with an absolute plugin dir:
    quoted (backticks, double quotes) or not, each whitespace-bounded prefix
    tried, longest first — a dir whose name holds a space is one dir, and
    the line's `— plugin paths resolve here …` tail is not part of it."""
    for m in ROOT.finditer(text):
        rest = m.group(1).strip()
        q = rest[:1]
        if q in "`\"" and q and q in rest[1:]:
            cands = [rest[1:rest.index(q, 1)]]
        else:
            cands = [rest[:k.start()] for k in re.finditer(r"\s|$", rest)][::-1]
        for d in cands:
            d = d.rstrip(".,;:)`'\"")
            if os.path.isabs(d) and os.path.isfile(os.path.join(d, "references",
                                                                  "workflow.md")):
                return True
    return False


def seats_of(agent, top):
    """The seats `agent` sits in, as bin/roz-persona resolves them."""
    main_top = main_checkout(top)
    roots = [top] + ([main_top] if main_top and os.path.realpath(main_top)
                     != os.path.realpath(top) else [])
    lines = {}
    for name, value in persona.LINE.findall(find_block(top, main_top, title="personas") or ""):
        if name in persona.SEATS:
            lines.setdefault(name, value)
    out = [s for s in persona.SEATS if persona.resolve(s, lines, roots).get("agent_type") == agent]
    if agent.startswith("roz-gate:") and agent[len("roz-gate:"):] in persona.SEATS:
        out.append(agent[len("roz-gate:"):])
    return list(dict.fromkeys(out))


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        inp = payload.get("tool_input") or {}
        agent = inp.get("subagent_type") or ""
    except (ValueError, AttributeError):
        deny(FAILED % "the hook input is not a JSON tool call")
    if payload.get("tool_name") not in (None, "Agent", "Task") or not agent:
        return
    top = git(payload.get("cwd") or os.getcwd(), "rev-parse", "--show-toplevel")
    if not top or find_block(top) is None:
        return
    seats = seats_of(agent, top)
    if not seats:
        return
    text = " ".join(v for v in inp.values() if isinstance(v, str))
    table = rows()
    lost = [s for s in seats if s not in table]
    if lost:
        deny(FAILED % ("%s has no R&R row for %s" % (WORKFLOW, ", ".join(lost))))
    gaps = {s: missing_terms(table[s], text) for s in seats}
    seat = min(seats, key=lambda s: len(gaps[s]))
    has_root = root_ok(text)
    if has_root and not gaps[seat]:
        return
    owns, never = table[seat]
    need = []
    if not has_root:
        need.append("- the line `Plugin root: %s — plugin paths resolve here; never search for "
                    "plugin files.` — the absolute directory `${CLAUDE_PLUGIN_ROOT}` expands to "
                    "(Bash never sets it). A seat without it searches the disk for plugin files."
                    % PLUGIN)
    if gaps[seat]:
        need.append("- the %s R&R row itself, not a pointer to it — missing: %s. Paste the row:\n"
                    "  **%s** — Owns: %s — Never: %s"
                    % (seat, ", ".join('"%s"' % t for t in gaps[seat]), seat, owns, never))
    deny("%s. `%s` sits in the %s seat, and every seat dispatch attaches the seat's contract "
         "(references/workflow.md § Seats and personas). This prompt lacks:\n%s\n"
         "Add what is missing and re-send the same dispatch; a follow-up to a seat carries "
         "both too." % (DENY_OPEN, agent, seat, "\n".join(need)))


if __name__ == "__main__":
    main()
