"""`implementation_dirs` — the one reader of the key (#281).

The project's Roz Gate config block may carry

    - implementation_dirs: lib, app

the repo-relative directories that hold the implementation. guard-blind
rule E enforces the list; `bin/roz-implementation-dirs` renders the same
list as the dispatch's `Implementation:` line. Both call `load()` — there
is no second parse, so what a blind seat is told and what the hook denies
cannot disagree.

`load(top)` returns
  None       the key is absent (or this is no roz-gate project): rule E
             guards `src/` and `<module>/src/`, as it always has;
  a tuple    the normalized directories, in order, without repeats — the
             list REPLACES the default (`src/` is special only if listed);
  Invalid    the line is there and cannot be used; `.reason` says why.

A value is comma-separated; backticks, quotes, a leading `./` and a
trailing `/` are dropped. Invalid: no directory at all, an empty entry, an
absolute path, a `..` segment, the repo root itself.

Stdlib only, Python 3.9-compatible.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_block import find_block  # noqa: E402

KEY = "implementation_dirs"
LINE = re.compile(r"^-[ \t]*%s:[ \t]*(.*)$" % KEY, re.M)
SHAPE = "- %s: <dir>[, <dir>…]" % KEY


class Invalid:
    """The line as written, and why it cannot be used."""

    def __init__(self, raw, reason):
        self.raw, self.reason = raw, reason


def parse(raw):
    """The normalized directories of one value, or Invalid."""
    value = raw.strip()
    if not value.strip("`'\" \t"):
        return Invalid(raw, "it names no directory")
    dirs = []
    for part in value.split(","):
        entry = part.strip().strip("`'\"").strip()
        if not entry:
            return Invalid(raw, "it has an empty entry")
        if entry.startswith("/") or re.match(r"[A-Za-z]:[\\/]", entry):
            return Invalid(raw, "`%s` is an absolute path — give it relative to the repo root"
                           % entry)
        segs = [s for s in entry.replace("\\", "/").split("/") if s not in ("", ".")]
        if ".." in segs:
            return Invalid(raw, "`%s` climbs with `..`" % entry)
        if not segs:
            return Invalid(raw, "`%s` is the repo root — that would hide everything" % entry)
        norm = "/".join(segs)
        if norm not in dirs:
            dirs.append(norm)
    return tuple(dirs)


def load(top):
    """See the module docstring. `top` is a working tree's toplevel; the
    block is found as every reader finds it (config_block.find_block)."""
    blk = find_block(top)
    if blk is None:
        return None
    m = LINE.search(blk)
    return parse(m.group(1)) if m else None


def render(dirs):
    """The dispatch line for a loaded list."""
    return "Implementation: %s" % ", ".join(dirs)
