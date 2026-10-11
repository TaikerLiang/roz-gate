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
is. The dispatching command writes
``$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch`` immediately
before the Task call and removes it after the dispatch returns; the rule is
ON exactly while the file exists. The COMMON git dir is shared by the
checkout and every linked worktree (commands work in worktrees, issue
#37), so the marker governs a dispatch whatever its cwd; never tracked,
never in git status.
Fail-safe direction: a stale marker (the dispatch crashed) keeps the rule
ON — over-blocking a later non-blind read is a visible nuisance, and the
deny message names the file to remove; under-blocking a fidelity read is
the invisible failure this rule closes. ``agent_type`` is reported in the
message when present, never relied on.

The marker's content (1.29.0, references/branch-names.md): a repo whose
``branch_template`` names the implementation branch ``fix/pwliangc/5/1``
has no ``feat/`` ref to deny, so the dispatching command writes
``feat=<the bound implementation branch>`` into the marker and a git
action on THAT ref is denied too — the same verbs, the exact name. The
``feat/`` literal stays denied regardless (the pre-template rule, and the
D2 predicate held byte-identical with the checker); an empty or
``issue=``-only marker is the 1.16–1.28 shape and enforces exactly what
it did.

Exit 0 allows the tool call; exit 2 blocks it and feeds stderr to the
model.
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
from config_block import find_block  # noqa: E402

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


def bash_reads_src(cmd, suite=None, top=None):
    cmd = SRC_MENTIONED.sub(" ", SRC_EXCLUDED.sub(" ", cmd))
    if suite:
        cmd = suite_operand_re(suite, top).sub(suite_blanker(suite, top), cmd)
    return SRC_PATH.search(cmd) is not None
# --------------------------------------------------------------------------

# ---- the suite is not the implementation (issue #81, 1.29.1) -------------
# A Maven/Gradle layout keeps the acceptance suite under src/test/…; the
# predicate above read `src/test/java/acme/acceptance/T.java` as a read of
# the implementation, and the fidelity dispatch could not read the very
# suite it audits. The block's `acceptance_dir` is where the suite is —
# "what you need is on qa/<n>" — so an operand or a tool path under it is
# never a read of src/. Only a suite under a `src/` segment gets an
# exemption — `src/test/…`, or a multi-module `<module>/src/test/…` (#94:
# the first cut required `src` to be the FIRST segment, and every Maven
# multi-module layout was denied its own suite); `tests/acceptance` has
# nothing to exempt, and `src` or `<module>/src` itself would swallow the
# rule and exempts nothing. A Bash operand that climbs out of the suite
# (`…/acceptance/../../main/java/App.java`) is not blanked; a tool path is
# normalized before the containment test, so the climb lands where it
# really points. The four regexes above are untouched (lint D2 holds them
# byte-identical to the replay checker).
DEFAULT_ACCEPTANCE_DIR = "tests/acceptance"


def load_acceptance_dir(top):
    """`acceptance_dir` from the project's Roz Gate config block — `CLAUDE.md`,
    else `CLAUDE.local.md`, here or in the main checkout (config_block.py);
    the block only, as guard_acceptance reads it. None → not a roz-gate
    project, or no toplevel."""
    blk = find_block(top)
    if blk is None:
        return None
    m = re.search(r"^-\s*acceptance_dir:\s*(.+)$", blk, re.M)
    return m.group(1).strip().strip("`") if m else DEFAULT_ACCEPTANCE_DIR


def suite_under_src(acceptance_dir):
    """The suite's repo-relative path when it sits under a `src/` segment —
    `src/test/…` or `<module>/src/test/…` — else None."""
    if not acceptance_dir:
        return None
    segs = [x for x in os.path.normpath(acceptance_dir).replace(os.sep, "/").split("/")
            if x not in (".", "")]
    if ".." in segs or "src" not in segs or segs.index("src") == len(segs) - 1:
        return None
    return "/".join(segs)


def suite_operand_re(suite, top):
    """A shell operand naming the suite: relative (`src/test/…`, `./src/test/…`,
    after `)/` as in `$(git rev-parse --show-toplevel)/src/test/…`) or absolute
    (any `/…/<suite>…`); the suite dir itself or anything below it, never a
    sibling such as `…/acceptance-old/`. The operand ends at whitespace, a
    quote or a shell control / redirection character — `cat <suite>/T;cat
    <src/main/App` is two operands, and the second is a read (codex review,
    PR #84). Spelling is only the candidate: the blanker resolves it."""
    quoted = re.escape(suite)
    tail = r"(?![\w.-])[^\s'\"<>|;&()]*"
    forms = [r"(?:(?<![\w.\-/])|(?<=\)/))(?:\./)?" + quoted + tail]
    if top:
        forms.append(r"(?<![\w.-])/[^\s'\"<>|;&()]*?/" + quoted + tail)
    return re.compile("|".join(forms))


def resolves_under_suite(path, suite, top):
    """The operand's REAL location is at or under the toplevel's suite:
    `realpath` resolves `..` and symlinks alike, so a climb out of the suite
    (`…/acceptance/../../main/…`), a symlink inside it that points out
    (`…/acceptance/impl → ../../../../main`, codex review, PR #84), another
    tree's `src/test/…`, and a toplevel spelled through a symlink (macOS's
    `/var/…` for `/private/var/…`) all land where they really point. The
    suite dir itself is joined lexically — a suite that is itself a symlink
    out of src/ exempts nothing."""
    if not top:
        return False
    want = os.path.join(os.path.realpath(top), suite)
    rp = os.path.realpath(path if os.path.isabs(path) else os.path.join(top, path))
    return rp == want or rp.startswith(want + "/")


def suite_blanker(suite, top):
    def blank(m):
        return " " if resolves_under_suite(m.group(0), suite, top) else m.group(0)
    return blank


def under_suite(path, suite, top):
    """A tool path (absolute or repo-relative) whose real location is at or
    under the suite — the same resolution as a Bash operand."""
    return resolves_under_suite(path, suite, top)


def tool_reads_src(tool, inp, suite=None, top=None):
    """A Read/Glob/Grep input naming src/ — unless every such value is under the suite."""
    if not suite:
        return SRC_PATH.search(json.dumps(inp, ensure_ascii=False)) is not None
    for v in inp.values():
        text = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        if SRC_PATH.search(text) and not (isinstance(v, str) and under_suite(v, suite, top)):
            return True
    return False

BLIND_MSG = (
    "Roz Gate: blocked — this is a fidelity dispatch and it is "
    "implementation-blind: `src/` and `feat/<n>` are off-limits (%s). What "
    "you need is in spec.md / technical-spec.md and the QA suite on "
    "qa/<n>%s. If you believe a read of the implementation is required, "
    "report it as a finding instead of performing it "
    "(references/fidelity-brief.md, the blindness rule). Not inside a "
    "fidelity dispatch? Then the marker is stale — the dispatching command "
    "removes `%s` when the dispatch returns; remove it and retry.%s"
)


def deny(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def marker_path():
    # The COMMON dir, not --git-dir: a dispatch runs in a linked worktree
    # (commands/next-stage.md B5b), whose own git dir is
    # <common>/worktrees/<name>; the marker written from the checkout would
    # be invisible there and the rule silently OFF (codex review, PR #53).
    try:
        out = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return os.path.abspath(out.stdout.strip()) + "/" + MARKER_REL


def marker_ref(path):
    """The implementation branch the marker names (`feat=<branch>`), or None."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("feat="):
                    return line[len("feat="):].strip() or None
    except (OSError, TypeError):
        pass
    return None


def ref_touch_re(ref):
    """GIT_TOUCH's shape for one exact ref: the same verbs, the bound name
    (not a prefix — `fix/paul/5/1` must not deny `fix/paul/5/10`; a leading
    `origin/` is still that ref)."""
    return re.compile(
        r"\bgit\b[^|;&\n]*\b(checkout|switch|diff|show|log|merge|restore"
        r"|worktree)\b[^|;&\n]*(?<![\w-])" + re.escape(ref) + r"(?![\w-])")


def violation(tool, inp, ref=None, suite=None, top=None):
    """The D2 checker's dispatch_blind(), per call: what it names. `suite`
    is the acceptance dir when it sits under src/ (never a read); `top`
    the repo toplevel the absolute forms resolve against."""
    if tool == "Bash":
        cmd = inp.get("command") or ""
        if GIT_TOUCH.search(cmd):
            return "a git action on a feat/ ref"
        if ref and ref_touch_re(ref).search(cmd):
            return "a git action on %s, the implementation branch" % ref
        if bash_reads_src(cmd, suite, top):
            return "a read of src/"
    elif tool in ("Read", "Glob", "Grep"):
        if tool_reads_src(tool, inp, suite, top):
            return "a %s under src/" % tool
    return None


def toplevel():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    tool = payload.get("tool_name")
    if tool not in ("Bash", "Read", "Glob", "Grep"):
        return
    inp = payload.get("tool_input") or {}
    marker = marker_path()
    top = toplevel()
    suite = suite_under_src(load_acceptance_dir(top))
    what = violation(tool, inp, marker_ref(marker), suite, top)
    if not what:
        return
    agent = payload.get("agent_type")
    deny(BLIND_MSG % (what, " (its `%s` is readable here)" % suite if suite else "",
                      marker or "<git-dir>/" + MARKER_REL,
                      " (agent: %s)" % agent if agent else ""))


if __name__ == "__main__":
    main()
