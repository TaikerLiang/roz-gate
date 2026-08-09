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


def check_trigger(holders, comments):
    """comments: oldest-first list of (author_login, body)."""
    last_holder_idx = None
    for i, (login, _body) in enumerate(comments):
        if login in holders:
            last_holder_idx = i
    if last_holder_idx is None or not is_summary_request(comments[last_holder_idx][1]):
        deny(PROTOCOL_MSG)
    for _login, body in comments[last_holder_idx + 1:]:
        if SUMMARY_MARKER.search(body):
            deny(ALREADY_POSTED_MSG)


def check_github_summary(cmd):
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
    holders = {a.get("login") for a in issue.get("assignees") or [] if a.get("login")}
    if not holders:
        author = (issue.get("author") or {}).get("login")
        holders = {author} if author else set()
    comments = sorted(issue.get("comments") or [], key=lambda c: c.get("createdAt", ""))
    check_trigger(
        holders,
        [((c.get("author") or {}).get("login"), c.get("body", "")) for c in comments],
    )


def check_gitlab_summary(cmd):
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
    holders = {
        a.get("username") for a in issue.get("assignees") or [] if a.get("username")
    }
    if not holders:
        author = (issue.get("author") or {}).get("username")
        holders = {author} if author else set()
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
        check_github_summary(cmd)
        check_gitlab_summary(cmd)


main()
