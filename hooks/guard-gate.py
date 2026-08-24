#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: trigger validation.

Invoked by guard-gate.sh only when a Bash command mentions a guarded
pattern. Three rules, each the mechanical form of existing protocol text:

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

Exit 0 allows the tool call; exit 2 blocks it and feeds stderr to the
model. Forge API failures fail closed, with a message that says it is an
API failure to retry, not a protocol block.

Identity modes (1.7.0): when the project's CLAUDE.md config block says
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
import re
import shlex
import subprocess
import sys

GATE = re.compile(r"ready-for-(spec|dev)")
SUMMARY_MARKER = re.compile(r"\[intake\]\**\s*[·•\-–—:|]\s*summary", re.IGNORECASE)
ROZ_MARKER = re.compile(r"\*\*\[|✅ \[")
API_TIMEOUT = 20

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

BODY_FILE_MSG = (
    "Roz Gate: cannot judge this comment body — it arrives via --body-file "
    "from a source the guard cannot read, and the command carries a "
    "roz-gate marker. Post it with an inline --body/--message or a heredoc "
    "(--body-file - <<'EOF') so the guard can check that the comment opens "
    "with its marker, then retry."
)

UNPARSEABLE_MSG = (
    "Roz Gate: cannot verify the intake-summary trigger — the issue number "
    "was not found in the command. Use the adapter form "
    "(`gh issue comment <number> ...` / `glab issue note <number> ...`) so "
    "the guard can check the issue."
)

NO_HOLDER_MSG = (
    "Roz Gate: blocked — no human gate holder. The issue is bot-authored "
    "and unassigned; a bot identity never holds a gate. A human assignee "
    "must exist before an intake summary can be posted — assign the issue "
    "and retry."
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
    """Bot identities from the project's CLAUDE.md Roz Gate config block.

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
        if top.returncode != 0:
            return set()
        with open(top.stdout.strip() + "/CLAUDE.md", encoding="utf-8") as f:
            text = f.read()
    except (OSError, subprocess.TimeoutExpired):
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


def deny_api_failure(detail):
    deny(
        "Roz Gate: could not verify the intake-summary trigger — the forge "
        "API call failed (%s). This is NOT a protocol block: the command may "
        "be legitimate. Retry it shortly; if the forge stays unreachable, "
        "stop and report per the STOP protocol." % detail
    )


def forge_json(argv):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=API_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        deny_api_failure(str(exc))
    if out.returncode != 0:
        err = out.stderr.strip().splitlines()
        deny_api_failure(err[-1] if err else "exit %d" % out.returncode)
    try:
        return json.loads(out.stdout)
    except ValueError as exc:
        deny_api_failure("unparseable response: %s" % exc)


def check_gate_label_add(cmd, toks):
    """Rule B: block label-add flags whose value names a gate label."""
    if toks is None:
        # Shell we couldn't tokenize; conservative when both halves appear.
        if re.search(r"--(add-)?label", cmd) and GATE.search(cmd):
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


def check_quote_open(cmd, toks):
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
    """
    if toks is None:
        return
    for seg in shell_segments(toks):
        check_quote_open_segment(cmd, seg)


def shell_segments(toks):
    """Split a token list on shell separators. shlex keeps `&&`/`||`/`|`
    as their own tokens but glues `;` to the preceding word — both forms
    are boundaries."""
    segments, seg = [], []
    for tok in toks:
        if tok in ("&&", "||", ";", "|", "|&"):
            segments.append(seg)
            seg = []
        elif tok.endswith(";") and not tok.startswith("-"):
            seg.append(tok[:-1])
            segments.append(seg)
            seg = []
        else:
            seg.append(tok)
    segments.append(seg)
    return segments


def check_quote_open_segment(cmd, toks):
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
        return
    for body in comment_bodies(cmd, toks, gh_comment, glab_note, api_comment):
        if body and quote_opening(body):
            deny(QUOTE_OPEN_MSG)


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


def body_from_file(path, cmd):
    """gh's --body-file: the body is not an argument. `-` is stdin — in
    agent practice a heredoc whose text IS in the command; parse it out.
    A real path is read back from disk (it must exist for gh to work). A
    body the guard cannot see fails closed only when the command itself
    shows a marker — the scoping condition lives in the body, so an
    unmarked command stays free."""
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
    if ROZ_MARKER.search(cmd):
        deny(BODY_FILE_MSG)
    return None


def quote_opening(body):
    if body.startswith("$"):
        # bash ANSI-C $'...' reaches shlex as `$` + content with literal
        # \n escapes; normalize enough to judge the opening.
        body = body[1:].replace("\\n", "\n").replace("\\t", "\t")
    return bool(ROZ_MARKER.search(body)) and body.lstrip().startswith(">")


def is_summary_request(body):
    """First or last non-empty line is exactly `summary` (emphasis,
    backticks, quotes, and a trailing period stripped; case-insensitive) —
    so corrections and the request can share one comment."""
    lines = [l.strip().strip("`'\"*.").strip() for l in body.splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return False
    return "summary" in (lines[0].casefold(), lines[-1].casefold())


def resolve_holders(assignee_logins, author_login, bots):
    """Gate holders: assignees, unassigned → author — humans only. A bot
    is never a gate holder; bot-authored + unassigned = no holder."""
    holders = {normalize_login(a) for a in assignee_logins if a} - bots
    if not holders:
        author = normalize_login(author_login)
        if author and author not in bots:
            holders = {author}
    if not holders:
        deny(NO_HOLDER_MSG)
    return holders


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
    labels = [l.get("name", "") for l in issue.get("labels") or []]
    if any(GATE.search(name) for name in labels):
        return  # finalize path: the gate holder's label authorizes the summary
    holders = resolve_holders(
        (a.get("login") for a in issue.get("assignees") or []),
        (issue.get("author") or {}).get("login"),
        bots,
    )
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
    holders = resolve_holders(
        (a.get("username") for a in issue.get("assignees") or []),
        (issue.get("author") or {}).get("username"),
        bots,
    )
    notes = forge_json(
        ["glab", "api", "projects/:id/issues/%s/notes?per_page=100" % number]
    )
    notes = sorted(
        (n for n in notes if not n.get("system")),
        key=lambda n: n.get("created_at", ""),
    )
    check_trigger(
        holders,
        [((n.get("author") or {}).get("username"), n.get("body", "")) for n in notes],
        bots,
    )


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
        toks = shlex.split(cmd, posix=True)
    except ValueError:
        toks = None
    check_gate_label_add(cmd, toks)
    check_quote_open(cmd, toks)
    if SUMMARY_MARKER.search(cmd):
        bots = load_bot_logins()
        check_github_summary(cmd, bots)
        check_gitlab_summary(cmd, bots)


main()
