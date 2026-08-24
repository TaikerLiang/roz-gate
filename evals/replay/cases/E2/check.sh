#!/usr/bin/env bash
# E2 · A seat's questions reach the holder from any document.
# Fixture: the implementer (scripted double) leaves its question in
# technical-spec.md §9 and does not return it in its report.
# source: ledger E2 — "Relocated verbatim into spec.md's Open Questions,
#   tagged with the raising role, before threads are posted." (threads are
#   the only objects the gates count; a question outside the threaded
#   surface blocks nothing)
# source: commands/next-stage.md:175-186 (A6) — sweep the other spec docs
#   for question-shaped content, relocate verbatim, then post one thread
#   per item
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "ledger E2 + next-stage.md:176-181" \
  "the §9 question was relocated into spec.md's Open Questions" \
  bash -c 'git -C "$BARE" show spec/5:docs/specs/5/spec.md | grep -q "clock source"'

expect "next-stage.md:175-180 (sweep before posting)" \
  "technical-spec.md no longer carries an open-questions section" \
  bash -c '! git -C "$BARE" show spec/5:docs/specs/5/technical-spec.md | grep -qiE "^#+ .*open questions"'

expect "ledger E2 (a question outside the threads blocks nothing)" \
  "a thread was posted for the relocated question" \
  bash -c 'grep "thread-post-inline" "$RUN_DIR/forge/journal.jsonl" | grep -q "clock source"'

finish
