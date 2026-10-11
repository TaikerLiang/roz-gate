#!/usr/bin/env python3
"""The config block's two homes — the one reader every hook uses (#94).

``/roz-gate:init`` writes the ``### Roz Gate config`` block into the
project's ``CLAUDE.md``. A project may keep it in ``CLAUDE.local.md``
instead (untracked, per clone — a shared ``CLAUDE.md`` the block must not
touch). Claude Code loads both files into the model's context, so the
commands found the block either way; the hooks opened ``CLAUDE.md`` only
and, finding nothing, judged the repo "not a roz-gate project": guard-
acceptance off, rule D off, rule A in user mode, rule E without its suite
exemption — four rules degraded with no visible trace while the loop ran.

The order is ``bin/roz-config``'s: ``CLAUDE.md``, then ``CLAUDE.local.md``
— the first block found wins, whole; no per-key merge. Each name is looked
up in the toplevel the hook runs in AND in the main checkout (the parent of
the common git dir): ``CLAUDE.local.md`` is untracked, so a linked worktree
under ``.git/roz-gate/wt/<branch>`` — where every dispatch runs — does not
carry it. Stdlib only, Python 3.9-compatible, like the hooks that import it.
"""

import os
import re
import subprocess

HOMES = ("CLAUDE.md", "CLAUDE.local.md")
# The block only — a `- key:` bullet in a later Notes section is
# documentation, not config (codex review, PR #82).
BLOCK = re.compile(r"^###\s+(?:Roz Gate|Gated Loop) config\s*$(.*?)(?=^#|\Z)", re.M | re.S)


def main_checkout():
    """The main worktree's toplevel — the parent of the common git dir — or
    None when git cannot say."""
    for args in (["--path-format=absolute", "--git-common-dir"], ["--git-common-dir"]):
        try:
            out = subprocess.run(["git", "rev-parse"] + args,
                                 capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode == 0 and out.stdout.strip():
            return os.path.dirname(os.path.abspath(out.stdout.strip()))
    return None


def find_block(top):
    """The text of the first config block found — `CLAUDE.md`, then
    `CLAUDE.local.md`, in `top`, then in the main checkout. None → not a
    roz-gate project (no block anywhere), or no toplevel."""
    if not top:
        return None
    roots = [top]
    main = main_checkout()
    if main and os.path.realpath(main) != os.path.realpath(top):
        roots.append(main)
    for root in roots:
        for name in HOMES:
            try:
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            m = BLOCK.search(text)
            if m:
                return m.group(1)
    return None
