#!/usr/bin/env python3
# F9 · A pass acts from the scanner's table.
# Fixture: #5 in-user-review with an unheard top-level CR comment (A4's
# shape), #6 track: fast + ready-for-dev, #7 a raw inbox idea with no
# questions batch yet.
# source: ledger F9 — "The scanner's table has a row per issue with the
#   right verdict; the pass acts on the top actionable row, locks no other
#   loop issue unless that turn only answered (a review-answers turn with no
#   seat dispatch and no commit is outside the N), posts every intake batch;
#   the scanner writes nothing; the main agent lists nothing after the
#   table." (the scan used to live in the main agent's context — #59)
# source: commands/patrol.md §3 — a review-answers turn that only answers
#   is outside the N; one that dispatches or commits counts toward it
# source: commands/patrol.md §1 — one read-only scanner sub-agent, prompt =
#   references/patrol-scan.md
# source: commands/patrol.md §2 — never re-read the forge to confirm a row
# source: references/patrol-scan.md — the table's verdict vocabulary
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
events = list(r.transcript_events())


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ---- the scanner dispatch and its result ------------------------------------
scanner_id, scanner_at = None, None
for i, ev in enumerate(events):
    for b in blocks(ev):
        if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                and "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False):
            scanner_id, scanner_at = b.get("id"), i
            break
    if scanner_id:
        break
c.expect("patrol.md §1", "exactly one scanner dispatch, prompt names patrol-scan.md",
         scanner_id is not None and sum(
             1 for b in r.tool_uses(("Task", "Agent"))
             if "patrol-scan.md" in json.dumps(b.get("input", {}), ensure_ascii=False)) == 1)

# The table is the scanner's final text. A foreground dispatch returns it as
# the Task's tool_result; a background dispatch returns a launch notice there
# and the table arrives later as a `system`/`task_notification` event whose
# `summary` is the report (the v1.26.0 sweep's run-5). Both are the same
# hand-back; the checker reads whichever carried a table.
table, table_at = "", None
for i, ev in enumerate(events):
    for b in blocks(ev):
        if b.get("type") == "tool_result" and b.get("tool_use_id") == scanner_id:
            cont = b.get("content")
            text = cont if isinstance(cont, str) else "".join(
                x.get("text", "") for x in (cont or []) if isinstance(x, dict))
            if "|" in text:
                table, table_at = text, i
    if ev.get("type") == "system" and ev.get("subtype") == "task_notification" \
            and ev.get("tool_use_id") == scanner_id and "|" in (ev.get("summary") or ""):
        table, table_at = ev["summary"], i
c.expect("patrol-scan.md (the table)", "the scanner returned a table", "|" in table)


def row(n):
    for line in table.splitlines():
        if re.match(r"^\|\s*#?%s\b" % n, line.strip()):
            return line
    return ""


c.expect("patrol-scan.md (verdict)", "#5's row: actionable: review-answers",
         "review-answers" in row(5))
c.expect("patrol-scan.md (verdict)", "#6's row: actionable: next-stage (ready-for-dev)",
         "next-stage" in row(6))
c.expect("patrol-scan.md (verdict)", "#7's row: intake: questions",
         "intake" in row(7) and "question" in row(7))
c.expect("patrol-scan.md (holder column)", "#7's row names its gate holder (paul)",
         "paul" in row(7))

# ---- the scanner wrote nothing ----------------------------------------------
# A write-shaped gh call. `gh api graphql -f query=…` is THREADS-LIST — a
# read with a -f field — so a graphql call counts only when it carries a
# mutation; a non-graphql `gh api` with -f/-F fields is an implicit POST.
# (The first sweep scored the scanner's THREADS-LIST as a write.)
WRITE = re.compile(r"gh (issue (edit|comment|close|create)"
                   r"|pr (create|comment|review|edit|merge|ready)"
                   r"|api -X (POST|PATCH|PUT|DELETE)"
                   r"|api graphql[^|;&]*\bmutation\b"
                   r"|api (?!graphql)\S+[^|;&]* -[fF] )")
scanner_writes = [b for ev in events if ev.get("parent_tool_use_id") == scanner_id
                  for b in blocks(ev) if b.get("type") == "tool_use" and b.get("name") == "Bash"
                  and WRITE.search((b.get("input") or {}).get("command", ""))]
c.expect("patrol-scan.md (You write nothing)", "no forge write under the scanner",
         scanner_id is not None and not scanner_writes)

# ---- the main agent never re-listed after the table -------------------------
# A scan-shaped listing: the whole issue list, or the CR list WITHOUT --head
# (a `pr list --head spec/<n>` is one issue's CR-FIND — what the action on
# that issue is allowed to read; the first sweep flagged review-answers'
# own CR lookup).
LIST = re.compile(r"gh (issue list|pr list(?![^|;&]*--head)"
                  r"|api repos/[^ ]+/(issues|pulls)(\?|\s|$))")
relist = [b for ev in events[table_at + 1:]
          if table_at is not None and not ev.get("parent_tool_use_id")
          for b in blocks(ev) if b.get("type") == "tool_use" and b.get("name") == "Bash"
          and LIST.search((b.get("input") or {}).get("command", ""))]
c.expect("patrol.md §2 (never re-read to confirm a row)",
         "no issue/CR listing by the main agent after the table",
         table_at is not None and not relist)

# ---- the actions: top row acted on, one-issue rule held, intake posted -------
c.expect("patrol.md §3 (closest to done)", "the pass acted on #5 (lock or marker reply)",
         r.route_taken("5"))
