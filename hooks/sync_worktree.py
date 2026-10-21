#!/usr/bin/env python3
"""Roz Gate — the worktree copy (#122): layer 2, after a `git worktree add`.

Invoked by sync-worktree.sh only when a Bash command mentions `worktree
add`. Every loop command works in a linked worktree under
`$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>` (references/
workflow.md § The workspace), and a gitignored file — `.env` first among
them — is never in one: a repo whose `test` loads it went red there for
harness reasons. This hook copies the paths bin/roz-config's local key
`worktree_copy` lists (absent → `.env`; "" → nothing) from the main
checkout into every such worktree that lacks them:

- the worktrees are read from `git worktree list --porcelain`, never parsed
  from the command — the loop's command text carries the unexpanded
  `$(git rev-parse --git-common-dir)/…`;
- only a path git ignores in the worktree is copied — for a directory,
  every file in it (an ignore rule's `!` exception unignores one): an
  unignored file would sit there untracked, for the commit to pick up
  (reported, not copied; codex review, PR #184). Everything copied into a
  worktree is checked again once all of it is in place, by `git status`,
  under the rules the copy brought — a copied `.gitignore`, inside a
  directory or listed on its own, can unignore a file the first check
  passed — and every copied entry that shows an untracked file is removed,
  until nothing does;
- a missing source is skipped; an existing destination is never
  overwritten (a directory that exists is left whole); a path that is
  absolute, climbs with `..`, or sits outside the main checkout is ignored —
  judged on the path as written, so a `.env` that is a link to a shared file
  elsewhere is still yours to copy;
- it copies contents, never links, and never writes back — a symlinked
  `.env` (or a link inside a copied directory) arrives as the file it points
  to, so a test that writes to `.env` in the worktree touches neither your
  checkout's copy nor a tracked file the link named (codex review, PR #184);
- installing never replaces anything, even against a concurrent run: a
  file is created exclusively (`O_EXCL`), a directory is staged beside its
  destination and renamed onto a name that must not exist — and a failure
  removes what this run created, so nothing half-copied is left for a later
  run to mistake for done (codex review, PR #184);
- worktrees anywhere else — your own — are never touched.

It never blocks (exit 0 always: the command has already run). What it
copied, and any copy error, go back to the agent as PostToolUse
`additionalContext`. Stdlib only, Python 3.9-compatible.
"""

import errno
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_block import main_checkout  # noqa: E402

LOCAL_FILE = os.path.join(".claude", "roz-gate.local.json")
DEFAULT = [".env"]


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
        value = [part for part in value.split(",")]
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


def loop_worktrees(common):
    """Linked worktrees under `<common>/roz-gate/wt/`."""
    listing = git("worktree", "list", "--porcelain") or ""
    base = os.path.join(common, "roz-gate", "wt")
    return [line[len("worktree "):] for line in listing.splitlines()
            if line.startswith("worktree ") and inside(line[len("worktree "):], base)
            and os.path.realpath(line[len("worktree "):]) != os.path.realpath(base)]


