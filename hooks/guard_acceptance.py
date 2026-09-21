#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: the acceptance suite is not editable on a
spec branch.

Invoked by guard-acceptance.sh only when HEAD is a ``spec/<n>`` branch. One
rule, the mechanical form of existing protocol text:

  C. Acceptance tests are written on ``qa/<n>`` and reach ``spec/<n>`` by
     merge (references/workflow.md (4); commands/integrate.md step 3). An
     *edit* to them on the spec branch is the one move integrate.md step 5
     forbids in words — "an integration RED is never resolved by editing a
     QA assertion to match observed behaviour, that rewrites the verdict
     into an echo of the implementation" — and at stage (7) it is worse:
     the human has already been told the work is verified, so a weakened
     assertion re-runs green and the evidence cards regenerate clean.

The guard is deliberately branch-and-path only: no stage detection, no
label lookup, no dispatch-identity check, no exemption list. That is what
makes it bind the main agent and every seat identically — at (7) the main
agent is host, author, committer and kit assembler at once, and it is the
one stage with no adversarial second party.

Exit 0 allows the tool call; exit 2 blocks it and feeds stderr to the
model. A repo with no Roz Gate config is not a roz-gate project — the
guard has nothing to enforce and allows the call.
"""

import json
import os
import re
import subprocess
import sys

DEFAULT_ACCEPTANCE_DIR = "tests/acceptance"

BLOCK_MSG = (
    "Roz Gate: blocked — %s is the acceptance suite, and this is a spec "
    "branch (%s). Acceptance tests are written on `qa/<n>` and reach "
    "`spec/<n>` by merge; editing an assertion here rewrites the verdict "
    "into an echo of the implementation (commands/integrate.md step 5), and "
    "at (7) the human has already been told the work is verified. The road: "
    "make the change on `qa/<n>`, merge it in, re-run the suite. If the "
    "assertion is wrong because the *contract* changed, that is the backward "
    "transition — amend the spec, then QA re-derives the test from it."
)


def deny(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def git(*args):
    try:
        out = subprocess.run(
            ["git"] + list(args), capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def load_acceptance_dir(top):
    """`acceptance_dir` from the project's CLAUDE.md Roz Gate config block.

    None → not a roz-gate project (no config block): nothing to enforce.
    Config block present but the key absent → the documented default, the
    same fallback /roz-gate:init writes.
    """
    try:
        with open(os.path.join(top, "CLAUDE.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    if not re.search(r"^###\s+(Roz Gate|Gated Loop) config\s*$", text, re.M):
        return None
    m = re.search(r"^-\s*acceptance_dir:\s*(.+)$", text, re.M)
    return (m.group(1).strip().strip("`") if m else DEFAULT_ACCEPTANCE_DIR)


def under(path, directory):
    """True when `path` is inside `directory` — both repo-relative, compared
    by path segments so `tests/acceptance-old/` is not `tests/acceptance/`.

    A directory that resolves to the repo root (`.`, `/`, empty) matches
    everything, which would deny every edit on every spec branch — a
    misconfiguration must not brick the loop, so it enforces nothing."""
    p = os.path.normpath(path).split(os.sep)
    d = [seg for seg in os.path.normpath(directory).split(os.sep) if seg not in (".", "")]
    if not d:
        return False
    return len(p) > len(d) and p[: len(d)] == d


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("tool_name") not in (None, "Edit", "Write", "MultiEdit"):
        return
    target = (payload.get("tool_input") or {}).get("file_path")
    if not target:
        return

    top = git("rev-parse", "--show-toplevel")
    if not top:
        return
    acceptance_dir = load_acceptance_dir(top)
    if not acceptance_dir:
        return

    try:
        rel = os.path.relpath(os.path.realpath(target), os.path.realpath(top))
    except ValueError:
        return
    if not under(rel, acceptance_dir):
        return

    deny(BLOCK_MSG % (rel, git("rev-parse", "--abbrev-ref", "HEAD") or "spec/?"))


main()
