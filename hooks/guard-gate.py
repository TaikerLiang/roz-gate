#!/usr/bin/env python3
"""Roz Gate enforcement — layer 2: trigger validation.

Invoked by guard-gate.sh only when a Bash command mentions a guarded
pattern. Two rules, each the mechanical form of existing protocol text:

  A. An ``**[intake] · summary**`` comment may be posted only when the
     async-intake trigger holds (commands/patrol.md step 2): a gate label
     is present on the issue, or the gate holder's latest comment requests
     a summary (its first or last non-empty line is exactly ``summary``)
     and no intake summary has been posted after it.
  B. Gate labels (ready-for-spec / ready-for-dev) are applied by the human
     gate holder only — an agent never adds them (references/workflow.md:
     "you move gate labels — a gate label is an authorization").

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
    if SUMMARY_MARKER.search(cmd):
        bots = load_bot_logins()
        check_github_summary(cmd, bots)
        check_gitlab_summary(cmd, bots)


main()