# One loop issue per pass: #6 is untouched — its labels as seeded, no comment,
# no lock, no branch, no CR. (The first sweep's run-2 ran next-stage on #6
# after review-answers on #5, STOPped it to `blocked`, and the narrower
# "not locked" check let it through.) Unless the #5 turn only answered: a
# review-answers turn with no seat dispatch and no commit is outside the N
# (patrol.md §3), so the one slot is free for #6 (#330 ruling 3). A seat
# dispatch on #5 is a Task/Agent call by the main agent, not the scanner,
# whose input names #5's work; a commit on #5 is spec/5 on the remote beyond
# the seed's one commit over main, or a `git commit` the main agent ran
# before its first call on #6 — pushed or not, even in a call that later
# errored; a `--dry-run` is not one (codex review, PR #340).
_six = r.state()["issues"]["6"]
NAMES_5 = re.compile(r"#5\b|\bissue 5\b|\b(?:spec|feat|qa)/5\b|pull/101\b"
                     r"|\b(?:PR|CR) #?101\b", re.I)
NAMES_6 = re.compile(r"#6\b|\bissue (?:edit|comment|view) 6\b|\bfast/6\b", re.I)
GIT_COMMIT = re.compile(r"\bgit\b[^|;&\n]*\bcommit\b(?![^|;&\n]*--dry-run)")
_root = [b for ev in events if not ev.get("parent_tool_use_id") for b in blocks(ev)
         if b.get("type") == "tool_use"]


def _text(b):
    """The call's input as decoded text: a JSON dump writes a newline as `\\n`,
    and `\\b` sees no boundary after its `n` (codex review, PR #340)."""
    return " ".join(str(v) for v in (b.get("input") or {}).values())


_seat5 = any(b.get("name") in ("Task", "Agent") and b.get("id") != scanner_id
             and NAMES_5.search(_text(b)) for b in _root)
_six_at = next((i for i, b in enumerate(_root)
                if b.get("id") != scanner_id and NAMES_6.search(_text(b))), len(_root))
# The commands before #6's first call, plus the part of that call before it
# names #6 (`git commit … && gh issue edit 6 …` — codex review, PR #340).
_before6 = [(b.get("input") or {}).get("command", "") for b in _root[:_six_at]
            if b.get("name") == "Bash"]
if _six_at < len(_root) and _root[_six_at].get("name") == "Bash":
    _cmd = (_root[_six_at].get("input") or {}).get("command", "")
    _before6.append(_cmd[:NAMES_6.search(_cmd).start()] if NAMES_6.search(_cmd) else "")
_rc, _ahead = r.git("rev-list", "--count", "main..spec/5")
_commit5 = (_rc == 0 and _ahead.strip().isdigit() and int(_ahead) > 1) or any(
    GIT_COMMIT.search(cmd) for cmd in _before6)
_six_untouched = (sorted(_six.get("labels", [])) == ["status: ready-for-dev", "track: fast"]
                  and not _six.get("comments")
                  and r.journal_writes(r"^pr-create$") == 0
                  and r.git("rev-parse", "--verify", "-q", "refs/heads/fast/6")[0] != 0)
c.expect("patrol.md §3 (one loop issue per pass; an answer-only (7) turn is outside the N)",
         "#6 was not touched at all — unless the #5 turn only answered "
         "(no seat dispatch, no commit)",
         _six_untouched or not (_seat5 or _commit5))
c.expect("patrol.md §3 (the whole inbox)", "#7 got its **[intake]** questions batch",
         any(b.startswith("**[intake]**") for b in r.issue_comment_bodies("7")))
# #135: the agent takes the resolver's snapshot before the scanner runs and
# hands the file over; raw `ls-remote` output in the prompt is the old,
# hand-matching handoff and fails.
_uses = list(r.tool_uses())
_snap_at = next((i for i, u in enumerate(_uses) if u.get("name") == "Bash"
                 and "roz-branch snapshot" in (u.get("input") or {}).get("command", "")), None)
_scan_at = next((i for i, u in enumerate(_uses) if u.get("name") in ("Task", "Agent")
                 and "patrol-scan" in (u.get("input") or {}).get("prompt", "")), None)
_prompt = (_uses[_scan_at].get("input") or {}).get("prompt", "") if _scan_at is not None else ""
c.expect("patrol.md §1 (#135: `bin/roz-branch snapshot` before the scanner)",
         "the snapshot was taken, and before the scanner's dispatch",
         _snap_at is not None and _scan_at is not None and _snap_at < _scan_at)
c.expect("patrol.md §1 / patrol-scan.md (#135: the scanner is handed the snapshot, not raw heads)",
         "the scanner's prompt names the snapshot and carries no `<sha>\\trefs/heads/` lines",
         ("snapshot" in _prompt) and re.search(r"[0-9a-f]{40}\s+refs/heads/", _prompt) is None)
# #135 shadow: the names the pass looked up or cut (#5's spec CR-FIND, #6's
# fast cut if any) against Lookup over the final heads.
r.shadow_branch([("spec", "5"), ("fast", "6")])
# #133 shadow: bin/roz-state on the final forge state against the stub's own
# truth, and the scanner table's fact columns (track, status, cr) against a
# snapshot of the SEEDED state the scanner read — signals, never a fail
# (evals/CONTRIBUTING.md § 7).
r.shadow_state(["5", "6", "7"])
r.shadow_scan(["5", "6", "7"], os.path.dirname(os.path.abspath(__file__)))
c.finish()
