#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: the acceptance suite is not editable on a
spec branch.

Invoked by guard-acceptance.sh on every Edit / Write / MultiEdit — the shim
is a thin wrapper since #277: the payload, the path and the config are read
here, in one place. One rule (the acceptance rule — no letter; rule C is
guard-gate's quote-open rule), the mechanical form of existing protocol
text:

  Acceptance tests are written on ``qa/<n>`` and reach ``spec/<n>`` by
  merge (references/workflow.md (4); commands/integrate.md step 3). An
  *edit* to them on the spec branch is the one move integrate.md step 5
  forbids in words — "an integration RED is never resolved by editing a
  QA assertion to match observed behaviour, that rewrites the verdict
  into an echo of the implementation" — and at stage (7) it is worse:
  the human has already been told the work is verified, so a weakened
  assertion re-runs green and the evidence cards regenerate clean.

**The place is the file's** (#277). Branch, toplevel, config block and
local file all come from the worktree that holds ``file_path`` — its
nearest existing ancestor directory, since a Write may create the file and
its directories; a relative path resolves against the hook's cwd. The loop
runs from the main checkout on ``main`` and edits
``<common-dir>/roz-gate/wt/spec/<n>/…`` by absolute path: judged from the
cwd, those edits were never denied from 1.22.0 on. A path in no git work
tree is allowed. The config block is read from ``CLAUDE.md``, else
``CLAUDE.local.md``, in that worktree or its main checkout
(``hooks/config_block.py``, #94); the template from the local file, the
same two places (#165).

The spec kind is ``spec/*``, or whatever the local ``branch_template``
renders for it (``.claude/roz-gate.local.json``, bin/roz-config's;
references/branch-names.md). A stored template ``branch_names.validate``
rejects cannot tell a spec branch from a qa branch, so a write under the
suite is denied on **every** branch, with the reason and the checkout
whose file to fix (#277, ruling 1) — the visible direction; writes
elsewhere are untouched.

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

# The hook's own directory: guard-*.sh runs the file by path (sys.path[0] is
# this dir already); the lint tier and the D5 checker load it by
# spec_from_file_location, from elsewhere — the reader must still import.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from branch_names import LOCAL_FILE, local_key_source, pattern_for_kind, validate  # noqa: E402
from config_block import find_block, main_checkout  # noqa: E402

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

INVALID_MSG = (
    "Roz Gate: blocked — %(rel)s is the acceptance suite, and branch_template %(t)r in "
    "%(file)s is invalid (%(why)s), so the guard cannot tell a spec branch from a qa "
    "branch: every write to the suite is denied until it is fixed "
    "(references/branch-names.md). Fix it in that checkout: `cd %(root)s && roz-config "
    "branch_template <template>`, or `roz-config branch_template` with no value to go "
    "back to the default `{kind}/{n}`."
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


def toplevel(target):
    """The toplevel of the work tree that holds `target`, or None (#277): a
    relative path resolves against the hook's cwd; the walk up stops at the
    nearest existing directory, since a Write may create the file and its
    directories."""
    d = os.path.dirname(os.path.abspath(target))
    while not os.path.isdir(d):
        d = os.path.dirname(d)
    return git("-C", d, "rev-parse", "--show-toplevel")


def load_config(top, main):
    """(`acceptance_dir`, `branch_template`, the checkout whose local file
    holds the template) for the work tree `top` and its main checkout
    `main`: the dir from the project's Roz Gate config block — `CLAUDE.md`,
    else `CLAUDE.local.md`, in either (config_block.py) — the template from
    bin/roz-config's local file, the first of the two that holds the key
    (a stored "" is a chosen default → None). The block's old
    `- branch_template:` line is never read here: roz-config moves it into
    the file once (#165).

    None → not a roz-gate project (no config block anywhere): nothing to
    enforce. Config block present but `acceptance_dir` absent → the
    documented default, the same fallback /roz-gate:init writes.
    `branch_template` unset → None: the spec branch is `spec/*`.
    """
    block = find_block(top, main)
    if block is None:
        return None
    m = re.search(r"^-\s*acceptance_dir:\s*(.+)$", block, re.M)
    template, holder = local_key_source((top, main), "branch_template")
    return (m.group(1).strip().strip("`") if m else DEFAULT_ACCEPTANCE_DIR,
            template, holder)


def is_spec_branch(branch, template):
    """Is HEAD a spec branch — any issue, any `{user}`, any `{seq}`:
    hooks/branch_names.pattern_for_kind for the spec kind with `n` open
    (#135; references/branch-names.md § The hooks). Unset → `spec/*`, as
    before. An invalid template never reaches here: main() denies the
    suite write first (#277)."""
    if template is None:
        return branch.startswith("spec/")
    return pattern_for_kind(template, "spec").match(branch) is not None


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

    top = toplevel(target)
    if not top:
        return
    main_root = main_checkout(top)
    config = load_config(top, main_root)
    if not config:
        return
    acceptance_dir, template, holder = config

    try:
        rel = os.path.relpath(os.path.realpath(target), os.path.realpath(top))
    except ValueError:
        return
    if not under(rel, acceptance_dir):
        return

    why = validate(template) if template is not None else None
    if why:
        deny(INVALID_MSG % {"rel": rel, "t": template, "why": why, "root": holder,
                            "file": os.path.join(holder, LOCAL_FILE)})
    branch = git("-C", top, "rev-parse", "--abbrev-ref", "HEAD") or ""
    if not is_spec_branch(branch, template):
        return

    deny(BLOCK_MSG % (rel, branch or "spec/?"))


main()