def unignored_files(wt, rel, src):
    """The files under directory `src` (entry `rel`) git would NOT ignore in
    `wt` — one `check-ignore --stdin` for all of them. A directory with
    none of its own is judged by its `rel/` probe alone (the caller's)."""
    files = [os.path.join(rel.rstrip("/"), os.path.relpath(os.path.join(top, name), src))
             for top, _dirs, names in os.walk(src, followlinks=True) for name in names]
    if not files:
        return []
    try:
        out = subprocess.run(["git", "-C", wt, "check-ignore", "--no-index", "--stdin", "-z"],
                             input="\0".join(files) + "\0", capture_output=True, text=True,
                             timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return files
    if out.returncode not in (0, 1):     # 1: none ignored; anything else: git failed
        return files
    ignored = set(p for p in out.stdout.split("\0") if p)
    return [f for f in files if f not in ignored]


def untracked_after(wt, rels):
    """Files under `rels` that `git status` shows untracked in `wt` once
    they are there — under every rule then in force, the `.gitignore` files
    the copy brought included. Unknown (git failed) counts as untracked."""
    try:
        out = subprocess.run(["git", "-C", wt, "status", "--porcelain=v1", "-z",
                              "--untracked-files=all", "--"] + list(rels),
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return list(rels)
    if out.returncode != 0:
        return list(rels)
    return [e[3:] for e in out.stdout.split("\0") if e.startswith("?? ")]


def under(path, rel):
    rel = rel.rstrip("/")
    return path == rel or path.startswith(rel + "/")


def unwind_untracked(wt, copied, unignored):
    """Remove every entry this run copied into `wt` that shows an untracked
    file now that all of them are in place, and say so; repeat, because
    removing a copied `.gitignore` changes the rules for the rest."""
    for _ in range(len(copied) + 1):
        loose = untracked_after(wt, copied) if copied else []
        bad = [rel for rel in copied if any(under(p, rel) for p in loose)]
        if not bad:
            return
        for rel in bad:                      # ours: this run installed it
            dst = os.path.join(wt, rel)
            if os.path.isdir(dst) and not os.path.islink(dst):
                shutil.rmtree(dst, ignore_errors=True)
            elif os.path.lexists(dst):
                os.remove(dst)
            copied.remove(rel)
            names = [p for p in loose if under(p, rel)]
            unignored.append("%s (%s)" % (rel, ", ".join(names[:3])
                                          + (", …" if len(names) > 3 else "")))


def install_file(src, dst):
    """Create `dst` only if it does not exist (`O_EXCL`), with `src`'s
    contents — a symlinked `src` is read through. False: it exists."""
    with open(src, "rb") as fin:
        try:
            fout = open(dst, "xb")
        except FileExistsError:
            return False
        try:
            with fout:
                shutil.copyfileobj(fin, fout)
            shutil.copystat(src, dst)
        except OSError:
            os.remove(dst)
            raise
    return True


def install_dir(src, dst):
    """Stage a copy beside `dst`, then rename it onto `dst` — a rename onto a
    directory that holds anything fails, so nothing is replaced. False: it
    exists (another run installed it first)."""
    tmp = "%s.roz-gate-%d.tmp" % (dst.rstrip("/"), os.getpid())
    try:
        shutil.copytree(src, tmp)          # symlinks=False: a link arrives as its target
        os.rename(tmp, dst)
    except OSError as exc:                 # shutil.Error is an OSError
        shutil.rmtree(tmp, ignore_errors=True)
        if getattr(exc, "errno", None) in (errno.EEXIST, errno.ENOTEMPTY):
            return False
        raise
    return True


def entries(paths):
    """The list as git will name it: each path normalized (`./x`, `x//y` →
    `x`, `x/y` — `git status` reports canonical paths, and the final check
    matches against them), absolute and `..` entries dropped, duplicates
    dropped, and an entry under another listed one dropped — the parent's
    copy carries it, and copying the child first would make the parent's
    destination exist and skip the rest of it (codex review, PR #184)."""
    rels = []
    for raw in paths:
        if os.path.isabs(raw) or ".." in raw.replace("\\", "/").split("/"):
            continue
        rel = os.path.normpath(raw).replace(os.sep, "/")
        if rel not in (".", "") and rel not in rels:
            rels.append(rel)
    return [r for r in rels if not any(o != r and under(r, o) for o in rels)]


def copy_into(main, wt, paths):
    copied, errors, unignored = [], [], []
    for rel in entries(paths):
        src, dst = os.path.join(main, rel), os.path.join(wt, rel)
        if not written_inside(src, main) or not os.path.exists(src) or os.path.lexists(dst):
            continue
        # The destination does not exist yet, so git cannot tell a directory:
        # a `dir/` pattern matches only the path written with its slash.
        probe = rel.rstrip("/") + "/" if os.path.isdir(src) else rel
        if git("-C", wt, "check-ignore", "-q", "--no-index", probe) is None:
            unignored.append(rel)
            continue
        if os.path.isdir(src):
            loose = unignored_files(wt, rel, src)
            if loose:
                unignored.append("%s (%s)" % (rel, ", ".join(loose[:3])
                                              + (", …" if len(loose) > 3 else "")))
                continue
        try:
            os.makedirs(os.path.dirname(dst) or wt, exist_ok=True)
            if (install_dir if os.path.isdir(src) else install_file)(src, dst):
                copied.append(rel)
        except OSError as exc:
            errors.append("%s (%s)" % (rel, exc))
    unwind_untracked(wt, copied, unignored)
    return copied, errors, unignored


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
        copied, errors, unignored = copy_into(main_root, wt, paths)
        if copied:
            notes.append("[roz-gate] copied %s into %s (worktree_copy, #122)"
                         % (", ".join(copied), wt))
        if unignored:
            notes.append("[roz-gate] did not copy %s into %s: git does not ignore it there, so "
                         "a commit could pick it up — add it to .gitignore, or drop it from "
                         "worktree_copy" % (", ".join(unignored), wt))
        if errors:
            notes.append("[roz-gate] could not copy %s into %s — the worktree lacks them"
                         % (", ".join(errors), wt))
    if notes:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": "\n".join(notes)}}))


if __name__ == "__main__":
    main()
