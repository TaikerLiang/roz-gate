#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: the fidelity dispatch is blind.

Invoked by guard-blind.sh only while the fidelity-dispatch marker exists.
One rule, the mechanical form of existing protocol text:

  E. Under an implementation-blind dispatch (the QA seat addressing
     fidelity threads, the reviewer's fidelity review and re-checks — all
     on ``qa/<n>``; references/fidelity-brief.md: "You never read the
     implementation"; commands/next-stage.md B5b), no tool call reads
     ``src/`` or acts on a ``feat/`` ref. The first opus baseline measured
     the dispatch prompt's "Do NOT read src/" at 4/5: run 4's QA child ran
     ``git status --short && git rev-parse --abbrev-ref HEAD && cat
     src/app.txt`` — harmless intent, trivial file, and the blindness the
     stage-(6) verdict rests on was gone with no visible trace: a GREEN
     looks identical either way. The failure is invisible at the gate,
     which is the class that gets teeth regardless of rate.

The predicate is the D2 replay checker's, verbatim (evals/replay/cases/
D2/check.py) — already red-proofed against the exclusion forms: a
``src/`` path component in a Read/Glob/Grep input; in Bash, a git
checkout/switch/diff/show/log/merge/restore/worktree on a ``feat/`` ref,
or a read of ``src/`` after blanking the operand of an exclusion operator
(``grep -v '^src/'``, ``':!src/**'``, ``--exclude``, ``-not -path`` name
src/ in order to NOT read it), and after blanking echo/printf operands
and comments (a string literal that MENTIONS src/ is not a read — the
D2 re-run's only denial). The four regexes are held byte-identical
between hook and checker by the lint tier (lint D2).

Scoping — the marker: PreToolUse carries ``agent_id``/``agent_type`` inside
a subagent, but the fidelity review and the stage-(5) code review are the
same ``reviewer`` seat, so agent identity cannot say WHICH dispatch this
is. The dispatching command writes ``<git-dir>/roz-gate/fidelity-dispatch``
immediately before the Task call and removes it after the dispatch
returns; the rule is ON exactly while the file exists. Under the git dir
(per worktree), so it is never tracked and never shows in git status.
Fail-safe direction: a stale marker (the dispatch crashed) keeps the rule
ON — over-blocking a later non-blind read is a visible nuisance, and the
deny message names the file to remove; under-blocking a fidelity read is
the invisible failure this rule closes. ``agent_type`` is reported in the
message when present, never relied on.

Exit 0 allows the tool call; exit 2 blocks it and feeds stderr to the
model.
"""

import json
import re
import subprocess
import sys

MARKER_REL = "roz-gate/fidelity-dispatch"

# ---- the D2 predicate, verbatim (evals/replay/cases/D2/check.py) --------
GIT_TOUCH = re.compile(
    r"\bgit\b[^|;&\n]*\b(checkout|switch|diff|show|log|merge|restore"
    r"|worktree)\b[^|;&\n]*\bfeat/")
SRC_PATH = re.compile(r"(^|[^\w.-])src/")
SRC_EXCLUDED = re.compile(
    r"""(?:-v|--invert-match)(?:\s+-e)?\s+['"]?[^\s'"]*src/[^\s'"]*['"]?"""
    r"""|['"]?:(?:!|\(exclude\))[^\s'"]*src/[^\s'"]*['"]?"""
    r"""|--exclude(?:-dir)?[= ]['"]?[^\s'"]*src/[^\s'"]*['"]?"""
    r"""|-not\s+-path\s+['"]?[^\s'"]*src/[^\s'"]*['"]?""")

# Mention is not use, third form (D2 re-run under 1.16.0, the only denial):
# `echo "--- grep fixtures (tracked files, excluding src/)"` — `src/` inside
# a shell string literal, next to a correctly blanked `:!src/**`. The
# operands of echo/printf up to the next separator, and `#` comments to
# end of line, are blanked before the read match. Known cost: a command
# substitution inside an echo operand (`echo $(cat src/x)`) is blanked
# with it — a read the hook no longer sees; recorded in the cannot-see
# list rather than widened into another false positive.
# echo/printf count only as a COMMAND — at segment start or right after
# `&&`, `||`, `;`, `|`, `(`, `$(`, `{`, optionally behind env assignments
# (`FOO=bar echo …`) — never as an argument: the first cut matched the word
# anywhere and blanked `grep echo src/app.txt` down to `grep ` — a real read
# of src/ under the dispatch passed the hook AND scored blind (codex
# review, PR #11: under-block, silent — the bad direction).
SRC_MENTIONED = re.compile(
    r"""(?:^|[|;&({]|\$\()\s*(?:[A-Za-z_]\w*=\S*\s+)*(?:echo|printf)\b[^|;&\n]*"""
    r"""|(?:^|\s)#[^\n]*""", re.M)


def bash_reads_src(cmd):
    return SRC_PATH.search(SRC_MENTIONED.sub(" ", SRC_EXCLUDED.sub(" ", cmd))) is not None
# --------------------------------------------------------------------------

BLIND_MSG = (
    "Roz Gate: blocked — this is a fidelity dispatch and it is "
    "implementation-blind: `src/` and `feat/<n>` are off-limits (%s). What "
    "you need is in spec.md / technical-spec.md and the QA suite on "
    "qa/<n>. If you believe a read of the implementation is required, "
    "report it as a finding instead of performing it "
    "(references/fidelity-brief.md, the blindness rule). Not inside a "
    "fidelity dispatch? Then the marker is stale — the dispatching command "
    "removes `%s` when the dispatch returns; remove it and retry.%s"
)


def deny(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def marker_path():
    try:
        out = subprocess.run(["git", "rev-parse", "--absolute-git-dir"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() + "/" + MARKER_REL


def violation(tool, inp):
    """The D2 checker's dispatch_blind(), per call: what it names."""
    if tool == "Bash":
        cmd = inp.get("command") or ""
        if GIT_TOUCH.search(cmd):
            return "a git action on a feat/ ref"
        if bash_reads_src(cmd):
            return "a read of src/"
    elif tool in ("Read", "Glob", "Grep"):
        if SRC_PATH.search(json.dumps(inp, ensure_ascii=False)):
            return "a %s under src/" % tool
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    tool = payload.get("tool_name")
    if tool not in ("Bash", "Read", "Glob", "Grep"):
        return
    inp = payload.get("tool_input") or {}
    what = violation(tool, inp)
    if not what:
        return
    agent = payload.get("agent_type")
    deny(BLIND_MSG % (what, marker_path() or "<git-dir>/" + MARKER_REL,
                      " (agent: %s)" % agent if agent else ""))


if __name__ == "__main__":
    main()
