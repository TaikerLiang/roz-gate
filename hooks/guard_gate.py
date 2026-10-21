#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: trigger validation.

Invoked by guard-gate.sh only when a Bash command mentions a guarded
pattern. Nine rules, each the mechanical form of existing protocol text:

  A. An ``**[intake] · summary**`` comment may be posted only when the
     async-intake trigger holds (commands/patrol.md step 2): a gate label
     is present on the issue, or the gate holder's latest comment requests
     a summary (its first or last non-empty line is exactly ``summary``)
     and no intake summary has been posted after it.
  B. Gate labels (ready-for-spec / ready-for-dev) are applied by the human
     gate holder only — an agent never adds them (references/workflow.md:
     "you move gate labels — a gate label is an authorization").
  C. A forge comment that carries a roz-gate marker never OPENS with a
     quote block (commands/review-answers.md: "Never open with a quote
     block") — patrol classifies a comment by its opening token, so a
     quote-opening agent comment reads as a human answer and the loop
     replies to itself once per pass, dispatching seats and committing
     each time (the 1.11.0 runaway).
  D. A ``git commit`` never carries a ``technical-spec.md`` under the
     project's ``specs_dir`` that still holds an open-questions section
     (commands/next-stage.md A6: "move it … and delete it from the source
     document — the section goes"). The first opus baseline measured the
     prose at 0/5 AFTER it was made explicit: every run copied the
     question into spec.md, threaded it, and left the source untouched —
     a two-obligation instruction with the second silently dropped. The
     deny lands at the moment the agent can still act on it, and its
     message is the remedy. Working tree AND index are checked: a fixed
     file that was never re-staged would commit the stale section.
  F. A question comment lists its options as bullets (commands/next-stage.md
     A3, references/intake-brief.md: "the options as (a)/(b) bullets").
     Issue #109: a (2a) thread wrote them as prose — and the forge renders
     consecutive lines as one paragraph, so even options written one per
     line reach the gate holder's phone run together, with nothing for the
     ``3a`` shorthand to point at. Per question block (a stand-alone title
     line, ``**[<role>] · Q<k> · <label>**`` or ``**Q<n> · <label>**``, up
     to the next), fewer than two option bullets (``- (a) …``, any list
     marker) is a deny; a title whose line carries a ruling (``→ (a)``) or
     a resolution (``— resolved.``) is not a question — answers, folds and
     ledgers are out of scope by construction.
  G. A STOP comment names its resume move (references/workflow.md, the
     STOP protocol; issue #98). The ``blocked`` comment is what the gate
     holder reads on a phone; ADMC #73 saw them do the two natural things
     — leave ``blocked`` on, answer as a top-level CR comment — and neither
     was heard. The protocol fixes the must-read's first line (the title
     ``**[<command>] · blocked**``) and its last (``**To resume:**`` — the
     label to clear, the phase to apply, where the answer goes); a body
     carrying the title and no resume line is a deny.
  H. A CR-OPEN declares its contract deviations (commands/next-stage.md
     B4; issue #140, 2.0.0). The implementer corrects ``technical-spec.md``
     on its branch as it builds, and QA — which since 2.0.0 starts after
     the implementation lands — tests the contract as built; a correction
     nobody declared reaches QA and the (5) reviewer as a silent edit. A
     ``gh pr create`` / ``glab mr create`` whose head's diff against its
     base touches ``<specs_dir>/*/technical-spec.md`` must carry a line
     ``## Contract deviations`` in its body (``--body`` / ``--body-file`` /
     ``--description``, a file read back, a heredoc parsed — rule C's
     shapes). The diff is one ``git diff --name-only <base>...<head>``; the
     base is ``--base``, else gh's own default — the head branch's
     ``gh-merge-base`` config, else the repository default branch; a
     diff that cannot be computed fails CLOSED, and the message says it is
     the diff that failed, not the protocol.
  I. An ``**[intake] · reply**`` answers a human (commands/patrol.md,
     async-intake; issue #174). Since 2.5.0 patrol replies to the humans
     on an intake thread until the gate label — one reply per pass, every
     comment since the latest agent ``**[intake]`` comment. A comment body
     OPENING with the reply marker (a mention is not a write of one) is
     allowed only when a human comment follows the latest agent
     ``**[intake]`` comment, the issue has a human gate holder, and no
     gate label is present (finalize owns that). Not human: a body opening
     with an agent marker (the only test in user mode, where the agent
     posts as the holder's own login), a ``bot_login``, or the forge's bot
     shape — the gate-label audit's (references/patrol-scan.md): GitHub
     REST ``user.type`` ``Bot`` or a ``[bot]`` login, GitLab a
     ``project_<id>_bot_`` / ``group_<id>_bot_`` username, system notes
     dropped. GitHub reads REST ``issues/<n>/comments``: ``gh issue view
     --json comments`` carries neither the type nor the suffix. A second
     reply in one pass is denied by construction — the first is the latest
     ``**[intake]`` comment.
  J. The loop's ``git worktree add`` runs alone (references/workflow.md
     § The workspace; issue #122, codex review PR #184). The plugin's
     PostToolUse hook ``sync-worktree`` copies your gitignored files
     (``worktree_copy``, default ``.env``) into a worktree under
     ``<git-common-dir>/roz-gate/wt/`` only once the Bash call returns, so
     a command chained after the add in the same call — ``&& cd … &&
     <test>`` — runs without them, the harness red the copy exists to
     prevent. A Bash call holding such an add and any other top-level
     command (``&&``, ``||``, ``;``, ``|``, ``&``, a second line) is a deny.
     Top level: outside quotes and ``$(…)`` / backticks; ``2>&1`` and
     ``&>`` are redirects, and a backslash-newline continues the line. An
     add found anywhere outside quotes — inside ``{ …; }``, ``if …; then``,
     a subshell — passes only as the call's one and only command (codex
     review, PR #184).

Exit 0 allows the tool call; exit 2 blocks it and feeds stderr to the
model. Forge API failures fail closed, with a message that says it is an
API failure to retry, not a protocol block.

Identity modes (1.7.0): when the project's config block (``CLAUDE.md``,
else ``CLAUDE.local.md`` — hooks/config_block.py, #94) says
``agent_identity: bot``, ``bot_login`` names the agent's forge identity
(comma-separated for multiple bots). A bot is never a gate holder, and
"a summary was already posted" additionally requires the poster to BE the
bot — a human quoting the marker no longer counts. Absent config keys →
user mode, the pre-1.7.0 behavior bit for bit. Logins are normalized
before comparison (``app/`` prefix and ``[bot]`` suffix stripped): the
same bot surfaces as ``app/name``, ``name[bot]``, or bare ``name``
depending on the API path.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# The hook's own directory: guard-*.sh runs the file by path (sys.path[0] is
# this dir already); the lint tier and the D5 checker load it by
# spec_from_file_location, from elsewhere — the reader must still import.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_block import find_block  # noqa: E402

GATE = re.compile(r"ready-for-(spec|dev)")
# Rule B's fallback for a command shlex cannot tokenize: the value right
# after the add flag — `=`, or any run of shell whitespace and `\`-newline
# continuations (codex review, PR #100) — quoted to its closing quote, or
# bare to whitespace — names a gate label. A gate word anywhere else (the
# label being removed, a comment body) is not an add.
GATE_ADD_FALLBACK = re.compile(
    r"""--add-label(?:=|[\s\\]+)(?:"[^"]*|'[^']*|[^\s"']*)ready-for-(?:spec|dev)""")
GLAB_ADD_FALLBACK = re.compile(
    r"""(?:--label|-l)(?:=|[\s\\]+)(?:"[^"]*|'[^']*|[^\s"']*)ready-for-(?:spec|dev)""")
# Rule D's predicate — the same literal the E2 replay checker asserts
# (evals/replay/cases/E2/check.py) and the lint tier proves; the three
# are held byte-identical by lint E2's conformance layer.
OPEN_QUESTIONS_SECTION = re.compile(r"^#+ .*open questions", re.I | re.M)
DEFAULT_SPECS_DIR = "docs/specs"
SUMMARY_MARKER = re.compile(r"\[intake\]\**\s*[·•\-–—:|]\s*summary", re.IGNORECASE)
ROZ_MARKER = re.compile(r"\*\*\[|✅ \[")
# Rule I: the reply opens its body; the batch, the summary and the reply
# all open with the intake tag; the forge's bot shape (patrol-scan.md's
# gate-label audit) — GitHub's `[bot]` login, GitLab's project/group bot.
REPLY_OPEN = re.compile(r"^\s*\*\*\[intake\] · reply\*\*")
INTAKE_OPEN = re.compile(r"^\s*\*\*\[intake\]")
FORGE_BOT = re.compile(r"\[bot\]$|^(?:project|group)_\d+_bot_")
API_TIMEOUT = 20
# Rule J: the loop's worktree add — `git` (with `-C <dir>` / `-c k=v` before
# the verb) `worktree add`. LOOP_WT_ADD is the whole call; WT_ADD_ANYWHERE
# finds one inside any shell form (`{ …; }`, `if …; then`, a subshell).
LOOP_WT_ADD = re.compile(r"^\s*git(?:\s+-[Cc]\s+\S+)*\s+worktree\s+add\b")
WT_ADD_ANYWHERE = re.compile(r"\bgit\b(?:\s+-[Cc]\s+\S+)*\s+worktree\s+add\b")

RULE_B_MSG = (
    "Roz Gate: blocked — gate labels (ready-for-spec / ready-for-dev) are "
    "applied by the human gate holder only, never by an agent "
    "(references/workflow.md: 'you move gate labels — a gate label is an "
    "authorization'). Removing a gate label or adding track:/other status: "
    "labels is "
    "unaffected. If this issue should be gated, the gate holder applies the "
    "label themselves."
)

PROTOCOL_MSG = (
    "Roz Gate: blocked — the intake-summary trigger has not fired. An "
    "`**[intake] · summary**` comment is allowed only when the gate holder's "
    "(issue assignee; unassigned → author) latest comment requests a summary "
    "— its first or last line is exactly `summary` — or a gate label is "
    "already present (commands/patrol.md, async-intake). Answered questions "
    "alone never trigger a summary. Do not retry or work around this: it is "
    "a human decision point — wait for the gate holder."
)

ALREADY_POSTED_MSG = (
    "Roz Gate: blocked — an `**[intake] · summary**` comment was already "
    "posted after the gate holder's `summary` request. Post a new one only "
    "after the gate holder comments `summary` again."
)

QUOTE_OPEN_MSG = (
    "Roz Gate: blocked — an agent comment must open with its marker, never "
    "a quote block (commands/review-answers.md). Fix: put the marker on "
    "line one (`**[<role>] · <kind>**`) and the quote below it, or hand "
    "the text back to the human to post themselves. Why: patrol classifies "
    "a comment by its opening token — a quote-opening agent comment reads "
    "as a human answer, and the loop replies to itself once per pass."
)

# Rule F: a question block starts at a line that is only its title — bold
# optional (the #109 thread had none), a list item allowed — and runs to
# the next title. The label is free text (`Scope: exports`, `Sort
# (pagination)`, `… (story-level)`); what closes the line to a title is the
# tail: a ruling (`→`, or an `(a)`-shaped option anywhere on the line) or a
# resolution (`— resolved`) opens no block, nor does text after a closing
# `**`. Codex review, PR #112: the first cut excluded `(` and `:` from the
# label, and a `Scope: exports` question with prose options passed —
# the silent direction.
Q_TITLE = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?!.*(?:→|\([a-z]\)|[—–-]\s*resolved))"
    r"(?:\*\*)?(?:\[[^\]\n]+\] · )?(Q\d+) · \S[^\n*]*?(?:\*\*)?\s*$")
OPTION_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\([a-z]\)")
OPTIONS_MSG = (
    "Roz Gate: blocked — a question comment lists its options as bullets, "
    "one per line, and %s has none: `- (a) …` / `- (b) … ← ✅ recommended` "
    "(commands/next-stage.md A3; references/intake-brief.md). Why: the forge "
    "renders consecutive lines as one paragraph — options written as prose "
    "or as bare lines reach the gate holder's phone run together, and the "
    "shorthand reply (`3a`) has nothing to point at (issue #109)."
)

# Rule G: the STOP comment's two fixed lines (references/workflow.md, the
# STOP protocol). The title is the whole line — a title sharing its line
# (`**[next-stage] · blocked** — see below`) is prose quoting it; the resume
# line is the LAST non-empty line of the must-read (the text before the
# first `<details`). Codex review, PR #114: matched anywhere in the body, a
# `**To resume:**` pasted inside the folded evidence, or followed by more
# must-read prose, passed — the exact failure the rule exists for.
STOP_TITLE = re.compile(r"^\s*\*\*\[[^\]\n]+\] · blocked\*\*\s*$")
RESUME_LINE = re.compile(r"^\s*\*\*To resume:\*\*")
RESUME_MSG = (
    "Roz Gate: blocked — a STOP comment ends its must-read with the resume "
    "line — the last non-empty line before `<details>` — and this one does "
    "not: `**To resume:** clear status: blocked, apply status: <phase> — "
    "yourself, or tell the main agent; <where the answer goes>` on one line "
    "(references/workflow.md, the STOP protocol; the command's STOP section "
    "names its phase and channel). Why: the comment is what the gate holder "
    "reads on a phone — without the line they leave `blocked` on and answer "
    "where nothing listens (issue #98)."
)

BODY_FILE_MSG = (
    "Roz Gate: cannot judge this comment body — it arrives via --body-file "
    "from a source the guard cannot read, and the command carries a "
    "roz-gate marker. Post it with an inline --body/--message or a heredoc "
    "(--body-file - <<'EOF') so the guard can check that the comment opens "
    "with its marker, then retry."
)

UNPARSEABLE_MSG = (
    "Roz Gate: cannot verify the intake trigger — the issue number "
    "was not found in the command. Use the adapter form "
    "(`gh issue comment <number> ...` / `glab issue note <number> ...`) so "
    "the guard can check the issue."
)

# Rule H: the section heading, alone on its line — `## Contract deviations`
# (any heading level; trailing text such as ` — none` tolerated).
DEVIATIONS_HEADING = re.compile(r"^#+\s*Contract deviations\b", re.I | re.M)
DEVIATIONS_MSG = (
    "Roz Gate: blocked — this CR changes `%s` and its body has no "
    "`## Contract deviations` section. Add the section to the body — one "
    "bullet per changed clause (`G<k>` / `C<k>` / a §5 row): what changed and "
    "why; or the single line `none` — then retry (commands/next-stage.md B4). "
    "Why: the contract is corrected during implementation, and QA tests it as "
    "built; a correction nobody declared reaches QA and the reviewer as a "
    "silent edit (issue #140)."
)
DIFF_FAILED_MSG = (
    "Roz Gate: cannot verify this CR — the diff `%s...%s` could not be "
    "computed (%s), so the guard cannot tell whether `technical-spec.md` "
    "changed. This is NOT a protocol block: fetch the base and head refs "
    "(`git fetch origin`), or pass `--base` / `--head` (gh) or "
    "`--target-branch` / `--source-branch` (glab) naming refs this clone "
    "has, then retry."
)

OPEN_QUESTIONS_MSG = (
    "Roz Gate: blocked — `%s` (%s) still carries an open-questions section "
    "(`%s`). Move it to spec.md's `## Open Questions` and delete it here — "
    "the section goes; at most a one-line pointer to the Q-ID stays under "
    "another heading (commands/next-stage.md A6) — then `git add` the file "
    "and commit. Why: a question outside the threaded surface is invisible "
    "to every gate that counts threads, and a copy left behind drifts."
)

NO_HOLDER_MSG = (
    "Roz Gate: blocked — no human gate holder. The issue is bot-authored "
    "(a `bot_login` or a forge bot) and unassigned; a bot identity never "
    "holds a gate. A human assignee "
    "must exist before an intake summary can be posted — assign the issue "
    "and retry."
)


RULE_J_MSG = (
    "Roz Gate: blocked — the loop's `git worktree add` runs alone, as its own "
    "Bash call (references/workflow.md § The workspace). The plugin's "
    "sync-worktree hook copies your gitignored files (`worktree_copy`, default "
    "`.env`) into the new worktree only once the call returns, so anything "
    "chained after it in the same call (`&& cd … && <test>`) runs without "
    "them. Run the `git worktree add …` line by itself, then continue in the "
    "next call."
)

REPLY_MSG = (
    "Roz Gate: blocked — no human comment to answer. An `**[intake] · reply**` "
    "comment is allowed only when a human comment follows the latest agent "
    "`**[intake]` comment on the issue (commands/patrol.md, async-intake). Not "
    "human: a comment opening with an agent marker, a `bot_login`, or a forge "
    "bot (GitHub `type` Bot or a `[bot]` login; GitLab a `project_<id>_bot_` / "
    "`group_<id>_bot_` username, or a system note). Do not retry: the thread "
    "is waiting on the humans."
)

REPLY_GATE_MSG = (
    "Roz Gate: blocked — a gate label is on this issue, so finalize owns it, "
    "not a reply (commands/patrol.md, async-intake: the gate-label route "
    "comes first). Run the finalize route instead."
)

REPLY_TWICE_MSG = (
    "Roz Gate: blocked — this command posts two `**[intake] · reply**` "
    "comments on one issue. One reply per issue per pass, covering every "
    "human comment since the latest agent `**[intake]` comment "
    "(commands/patrol.md, async-intake): post one."
)

REPLY_NO_HOLDER_MSG = (
    "Roz Gate: blocked — no human gate holder. The issue is bot-authored "
    "(a `bot_login` or a forge bot) and unassigned; only the questions "
    "batch may be posted on it, never a reply (commands/patrol.md, "
    "async-intake). A human assignee must exist "
    "first — report the issue as needing one."
)


def normalize_login(login):
    """One rule for every author shape the forges return: strip gh's
    `app/` prefix and REST's `[bot]` suffix, leaving the bare slug."""
    login = (login or "").strip()
    if login.startswith("app/"):
        login = login[4:]
    if login.endswith("[bot]"):
        login = login[:-5]
    return login


def load_bot_logins():
    """Bot identities from the project's Roz Gate config block (`CLAUDE.md`,
    else `CLAUDE.local.md` — config_block.py; the block only).

    Empty set → user mode (pre-1.7.0 behavior). Comma-separated
    `bot_login` values are supported so a multi-bot future is a config
    edit, not a refactor. Located via the git toplevel — the command may
    run from a subdirectory.
    """
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if top.returncode != 0:
        return set()
    text = find_block(top.stdout.strip())
    if text is None:
        return set()
    if not re.search(r"^-\s*agent_identity:\s*bot\s*$", text, re.M):
        return set()
    m = re.search(r"^-\s*bot_login:\s*(.+)$", text, re.M)
    if not m:
        return set()
    return {
        normalize_login(v)
        for v in m.group(1).split(",")
        if normalize_login(v)
    }


def deny(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def git_out(*args):
    try:
        out = subprocess.run(["git"] + list(args), capture_output=True,
                             text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def load_specs_dir(top):
    """`specs_dir` from the project's Roz Gate config block (`CLAUDE.md`, else
    `CLAUDE.local.md` — config_block.py). None → not a roz-gate project (no
    config block anywhere): nothing to enforce. Block present but the key
    absent → the documented default, the same fallback /roz-gate:init
    writes (mirrors guard-acceptance)."""
    text = find_block(top)
    if text is None:
        return None
    m = re.search(r"^-\s*specs_dir:\s*(.+)$", text, re.M)
    return (m.group(1).strip().strip("`") if m else DEFAULT_SPECS_DIR)


def check_open_questions_commit(toks):
    """Rule D: judged only when a shell segment IS a git commit (first
    non-assignment token `git`, `commit` among its tokens) — a comment
    body that mentions committing is not one. Every technical-spec.md
    under specs_dir is read in the working tree and in the index; either
    carrying the section denies, naming which."""
    if toks is None:
        return
    def is_commit(seg):
        seg = [t for t in seg if "=" not in t] or [""]
        return seg[0] == "git" and "commit" in seg
    if not any(is_commit(seg) for seg in shell_segments(toks)):
        return
    top = (git_out("rev-parse", "--show-toplevel") or "").strip()
    if not top:
        return
    specs_dir = load_specs_dir(top)
    if not specs_dir:
        return
    pattern = specs_dir.strip("/") + "/*/technical-spec.md"
    rels = set()
    # Paths resolve against the toplevel, not the shell's cwd (the command
    # may run from a subdirectory).
    for line in (git_out("-C", top, "ls-files", "--cached", "--others",
                         "--exclude-standard", "--", pattern) or "").splitlines():
        if line.strip():
            rels.add(line.strip())
    for rel in sorted(rels):
        versions = []
        try:
            with open(top + "/" + rel, encoding="utf-8", errors="replace") as f:
                versions.append(("working tree", f.read()))
        except OSError:
            pass
        staged = git_out("-C", top, "show", ":" + rel)
        if staged is not None:
            versions.append(("staged — the index still has it; `git add` "
                             "after editing", staged))
        for where, text in versions:
            m = OPEN_QUESTIONS_SECTION.search(text)
            if m:
                deny(OPEN_QUESTIONS_MSG % (rel, where, m.group(0).strip()))


def check_cr_open(cmd, toks):
    """Rule H: a CR-OPEN whose diff touches a technical-spec.md under
    specs_dir carries `## Contract deviations` in its body. Judged per shell
    segment on the CR-shaped writes only (`gh pr create`, `glab mr create`);
    a repo without a config block is not a roz-gate project and is left
    alone; a diff the guard cannot compute fails closed."""
    if toks is None:
        return
    for seg in shell_segments(toks):
        gh_pr = "gh" in seg and "pr" in seg and "create" in seg
        glab_mr = "glab" in seg and "mr" in seg and "create" in seg
        if not (gh_pr or glab_mr):
            continue
        top = (git_out("rev-parse", "--show-toplevel") or "").strip()
        if not top:
            return
        specs_dir = load_specs_dir(top)
        if not specs_dir:
            return
        base = flag_value(seg, ["--base", "-B"] if gh_pr else ["--target-branch", "-b"])
        head = flag_value(seg, ["--head", "-H"] if gh_pr else ["--source-branch", "-s"])
        if not base and gh_pr:
            base = gh_merge_base(top, head)
        base_ref = resolve_ref(top, base) if base else resolve_ref(top, "origin/HEAD")
        head_ref = resolve_ref(top, head) if head else "HEAD"
        if base_ref is None or head_ref is None:
            deny(DIFF_FAILED_MSG % (base or "<base>", head or "HEAD",
                                    "ref not found: %s" % (base if base_ref is None else head)))
        changed = git_out("-C", top, "diff", "--name-only",
                          "%s...%s" % (base_ref, head_ref))
        if changed is None:
            deny(DIFF_FAILED_MSG % (base_ref, head_ref, "git diff failed"))
        want = specs_dir.strip("/") + "/*/technical-spec.md"
        hit = [p for p in changed.splitlines() if p.strip() and _spec_match(p.strip(), want)]
        if not hit:
            continue
        body = cr_body(cmd, seg, gh_pr)
        if not DEVIATIONS_HEADING.search(ansi_c(body or "")):
            deny(DEVIATIONS_MSG % hit[0])


def _spec_match(path, pattern):
    """`<specs_dir>/*/technical-spec.md` — one path segment for the issue."""
    pre, _, name = pattern.partition("/*/")
    rest = path[len(pre) + 1:] if path.startswith(pre + "/") else None
    return rest is not None and rest.count("/") == 1 and rest.endswith("/" + name)


def flag_value(toks, flags):
    for i, tok in enumerate(toks):
        for flag in flags:
            if tok == flag and i + 1 < len(toks):
                return toks[i + 1]
            if tok.startswith(flag + "="):
                return tok.split("=", 1)[1]
    return None


def gh_merge_base(top, head):
    """gh's own default for a `pr create` without `--base`: the head branch's
    `branch.<head>.gh-merge-base` config (set by `gh pr create` itself, or by
    a repo whose feature branches target a spec branch), else the repository
    default branch — `origin/HEAD` here (codex review, PR #143: judging
    against the default branch alone diffs a different pair than the CR
    being opened). `head` is the `--head` value, else the current branch."""
    branch = head or (git_out("-C", top, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    if not branch or branch == "HEAD":
        return None
    return (git_out("-C", top, "config", "--get",
                    "branch.%s.gh-merge-base" % branch) or "").strip() or None


def resolve_ref(top, ref):
    """The ref as given, else its `origin/` form (a worktree cut from
    `origin/<spec-branch>` may have no local `<spec-branch>`); None when
    neither resolves."""
    for cand in (ref, "origin/" + ref) if not ref.startswith("origin/") else (ref,):
        if git_out("-C", top, "rev-parse", "--verify", "-q", cand + "^{commit}") is not None:
            return cand
    return None


def cr_body(cmd, toks, gh_pr):
    """The CR body of one `pr create` / `mr create` segment: `--body`/`-b`,
    `--body-file`/`-F` (file read back, `-` heredoc parsed) for gh;
    `--description`/`-d` for glab. None when none is given (`--fill`, or a
    body to be filled in an editor)."""
    flags = ["--body", "-b"] if gh_pr else ["--description", "-d"]
    for i, tok in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        for flag in flags:
            if tok == flag and nxt is not None:
                return nxt
            if tok.startswith(flag + "="):
                return tok.split("=", 1)[1]
        if gh_pr and (tok in ("--body-file", "-F") or tok.startswith("--body-file=")):
            path = tok.split("=", 1)[1] if "=" in tok else nxt
            if path is not None:
                return body_from_file(path, cmd, deviations=True)
    return None


def deny_api_failure(detail):
    deny(
        "Roz Gate: could not verify the intake trigger — the forge "
        "API call failed (%s). This is NOT a protocol block: the command may "
        "be legitimate. Retry it shortly; if the forge stays unreachable, "
        "stop and report per the STOP protocol." % detail
    )


def forge_json(argv, pages=False):
    """One forge call's JSON. `pages`: `gh api --paginate` / `glab api
    --paginate` print one JSON array per page, back to back — their rows,
    flattened."""
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=API_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        deny_api_failure(str(exc))
    if out.returncode != 0:
        err = out.stderr.strip().splitlines()
        deny_api_failure(err[-1] if err else "exit %d" % out.returncode)
    try:
        if not pages:
            return json.loads(out.stdout)
        rows, text, i, dec = [], out.stdout, 0, json.JSONDecoder()
        while True:
            while i < len(text) and text[i].isspace():
                i += 1
            if i == len(text):
                return rows
            page, i = dec.raw_decode(text, i)
            rows.extend(page)
    except ValueError as exc:
        deny_api_failure("unparseable response: %s" % exc)


def check_gate_label_add(cmd, toks):
    """Rule B: block label-add flags whose value names a gate label."""
    if toks is None:
        # Shell we couldn't tokenize (an apostrophe in a heredoc body, say):
        # judge the add-label VALUE, not the whole command — "both halves
        # anywhere" denied the STOP protocol's own swap, `--remove-label
        # ready-for-dev --add-label "status: blocked"` beside a comment
        # body that said "didn't" (#94).
        if GATE_ADD_FALLBACK.search(cmd) or (
            "glab" in cmd and "update" in cmd and GLAB_ADD_FALLBACK.search(cmd)
        ):
            deny(RULE_B_MSG)
        return

    def flag_values(flags):
        vals = []
        for i, tok in enumerate(toks):
            for flag in flags:
                if tok == flag and i + 1 < len(toks):
                    vals.append(toks[i + 1])
                elif tok.startswith(flag + "="):
                    vals.append(tok.split("=", 1)[1])
        return vals

    added = []
    if "gh" in toks:
        # gh's only add flag; the list-filter flag is --label and stays free.
        added += flag_values(["--add-label"])
    if "glab" in toks and "update" in toks:
        # glab shares --label between `issue update` (add) and `issue list`
        # (filter) — only the update form is an add.
        added += flag_values(["--label", "-l"])
    if any(GATE.search(v) for v in added):
        deny(RULE_B_MSG)


def check_comment_writes(cmd, toks):
    """Rule C: a marker-carrying comment body never opens with a quote.

    Purely static — no forge call. Judged only on comment-shaped writes
    (issue/pr comment, issue/mr note, and the api comment/note/reply/
    discussion endpoints the adapters use) — a CR or issue *body* may
    legitimately open by quoting something. The marker condition is the
    scoping: an unmarked body is not a protocol write and this rule does
    not touch it. Leading blank lines and spaces count as opening with
    the quote (the forms a model produces when it formats carefully); a
    body whose FIRST LINE is the marker with a quote below is the
    prescribed remedy and passes. Blast radius: the runaway requires the
    *agent* to post the malformed comment — a human posting a
    quote-opening comment through the web UI is just a human comment and
    is SUPPOSED to read as unheard. So unlike gate labels, B4's whole
    threat surface sits inside what this client-side hook can see, and no
    repository-side enforcement is needed. A body arriving by command
    substitution (`--body "$(cat f)"`) is structurally invisible to any
    static hook and stays on the prose rule; `--body-file` is covered —
    file read back, heredoc parsed, anything else fails closed when the
    command shows a marker. Unparseable commands are left alone: without
    tokens there is no body to judge.

    Classification happens PER SHELL SEGMENT (tokens split on && / || /
    ; / |): in a compound line like `gh api -F pr=101 && gh issue
    comment 5 --body "**[...]"`, the api segment's `-F` must never be
    read as the comment segment's `--body-file` — that misattribution
    was a live false positive. The heredoc extraction stays against the
    WHOLE command text (a `--body-file -` heredoc body may itself
    contain separator-looking tokens; body_from_file never uses the
    segmentation).

    Rule F (#109) rides the same bodies: after the quote check, a question
    block without its option bullets is denied. Rule G (#98) too: a body
    titled ``**[<command>] · blocked**`` without its ``**To resume:**`` line.
    """
    if toks is None:
        return
    for seg in shell_segments(toks):
        for body in segment_bodies(cmd, seg):
            if not body:
                continue
            if quote_opening(body):
                deny(QUOTE_OPEN_MSG)
            q = question_without_options(body)
            if q:
                deny(OPTIONS_MSG % q)
            if stop_without_resume(body):
                deny(RESUME_MSG)


def shell_segments(toks):
    """Split a token list on shell separators. The tokenizer runs with
    punctuation_chars, so every operator — spaced or glued — arrives as
    its own token made purely of `();<>|&` characters. Redirects count
    as boundaries too, which is harmless: a body flag always sits left
    of its redirect."""
    segments, seg = [], []
    for tok in toks:
        if tok and not tok.strip("();<>|&"):
            segments.append(seg)
            seg = []
        else:
            seg.append(tok)
    segments.append(seg)
    return segments


def segment_bodies(cmd, toks):
    """The comment bodies of one shell segment — none unless it is a
    comment-shaped forge write (gh/glab comment or note, or an api call to a
    comments/replies/notes/discussions route)."""
    gh_comment = "gh" in toks and "comment" in toks and (
        "issue" in toks or "pr" in toks
    )
    glab_note = "glab" in toks and "note" in toks and (
        "issue" in toks or "mr" in toks
    )
    api_comment = "api" in toks and ("gh" in toks or "glab" in toks) and (
        re.search(r"/(comments|replies|notes|discussions)\b", " ".join(toks))
    )
    if not (gh_comment or glab_note or api_comment):
        return []
    return comment_bodies(cmd, toks, gh_comment, glab_note, api_comment)


def question_without_options(body):
    """Rule F's predicate: the first question block (Q_TITLE line to the
    next) with fewer than two OPTION_BULLET lines — its Q-ID, or None."""
    current, count = None, 0
    for line in ansi_c(body).splitlines():
        m = Q_TITLE.match(line)
        if m:
            if current and count < 2:
                return current
            current, count = m.group(1), 0
        elif current and OPTION_BULLET.match(line):
            count += 1
    return current if current and count < 2 else None


def stop_without_resume(body):
    """Rule G's predicate: a STOP_TITLE line, and the must-read (the text
    before the first `<details`; the whole body without one) does not end
    on a RESUME_LINE."""
    text = ansi_c(body)
    if not any(STOP_TITLE.match(ln) for ln in text.splitlines()):
        return False
    must_read = [ln for ln in text.split("<details", 1)[0].splitlines() if ln.strip()]
    return not (must_read and RESUME_LINE.match(must_read[-1]))


def comment_bodies(cmd, toks, gh_comment, glab_note, api_comment):
    """Comment-body strings in a forge write: `--body`/`-b` (gh comment),
    `--message`/`-m` (glab note), the `body=` field of
    `-f`/`-F`/`--field`/`--raw-field` in separated, `=`-joined, and glued
    spellings (gh/glab api), and gh's `--body-file`/`-F` (file path or
    stdin heredoc). Flags are collected per CLI shape so a compound
    command's other `-m` (e.g. git commit's) is never read as a body."""
    flags = []
    if gh_comment:
        flags += ["--body", "-b"]
    if glab_note:
        flags += ["--message", "-m"]
    vals = []
    for i, tok in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        for flag in flags:
            if tok == flag and nxt is not None:
                vals.append(nxt)
            elif tok.startswith(flag + "="):
                vals.append(tok.split("=", 1)[1])
        if api_comment:
            if tok in ("-f", "-F", "--field", "--raw-field") \
                    and nxt is not None and nxt.startswith("body="):
                vals.append(nxt.split("=", 1)[1])
            elif re.match(r"^(-[fF]|--field=|--raw-field=)body=", tok):
                vals.append(tok.split("body=", 1)[1])
        if gh_comment and (tok in ("--body-file", "-F")
                           or tok.startswith("--body-file=")):
            path = tok.split("=", 1)[1] if "=" in tok else nxt
            if path is not None:
                vals.append(body_from_file(path, cmd))
    return vals


def body_from_file(path, cmd, deviations=False):
    """gh's --body-file: the body is not an argument. `-` is stdin — in
    agent practice a heredoc whose text IS in the command; parse it out.
    A real path is read back from disk (it must exist for gh to work). A
    body the guard cannot see fails closed only when the command itself
    shows a marker — the scoping condition lives in the body, so an
    unmarked command stays free. For rule H (`deviations=True`) the scoping
    condition is the diff, already decided: an unreadable body is an
    unreadable body, and it fails closed."""
    if path == "-":
        m = re.search(
            r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2\s*(?:\n|$)",
            cmd, re.S,
        )
        if m:
            return m.group(3)
    else:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            pass
    if deviations:
        deny(BODY_FILE_MSG.replace("the command carries a roz-gate marker",
                                   "the CR changes technical-spec.md (rule H)"))
    if ROZ_MARKER.search(cmd):
        deny(BODY_FILE_MSG)
    return None


def ansi_c(body):
    """bash ANSI-C $'...' reaches shlex as `$` + content with literal \\n
    escapes; normalize enough to judge lines and openings."""
    if body.startswith("$"):
        return body[1:].replace("\\n", "\n").replace("\\t", "\t")
    return body


def quote_opening(body):
    body = ansi_c(body)
    return bool(ROZ_MARKER.search(body)) and body.lstrip().startswith(">")


def is_summary_request(body):
    """First or last non-empty line is exactly `summary` (emphasis,
    backticks, quotes, and a trailing period stripped; case-insensitive) —
    so corrections and the request can share one comment."""
    lines = [line.strip().strip("`'\"*.").strip() for line in body.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return False
    return "summary" in (lines[0].casefold(), lines[-1].casefold())


def resolve_holders(assignee_logins, author_login, bots, no_holder_msg=None):
    """Gate holders: assignees, unassigned → author — humans only. A bot
    is never a gate holder; bot-authored + unassigned = no holder."""
    holders = {normalize_login(a) for a in assignee_logins if a} - bots
    if not holders:
        author = normalize_login(author_login)
        if author and author not in bots:
            holders = {author}
    if not holders:
        deny(no_holder_msg or NO_HOLDER_MSG)
    return holders


def forge_holders(forge, issue, bots, no_holder_msg=None):
    """Rules A and I resolve the holder here, from one issue view: a
    forge-shaped bot never holds a gate either, configured or not — gh's
    `author.is_bot`, and FORGE_BOT on every assignee and the author (codex
    review, PR #175; #176)."""
    key = "login" if forge == "gh" else "username"
    assignees = [a.get(key) for a in issue.get("assignees") or []
                 if not FORGE_BOT.search(a.get(key) or "")]
    author = issue.get("author") or {}
    login = author.get(key)
    if author.get("is_bot") or FORGE_BOT.search(login or ""):
        login = None
    return resolve_holders(assignees, login, bots, no_holder_msg)


def check_trigger(holders, comments, bots):
    """comments: oldest-first list of (author_login, body); logins are
    compared normalized."""
    last_holder_idx = None
    for i, (login, _body) in enumerate(comments):
        if normalize_login(login) in holders:
            last_holder_idx = i
    if last_holder_idx is None or not is_summary_request(comments[last_holder_idx][1]):
        deny(PROTOCOL_MSG)
    for login, body in comments[last_holder_idx + 1:]:
        # In bot mode a posted summary must also BE the bot's — a human
        # quoting the marker doesn't count.
        if SUMMARY_MARKER.search(body) and (
            not bots or normalize_login(login) in bots
        ):
            deny(ALREADY_POSTED_MSG)


def check_github_summary(cmd, bots):
    m = re.search(r"\bgh\s+issue\s+comment\s+(\S+)", cmd)
    if not m:
        return
    number = m.group(1)
    if not number.isdigit():
        deny(UNPARSEABLE_MSG)
    issue = forge_json(
        ["gh", "issue", "view", number, "--json", "assignees,author,labels,comments"]
    )
    labels = [lab.get("name", "") for lab in issue.get("labels") or []]
    if any(GATE.search(name) for name in labels):
        return  # finalize path: the gate holder's label authorizes the summary
    holders = forge_holders("gh", issue, bots)
    comments = sorted(issue.get("comments") or [], key=lambda c: c.get("createdAt", ""))
    check_trigger(
        holders,
        [((c.get("author") or {}).get("login"), c.get("body", "")) for c in comments],
        bots,
    )


def check_gitlab_summary(cmd, bots):
    m = re.search(r"\bglab\s+issue\s+note\s+(\S+)", cmd)
    if not m:
        return
    number = m.group(1)
    if not number.isdigit():
        deny(UNPARSEABLE_MSG)
    issue = forge_json(["glab", "issue", "view", number, "--output", "json"])
    labels = issue.get("labels") or []
    if any(GATE.search(name) for name in labels):
        return
    holders = forge_holders("glab", issue, bots)
    # Every page: a page is 100 notes, and the request or an already-posted
    # summary may sit past the first (#176).
    notes = forge_json(["glab", "api", "--paginate",
                        "projects/:id/issues/%s/notes?per_page=100" % number], pages=True)
    notes = sorted(
        (n for n in notes if not n.get("system")),
        key=lambda n: n.get("created_at", ""),
    )
    check_trigger(
        holders,
        [((n.get("author") or {}).get("username"), n.get("body", "")) for n in notes],
        bots,
    )


def is_human(login, body, forge_type, bots):
    """Rule I's human-comment test — the scanner's (references/patrol-scan.md
    § The human-comment test): an agent-marker opening, a `bot_login`, or
    the forge's bot shape is not a human."""
    if ROZ_MARKER.match(ansi_c(body or "").lstrip()):
        return False
    if forge_type == "Bot" or FORGE_BOT.search(login or ""):
        return False
    return normalize_login(login or "") not in bots


def check_reply_trigger(comments, bots):
    """comments: oldest-first (login, body, forge type). In bot mode the
    latest agent `**[intake]` comment must also BE the bot's, as rule A's
    already-posted test."""
    last = None
    for i, (login, body, _type) in enumerate(comments):
        if INTAKE_OPEN.match(ansi_c(body or "")) and (
            not bots or normalize_login(login or "") in bots
        ):
            last = i
    if last is None or not any(is_human(*c, bots) for c in comments[last + 1:]):
        deny(REPLY_MSG)


def reply_target(seg):
    """(forge, issue number) of a comment-shaped segment: `gh issue comment
    <n>` / `glab issue note <n>`, or an api route on issues/<n>/comments|notes."""
    forge = "glab" if "glab" in seg else "gh"
    if "api" in seg:
        for tok in seg:
            m = re.search(r"issues/([^/\s]+)/(?:comments|notes)\b", tok)
            if m:
                return forge, m.group(1)
        return forge, None
    verb = "note" if forge == "glab" else "comment"
    i = seg.index(verb) if verb in seg else -1
    return forge, (seg[i + 1] if 0 <= i < len(seg) - 1 else None)


def check_intake_reply(cmd, toks):
    """Rule I (#174): a body opening with `**[intake] · reply**` answers a
    human, on an issue with a human holder and no gate label."""
    if toks is None:
        return
    seen = set()
    for seg in shell_segments(toks):
        if not any(b and REPLY_OPEN.match(ansi_c(b)) for b in segment_bodies(cmd, seg)):
            continue
        forge, number = reply_target(seg)
        if not (number or "").isdigit():
            deny(UNPARSEABLE_MSG)
        # Every segment is judged against the same pre-command forge state:
        # a second reply to one issue in one command would pass on the
        # first one's human comment (codex review, PR #175). The CLIs read
        # the number as an integer — `07` is #7; the key is per forge
        # (codex review, PR #177).
        number = str(int(number))
        if (forge, number) in seen:
            deny(REPLY_TWICE_MSG)
        seen.add((forge, number))
        bots = load_bot_logins()
        if forge == "gh":
            issue = forge_json(["gh", "issue", "view", number, "--json",
                                "assignees,author,labels"])
            labels = [lab.get("name", "") for lab in issue.get("labels") or []]
            rows = forge_json(["gh", "api", "repos/{owner}/{repo}/issues/%s/comments" % number,
                               "--paginate"], pages=True)
            comments = [((c.get("user") or {}).get("login"), c.get("body", ""),
                         (c.get("user") or {}).get("type"))
                        for c in sorted(rows, key=lambda c: c.get("created_at", ""))]
        else:
            issue = forge_json(["glab", "issue", "view", number, "--output", "json"])
            labels = issue.get("labels") or []
            notes = forge_json(["glab", "api", "--paginate",
                                "projects/:id/issues/%s/notes?per_page=100" % number],
                               pages=True)
            comments = [((n.get("author") or {}).get("username"), n.get("body", ""), None)
                        for n in sorted((n for n in notes if not n.get("system")),
                                        key=lambda n: n.get("created_at", ""))]
        if any(GATE.search(name) for name in labels):
            deny(REPLY_GATE_MSG)
        forge_holders(forge, issue, bots, REPLY_NO_HOLDER_MSG)
        check_reply_trigger(comments, bots)


def top_level_segments(cmd):
    """The command's top-level segments, split on `&&`, `||`, `;`, `|`, `&`
    and an unescaped newline — never inside quotes, `$(…)` or backticks.
    `>&` / `&>` are redirects (`2>&1`), not separators. shlex cannot do
    this: its punctuation split breaks `$(git rev-parse …)` apart."""
    segs, cur, i, n = [], [], 0, len(cmd)
    quote, depth, tick = None, 0, False
    while i < n:
        ch = cmd[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                cur.append(cmd[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch == "\\" and i + 1 < n:      # an escaped char, a newline included
            cur.append(ch + cmd[i + 1])        # (backslash-newline continues the line)
            i += 1
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch == "`":
            tick = not tick
            cur.append(ch)
        elif cmd.startswith("$(", i):
            depth += 1
            cur.append("$(")
            i += 1
        elif ch == ")" and depth:
            depth -= 1
            cur.append(ch)
        elif depth or tick:
            cur.append(ch)
        elif ch == "&" and ((i > 0 and cmd[i - 1] == ">") or cmd.startswith(">", i + 1)):
            cur.append(ch)                    # 2>&1, &>file: a redirect
        elif ch in "&|;\n":
            segs.append("".join(cur))
            cur = []
            if cmd.startswith(ch * 2, i) and ch in "&|":
                i += 1
        else:
            cur.append(ch)
        i += 1
    segs.append("".join(cur))
    return [seg.strip() for seg in segs if seg.strip()]


def unquoted(cmd):
    """`cmd` with every quoted string's contents removed — what the shell
    runs as words, not what it passes as text."""
    out, quote, i = [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "\\" and i + 1 < len(cmd):
            out.append(cmd[i:i + 2])
            i += 1
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def check_worktree_add_alone(cmd):
    """Rule J (#122): a call that runs the loop's `git worktree add` runs
    nothing else — the add, alone, is the whole call; any other shape that
    holds one (a chain, `{ …; }`, `if …; then`, a subshell) is a deny."""
    if "worktree" not in cmd or "roz-gate/wt" not in cmd:
        return
    if not WT_ADD_ANYWHERE.search(unquoted(cmd)):
        return
    segs = top_level_segments(cmd)
    if not (len(segs) == 1 and LOOP_WT_ADD.match(segs[0])):
        deny(RULE_J_MSG)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("tool_name") not in (None, "Bash"):
        return
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return
    try:
        # punctuation_chars so unspaced operators (`x=y&&gh`, `50|head`)
        # come out as standalone tokens — token-equality segmentation is
        # then complete, not an enumeration of spaced spellings (the B1
        # lesson: fix the class, not the instance). Quoted bodies are
        # unaffected; punctuation inside quotes is never split.
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        toks = None
    check_gate_label_add(cmd, toks)
    check_comment_writes(cmd, toks)
    check_open_questions_commit(toks)
    check_cr_open(cmd, toks)
    check_intake_reply(cmd, toks)
    check_worktree_add_alone(cmd)
    if SUMMARY_MARKER.search(cmd):
        bots = load_bot_logins()
        check_github_summary(cmd, bots)
        check_gitlab_summary(cmd, bots)


main()
