#!/usr/bin/env python3
"""Roz Gate — the worktree copy (#122): layer 2, after a `git worktree add`.

Invoked by sync-worktree.sh only when a Bash command mentions `worktree`.
Every loop command works in a linked worktree under
`$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>` (references/
workflow.md § The workspace), and a gitignored file — `.env` first among
them — is never in one: a repo whose `test` loads it went red there for
harness reasons. This hook copies the files bin/roz-config's local key
`worktree_copy` lists (absent → `.env`; "" → nothing) from the main
checkout into every such worktree that lacks them:

- **files only** — never a directory, never a `.gitignore` (both reported,
  not copied). A plain file changes no ignore rule, so the one check below
  still holds after the copy; a directory or an ignore file could unignore
  something, the class of defect Codex found six times over on PR #184
  until the maintainer narrowed the key (ruling (a), 2026-10-21);
- only a file git ignores in the worktree is copied: an unignored one would
  sit there untracked, for the commit to pick up (reported, not copied);
- the worktrees are read from `git worktree list --porcelain`, never parsed
  from the command — the loop's command text carries the unexpanded
  `$(git rev-parse --git-common-dir)/…`;
- entries are normalized as git names them (`./x` → `x`); a missing source
  is skipped; an existing destination is never overwritten; an absolute or
  `..` path, or one outside the main checkout as written, is ignored — so a
  `.env` that links to a shared file elsewhere is still yours to copy;
- it copies contents, never links, and never writes back — a symlinked
  `.env` arrives as the file it points to, so writing to the worktree's
  copy touches neither yours nor a tracked file the link named;
- a copy is written to a stage in `<git-common-dir>/roz-gate/stage/` and
  published with a hard link, which creates the destination only if it does
  not exist: a concurrent run never replaces another's copy, and a run cut
  off mid-copy (the hook's timeout) leaves no truncated file in the
  worktree, and no stray one either, the stage being outside every worktree
  (codex review, PR #184);
- `.gitignore` is matched in any case (`.GITIGNORE` is the same file on a
  case-insensitive volume);
- worktrees anywhere else — your own — are never touched.

It never blocks (exit 0 always: the command has already run). What it
copied, and why it skipped what it skipped, go back to the agent as
PostToolUse `additionalContext`. Stdlib only, Python 3.9-compatible.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_block import main_checkout  # noqa: E402

LOCAL_FILE = os.path.join(".claude", "roz-gate.local.json")
DEFAULT = [".env"]
IGNORE_FILES = (".gitignore",)   # compared case-insensitively


def git(*args):
    try:
        out = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def wanted(main):
    """`worktree_copy` from the main checkout's local file — the worktree
    is the copy target and has none of its own."""
    try:
        with open(os.path.join(main, LOCAL_FILE), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return list(DEFAULT)
    if not isinstance(data, dict) or "worktree_copy" not in data:
        return list(DEFAULT)
    value = data["worktree_copy"]
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        return list(DEFAULT)
    return [p.strip() for p in value if isinstance(p, str) and p.strip()]


def inside(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def written_inside(path, root):
    """`path` lies under `root` as written — links not resolved: the entry is
    a name in your checkout, whatever it points at."""
    path, root = os.path.normpath(os.path.abspath(path)), os.path.normpath(os.path.abspath(root))
    return path == root or path.startswith(root + os.sep)


def entries(paths):
    """The list as git names it: each path normalized (`./x`, `x//y` → `x`,
    `x/y`), absolute and `..` entries and duplicates dropped."""
    rels = []
    for raw in paths:
        if os.path.isabs(raw) or ".." in raw.replace("\\", "/").split("/"):
            continue
        rel = os.path.normpath(raw).replace(os.sep, "/")
        if rel not in (".", "") and rel not in rels:
            rels.append(rel)
    return rels


def loop_worktrees(common):
    """Linked worktrees under `<common>/roz-gate/wt/`."""
    listing = git("worktree", "list", "--porcelain") or ""
    base = os.path.join(common, "roz-gate", "wt")
    return [line[len("worktree "):] for line in listing.splitlines()
            if line.startswith("worktree ") and inside(line[len("worktree "):], base)
            and os.path.realpath(line[len("worktree "):]) != os.path.realpath(base)]


def install_file(src, dst, stage_dir):
    """Write `src`'s contents (a symlinked `src` is read through) to a stage
    file in `stage_dir`, then publish it at `dst` with a hard link — which
    fails if `dst` exists, so nothing is replaced, and `dst` appears whole
    or not at all. The stage is removed either way. False: `dst` exists."""
    os.makedirs(stage_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=stage_dir, prefix="copy-")
    try:
        with os.fdopen(fd, "wb") as fout, open(src, "rb") as fin:
            shutil.copyfileobj(fin, fout)
        shutil.copystat(src, tmp)
        try:
            os.link(tmp, dst)
        except FileExistsError:
            return False
        return True
    finally:
        os.remove(tmp)


def copy_into(main, wt, paths, stage_dir):
    copied, errors, skipped = [], [], []
    for rel in entries(paths):
        src, dst = os.path.join(main, rel), os.path.join(wt, rel)
        if not written_inside(src, main) or not os.path.exists(src) or os.path.lexists(dst):
            continue
        if os.path.isdir(src):
            skipped.append("%s (a directory — worktree_copy lists files)" % rel)
            continue
        if os.path.basename(rel).lower() in IGNORE_FILES:
            skipped.append("%s (an ignore-rule file — never copied)" % rel)
            continue
        if git("-C", wt, "check-ignore", "-q", "--no-index", "--", rel) is None:
            skipped.append("%s (git does not ignore it there, so a commit could pick it up — "
                           "add it to .gitignore, or drop it from worktree_copy)" % rel)
            continue
        try:
            os.makedirs(os.path.dirname(dst) or wt, exist_ok=True)
            if install_file(src, dst, stage_dir):
                copied.append(rel)
        except OSError as exc:
            errors.append("%s (%s)" % (rel, exc))
    return copied, errors, skipped


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("tool_name") not in (None, "Bash"):
        return
    cwd = payload.get("cwd")
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
    common = (git("rev-parse", "--path-format=absolute", "--git-common-dir") or "").strip()
    main_root = main_checkout()
    if not common or not main_root:
        return
    # A bare repository has no checkout to copy from (its worktrees are all
    # linked); `--is-bare-repository` says false from inside one of them.
    if (git("config", "--file", os.path.join(common, "config"), "--bool", "core.bare")
            or "").strip() == "true":
        return
    paths = wanted(main_root)
    if not paths:
        return
    notes = []
    for wt in loop_worktrees(common):
        copied, errors, skipped = copy_into(main_root, wt, paths,
                                            os.path.join(common, "roz-gate", "stage"))
        if copied:
            notes.append("[roz-gate] copied %s into %s (worktree_copy, #122)"
                         % (", ".join(copied), wt))
        if skipped:
            notes.append("[roz-gate] did not copy into %s: %s" % (wt, "; ".join(skipped)))
        if errors:
            notes.append("[roz-gate] could not copy %s into %s — the worktree lacks them"
                         % (", ".join(errors), wt))
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": "\n".join(notes)}}))


if __name__ == "__main__":
    main()
