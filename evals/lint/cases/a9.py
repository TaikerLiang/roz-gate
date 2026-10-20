"""A9 · patrol answers every human comment on an intake thread  (defect 2.4.0-, #174)
Until 2.4.0 async intake had three triggers and an Otherwise: after the
batch, a comment that was neither the holder's `summary` nor a gate label
went unanswered — the thread "belonged to the humans". Since #174 a human
comment after the latest agent `**[intake]` comment gets one
`**[intake] · reply**` on the next pass. Lint holds the route and its
precedence, the verdict, the reply deliverable's limits, the adapters' op,
and the human-comment test — stated in the scan's brief and implemented in
guard-gate rule I, from one definition (the gate-label audit's bot shape).
hooks/tests prove rule I; replay A9 measures a pass.
"""

from lib.lintkit import c, read

META = {
    "id": "A9",
}


def flat(relpath):
    """The file with every whitespace run collapsed — prose anchors survive
    a re-wrap, never a reword."""
    return " ".join(read(relpath).split())


def has(name, relpath, literal):
    c.expect("pattern", name, " ".join(literal.split()) in flat(relpath))


_pat = flat("commands/patrol.md")
_route = "**A human comment follows the latest agent `**[intake]` comment**"
has("A9: patrol's async intake has the reply route", "commands/patrol.md", _route)
has("A9: the reply is one prefixed comment, one per issue per pass", "commands/patrol.md",
    "prefixed `**[intake] · reply**` — one per issue per pass")
has("A9: a bot or an agent-marker comment never counts", "commands/patrol.md",
    "a bot or an agent-marker comment never counts")
has("A9: a reply decides nothing — only the holder's summary line and label act",
    "commands/patrol.md", "only the holder's `summary` line and gate label act")
has("A9: patrol names the backstop", "commands/patrol.md", "guard-gate rule I denies a reply")
_order = ["**No `**[intake]**` questions comment exists yet**", _route, "**Otherwise**"]
_at = [_pat.find(" ".join(x.split())) for x in _order]
c.expect("pattern", "A9: route order — no batch → reply → otherwise",
         -1 not in _at and _at == sorted(_at))
c.expect("pattern", "A9: Otherwise no longer hands the thread to the humans",
         "the thread belongs to the humans" not in _pat)

has("A9: the scan's verdict vocabulary carries `intake: reply`", "references/patrol-scan.md",
    "`intake: summary` · `intake: reply` ·")
has("A9: the inbox row routes a human comment to `intake: reply`", "references/patrol-scan.md",
    "follows the latest agent `**[intake]` comment and the row has a holder → `intake: reply`")
for _clause in ("its body opens with an agent marker, `**[` or `✅ [`",
                "its author is in the `bot_login` list",
                "GitHub `type` `Bot`, or a `[bot]` suffix",
                "GitLab a `project_<id>_bot_` / `group_<id>_bot_` prefix (system notes are not "
                "comments)",
                "guard-gate rule I applies this same test"):
    has("A9: the human-comment test states: %s" % _clause[:48], "references/patrol-scan.md",
        _clause)
has("A9: the scan reads comments with ISSUE-COMMENTS-LIST", "references/patrol-scan.md",
    "An inbox row's comments are read with ISSUE-COMMENTS-LIST")

# The same test, implemented: rule I's predicate carries each clause.
_gg = read("hooks/guard_gate.py")
for _lit in ('ROZ_MARKER = re.compile(r"\\*\\*\\[|✅ \\[")',
             "if ROZ_MARKER.match(ansi_c(body or \"\").lstrip()):",
             'FORGE_BOT = re.compile(r"\\[bot\\]$|^(?:project|group)_\\d+_bot_")',
             'if forge_type == "Bot" or FORGE_BOT.search(login or ""):',
             'return normalize_login(login or "") not in bots',
             'REPLY_OPEN = re.compile(r"^\\s*\\*\\*\\[intake\\] · reply\\*\\*")',
             '"repos/{owner}/{repo}/issues/%s/comments" % number'):
    c.expect("pattern", "A9: rule I implements: %s" % _lit[:56], _lit in _gg)

for _clause in ("3. **A reply** (async only)",
                "never an @-mention",
                "is **recorded as input**, never as settled",
                "confirms it with the gate label",
                "**New questions only for decisions these comments opened**",
                "**Never a batch question again**",
                "It never edits the issue body or a label"):
    has("A9: the brief's reply deliverable states: %s" % _clause[:48],
        "references/intake-brief.md", _clause)

for _f in ("references/forge-github.md", "references/forge-gitlab.md"):
    has("A9: %s has ISSUE-COMMENTS-LIST" % _f, _f, "| ISSUE-COMMENTS-LIST |")
has("A9: GitHub's op reads the REST type", "references/forge-github.md",
    "type: .user.type")
has("A9: GitLab's op drops system notes", "references/forge-gitlab.md",
    "select(.system == false)")
