#!/usr/bin/env bash
# Test harness for hooks/guard-gate.sh — pipes synthetic PreToolUse JSON in,
# checks exit code and (optionally) a stderr substring. Forge CLIs stubbed
# via PATH.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
GUARD="$S/../guard-gate.sh"
export PATH="$S/bin:$PATH"
export STUB_LOG="$(mktemp)"
# Identity config is discovered from the git toplevel of the guard's cwd:
# USERREPO (no git, no CLAUDE.md) pins user mode; BOTREPO carries a bot config.
USERREPO=$(mktemp -d)
BOTREPO=$(mktemp -d)
git init -q "$BOTREPO" && mkdir -p "$BOTREPO/sub"
cat > "$BOTREPO/CLAUDE.md" <<'EOF'
## Development Workflow (Roz Gate)

### Roz Gate config

- forge: github
- agent_identity: bot
- bot_login: roz-bot
EOF
trap 'rm -f "$STUB_LOG"; rm -rf "$USERREPO" "$BOTREPO"' EXIT
pass=0 fail=0

run() { # name expected_exit stderr_substr command
  local name="$1" want="$2" substr="$3" cmd="$4"
  : > "$STUB_LOG"
  local payload err rc
  payload=$(python3 - "$cmd" <<'PY'
import json, sys
print(json.dumps({"tool_name": "Bash", "tool_input": {"command": sys.argv[1]}}))
PY
)
  err=$( (cd "${RUN_CWD:-$USERREPO}" && printf '%s' "$payload" | "$GUARD" 2>&1 >/dev/null) ); rc=$?
  if [ "$rc" != "$want" ]; then
    echo "FAIL $name: exit $rc, want $want"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  if [ -n "$substr" ] && ! grep -qF "$substr" <<<"$err"; then
    echo "FAIL $name: stderr missing '$substr'"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  echo "PASS $name"; pass=$((pass+1))
}

SUMMARY_CMD='gh issue comment 54 --body "**[intake] · summary**

**Story** — As a user, I want ..."'

# --- fast path / unrelated commands ---
export GH_FIXTURE="$S/fx/gh_no_trigger.json" GLAB_ISSUE_FIXTURE="$S/fx/glab_issue_ok.json" GLAB_NOTES_FIXTURE="$S/fx/glab_notes_ok.json"
run "unrelated command passes prefilter" 0 "" 'ls -la && git status'
run "plain issue comment passes" 0 "" 'gh issue comment 54 --body "thanks, will do"'
run "questions batch allowed (no API call)" 0 "" 'gh issue comment 54 --body "**[intake]**

3 questions — when it settles the assignee comments \`summary\`.

**Q1 · Scope** ..."'
grep -q . "$STUB_LOG" && { echo "FAIL questions batch hit the API"; fail=$((fail+1)); } || { echo "PASS questions batch made no API call"; pass=$((pass+1)); }

# --- rule B: gate labels are human-only ---
run "gate label add blocked (gh)" 2 "gate labels" 'gh issue edit 5 --add-label "status: ready-for-spec"'
run "gate label add blocked (gh, =form)" 2 "gate labels" 'gh issue edit 5 --add-label="status: ready-for-dev"'
run "gate label remove allowed" 0 "" 'gh issue edit 5 --remove-label "status: ready-for-spec" --add-label "track: spec"'
run "gate label add blocked (glab)" 2 "gate labels" 'glab issue update 5 --label "status::ready-for-dev"'
run "glab list filter allowed" 0 "" 'glab issue list --label "status::ready-for-spec" --output json'
run "gh list filter allowed" 0 "" 'gh issue list --label "status: ready-for-spec" --json number'
run "label create allowed (init)" 0 "" 'gh label create "status: ready-for-spec" --color 0e8a16 --description "gate"'

# --- rule C: a marker-carrying comment never opens with a quote block ---
# Static rule, no API. The B4 runaway: patrol reads a quote-opening agent
# comment as a human answer and the loop replies to itself.
run "quote-opening readback denied" 2 "marker on line one" 'gh pr comment 12 --body "> 你說的是要在讀取時就擋掉過期的 offer

**[review] · answer**

對,規則 R4 就是這個意思。"'
run "whitespace-led quote still denied" 2 "open with its marker" 'gh issue comment 54 --body "

   > the quoted claim
**[reviewer] · question** is this measured?"'
run "marker first, quote below — the remedy — allowed" 0 "" 'gh pr comment 12 --body "**[review] · answer**

> 你說的是要在讀取時就擋掉過期的 offer

對,規則 R4 就是這個意思。"'
run "quote-opening body with no marker allowed (scoping)" 0 "" 'gh pr comment 12 --body "> just quoting a teammate

agreed, merging."'
run "thread-reply via gh api denied (✅ marker)" 2 "open with its marker" 'gh api -X POST "repos/o/r/pulls/12/comments/9/replies" -f body="> the finding as stated

✅ [reviewer] resolved — fixed in abc123."'
run "glab message form denied" 2 "open with its marker" 'glab issue note 7 --message "> 原本的問題

**[qa] · addressed** covered by the new fixture."'
run "non-forge command with marker+quote allowed (gh/glab only)" 0 "" 'git commit -m "> odd subject **[not a protocol write]**"'
grep -q . "$STUB_LOG" && { echo "FAIL rule C hit the API"; fail=$((fail+1)); } || { echo "PASS rule C made no API call"; pass=$((pass+1)); }
run "CR body may open with a quote (comments only)" 0 "" 'gh pr create --title t --body "> quoting the spec intro
see **[R4]** below"'
run "body-file heredoc parsed and denied" 2 "open with its marker" 'gh pr comment 12 --body-file - <<EOF
> the quoted claim

**[review] · answer**
EOF'
BODYQ=$(mktemp); printf '> quoted claim\n\n**[review] · answer**\n' > "$BODYQ"
BODYOK=$(mktemp); printf '**[review] · answer**\n\n> quoted claim\n' > "$BODYOK"
run "body-file read back and denied" 2 "open with its marker" "gh pr comment 12 --body-file $BODYQ"
run "body-file with marker-first body allowed" 0 "" "gh pr comment 12 --body-file $BODYOK"
rm -f "$BODYQ" "$BODYOK"
run "unjudgeable marker-carrying body-file fails closed" 2 "cannot judge" 'printf "**[qa] · x**" | gh pr comment 12 --body-file -'
run "ANSI-C quoted body denied" 2 "open with its marker" "gh pr comment 12 --body \$'> quoted\\n\\n**[review] · answer**'"
run "glued --field=body= form denied" 2 "open with its marker" 'gh api -X POST "repos/o/r/pulls/12/comments/9/replies" --field=body="> the finding

✅ [reviewer] resolved — fixed."'
# Segment splitting (1.14.1): a compound line's api -F must never be read
# as the comment segment's --body-file (the dogfooded false positive).
run "compound api -F + marker comment allowed" 0 "" 'gh api graphql -f query="q" -F owner=acme -F repo=demo -F pr=101 && gh issue comment 5 --body "**[intake] · note** all three channels are clean."'
run "semicolon-joined quote-opening comment still denied" 2 "open with its marker" 'gh pr view 12; gh pr comment 12 --body "> quoted claim

**[qa] · addressed** done."'
run "pipe segment does not leak flags across the boundary" 0 "" 'gh api "repos/o/r/pulls/12/comments" -F per_page=50 | head -5 && gh issue comment 5 --body "**[review] · answer** see thread."'
# Glued (unspaced) operators — codex review on PR #2: token-equality alone
# missed `x=y&&gh`, reproducing the very false positive the PR fixes.
run "glued && operator: api -F + marker comment allowed" 0 "" 'gh api graphql -f query="q" -F owner=acme&&gh issue comment 5 --body "**[intake] · note** all clean."'
run "glued pipe does not leak flags across the boundary" 0 "" 'gh pr list --limit 50|head -3 && gh issue comment 5 --body "**[review] · answer** done."'
run "glued semicolon quote-opening comment still denied" 2 "open with its marker" 'gh pr view 12;gh pr comment 12 --body "> quoted claim

**[qa] · addressed** done."'

# --- rule D: a commit never carries an open-questions section in a
# technical-spec.md under specs_dir (1.15.0; E2 measured 0/5 on prose).
NOCFGREPO=$(mktemp -d)
git init -q "$NOCFGREPO" && (cd "$NOCFGREPO" \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init \
  && git checkout -qb spec/1)
QREPO=$(mktemp -d)
git init -q -b main "$QREPO" && mkdir -p "$QREPO/docs/specs/5" "$QREPO/sub"
cat > "$QREPO/CLAUDE.md" <<'EOF'
### Roz Gate config

- forge: github
- specs_dir: docs/specs
EOF
# The E2 fixture's exact technical-spec.md (the scripted double's output).
TS_WITH_SECTION='# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.

## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB'"'"'s or the API caller'"'"'s?
'
TS_MOVED='# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
  (open question on the clock source: spec.md Q9)
'
qrepo_set() { # technical-spec content, then stage everything
  printf '%s' "$1" > "$QREPO/docs/specs/5/technical-spec.md"
  printf '# Spec #5\n\n## Open Questions\n- **[implementer] · Q9 · Clock source**\n' > "$QREPO/docs/specs/5/spec.md"
  (cd "$QREPO" && git add -A)
}
qrepo_set "$TS_WITH_SECTION"
RUN_CWD=$QREPO run "rule D: §9 section left in technical-spec.md denied" 2 "open-questions section" 'git commit -m "spec: #5 refinement"'
RUN_CWD=$QREPO run "rule D: message carries the remedy (move + delete, A6)" 2 "delete it here" 'git commit -m "spec: #5 refinement"'
RUN_CWD=$QREPO/sub run "rule D: judged from a subdirectory" 2 "open-questions section" 'git commit -am x'
RUN_CWD=$QREPO run "rule D: compound line (cd && git commit) denied" 2 "open-questions section" 'git add -A && git -c user.name=t commit -m x'
RUN_CWD=$QREPO run "rule D: a comment body mentioning git commit is not a commit" 0 "" 'gh pr comment 12 --body "**[review] · answer** run git commit after the fix"'
qrepo_set "$TS_MOVED"
RUN_CWD=$QREPO run "rule D: moved — pointer line under another heading — allowed" 0 "" 'git commit -m "spec: #5 refinement"'
qrepo_set '# Technical spec #5

## §9 Open questions
- moved → spec.md Q9
'
RUN_CWD=$QREPO run "rule D: heading kept as pointer-only section still denied" 2 "open-questions section" 'git commit -m x'
qrepo_set "$TS_WITH_SECTION"; printf '%s' "$TS_MOVED" > "$QREPO/docs/specs/5/technical-spec.md"
RUN_CWD=$QREPO run "rule D: fixed in the working tree but stale in the index denied" 2 "git add" 'git commit -m x'
(cd "$QREPO" && git add -A)
RUN_CWD=$QREPO run "rule D: spec.md's own Open Questions is the destination, not a hit" 0 "" 'git commit -m x'
printf '%s' "$TS_WITH_SECTION" > "$QREPO/docs/specs/5/technical-spec.md"
RUN_CWD=$QREPO run "rule D: unstaged working-tree section denied (commit -a would take it)" 2 "working tree" 'git commit -am x'
(cd "$QREPO" && git checkout -q -- docs/specs/5/technical-spec.md)
mkdir -p "$QREPO/notes/9" && printf '%s' "$TS_WITH_SECTION" > "$QREPO/notes/9/technical-spec.md"
RUN_CWD=$QREPO run "rule D: a technical-spec.md outside specs_dir is not in scope" 0 "" 'git add -A && git commit -m x'
mkdir -p "$NOCFGREPO/docs/specs/1" && printf '%s' "$TS_WITH_SECTION" > "$NOCFGREPO/docs/specs/1/technical-spec.md"
(cd "$NOCFGREPO" && git add -A)
RUN_CWD=$NOCFGREPO run "rule D: repo without a Roz Gate config block untouched" 0 "" 'git commit -m x'
trap 'rm -f "$STUB_LOG"; rm -rf "$USERREPO" "$BOTREPO" "$QREPO" "$NOCFGREPO"' EXIT

# --- rule E (guard-blind, 1.16.0): the fidelity dispatch is blind while
# the dispatching command's marker exists (D2 measured 4/5 on prose).
GUARD_BLIND="$S/../guard-blind.sh"
BREPO=$(mktemp -d)
git init -q -b main "$BREPO" && mkdir -p "$BREPO/src" "$BREPO/tests/acceptance" "$BREPO/sub"
echo demo > "$BREPO/src/app.txt"; echo "# S1" > "$BREPO/tests/acceptance/test_expiry.py"
(cd "$BREPO" && git add -A && git -c user.email=t@t -c user.name=t commit -qm seed \
  && git branch -q feat/5 && git checkout -qb qa/5)
BMARK="$BREPO/.git/roz-gate/fidelity-dispatch"
marker_on() { mkdir -p "$(dirname "$BMARK")" && printf 'issue=5\n' > "$BMARK"; }
marker_off() { rm -f "$BMARK"; }
run_blind() { # name expected_exit stderr_substr tool json_tool_input [cwd]
  local name="$1" want="$2" substr="$3" tool="$4" inp="$5" cwd="${6:-$BREPO}"
  local payload err rc
  payload=$(python3 - "$tool" "$inp" <<'PY'
import json, sys
print(json.dumps({"tool_name": sys.argv[1], "tool_input": json.loads(sys.argv[2]), "agent_type": "roz-gate:qa"}))
PY
)
  err=$( (cd "$cwd" && printf '%s' "$payload" | "$GUARD_BLIND" 2>&1 >/dev/null) ); rc=$?
  if [ "$rc" != "$want" ]; then
    echo "FAIL $name: exit $rc, want $want"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  if [ -n "$substr" ] && ! grep -qF "$substr" <<<"$err"; then
    echo "FAIL $name: stderr missing '$substr'"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  echo "PASS $name"; pass=$((pass+1))
}
RUN4='{"command": "git status --short && git rev-parse --abbrev-ref HEAD && cat src/app.txt"}'
run_blind "rule E: D2 run-4's exact command without a marker allowed" 0 "" Bash "$RUN4"
marker_on
run_blind "rule E: D2 run-4's exact command under the marker denied" 2 "implementation-blind" Bash "$RUN4"
run_blind "rule E: message states the remedy (report it as a finding)" 2 "report it as a finding" Bash "$RUN4"
run_blind "rule E: message names the agent when the payload carries one" 2 "agent: roz-gate:qa" Bash "$RUN4"
run_blind "rule E: git checkout feat/5 under the marker denied" 2 "feat/ ref" Bash '{"command": "git checkout feat/5"}'
run_blind "rule E: git diff qa/5...feat/5 denied" 2 "feat/ ref" Bash '{"command": "git diff qa/5...feat/5 -- tests/"}'
run_blind "rule E: Read of an absolute src/ path denied" 2 "Read under src/" Read "{\"file_path\": \"$BREPO/src/app.txt\"}"
run_blind "rule E: Grep with path src/ denied" 2 "Grep under src/" Grep '{"pattern": "price", "path": "src/"}'
run_blind "rule E: Glob under src/ denied" 2 "Glob under src/" Glob '{"pattern": "src/**/*.py"}'
run_blind "rule E: exclusion form grep -v '^src/' allowed" 0 "" Bash '{"command": "git ls-files | grep -v '"'"'^src/'"'"'"}'
# Mention is not use, third form (D2 re-run under 1.16.0: the only denial).
run_blind "rule E: the re-run's exact echo-mention command allowed" 0 "" Bash '{"command": "git ls-files && echo \"--- grep fixtures (tracked files, excluding src/)\" && git grep -n -E '"'"'expires'"'"' -- '"'"':!src/**'"'"' ; echo \"--- diff of fix\" && git show e61367c -- tests/acceptance/"}'
run_blind "rule E: a comment mentioning src/ allowed" 0 "" Bash '{"command": "# never read src/ here\ngit status"}'
run_blind "rule E: a read after an echo mention still denied" 2 "read of src/" Bash '{"command": "echo \"excluding src/\" && cat src/app.txt"}'
# echo/printf are commands, never arguments (codex, PR #11: `grep echo src/app.txt` passed).
run_blind "rule E: grep echo src/app.txt denied (echo as an argument)" 2 "read of src/" Bash '{"command": "grep echo src/app.txt"}'
run_blind "rule E: grep -n echo src/a.py denied" 2 "read of src/" Bash '{"command": "grep -n echo src/a.py"}'
run_blind "rule E: printf_helper src/x denied (word inside a token)" 2 "read of src/" Bash '{"command": "printf_helper src/x"}'
run_blind "rule E: echo mention then ls allowed" 0 "" Bash '{"command": "echo \"excluding src/\" && ls tests"}'
run_blind "rule E: FOO=1 echo src/ && ls allowed (env-assignment prefix)" 0 "" Bash '{"command": "FOO=1 echo src/ && ls"}'
run_blind "rule E: ls && echo src/ | cat allowed (echo after &&)" 0 "" Bash '{"command": "ls && echo src/ | cat"}'
run_blind "rule E: cat src/app.txt | grep printf still denied" 2 "read of src/" Bash '{"command": "cat src/app.txt | grep printf"}'
run_blind "rule E: exclusion pathspec ':!src/**' allowed" 0 "" Bash '{"command": "git grep -n price -- '"'"':!src/**'"'"'"}'
run_blind "rule E: qa/<n> work — tests and spec docs — allowed" 0 "" Bash '{"command": "cat tests/acceptance/test_expiry.py && git status"}'
run_blind "rule E: Read of a spec doc allowed" 0 "" Read "{\"file_path\": \"$BREPO/docs/specs/5/spec.md\"}"
run_blind "rule E: judged from a subdirectory (marker found via git dir)" 2 "implementation-blind" Bash "$RUN4" "$BREPO/sub"
run_blind "rule E: stale marker still denies and names the marker file" 2 "roz-gate/fidelity-dispatch" Bash "$RUN4"
marker_off
run_blind "rule E: marker removed — the same read is allowed again" 0 "" Bash "$RUN4"
run_blind "rule E: outside any git repo the prefilter exits 0" 0 "" Bash "$RUN4" "$(mktemp -d)"
trap 'rm -f "$STUB_LOG"; rm -rf "$USERREPO" "$BOTREPO" "$QREPO" "$NOCFGREPO" "$BREPO"' EXIT

# --- rule A: intake summary triggers (GitHub) ---
export GH_FIXTURE="$S/fx/gh_no_trigger.json"
run "summary without trigger blocked (#54 case)" 2 "human decision point" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_summary.json"
run "summary after gate holder's 'summary' allowed" 0 "" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_gate_label.json"
run "summary with gate label allowed (finalize)" 0 "" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_already.json"
run "duplicate summary blocked" 2 "already" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_wrong_person.json"
run "'summary' from non-gate-holder blocked" 2 "gate holder" "$SUMMARY_CMD"
run "unparseable issue ref blocked" 2 "adapter form" 'gh issue comment https://github.com/x/y/issues/54 --body "**[intake] · summary** ..."'

# --- rule A: summary-request line rule (corrections + summary in one comment) ---
export GH_FIXTURE="$S/fx/gh_corrections_lastline.json"
run "corrections + last-line summary allowed" 0 "" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_firstline.json"
run "first-line summary allowed" 0 "" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_midline.json"
run "mid-text summary mention blocked" 2 "human decision point" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_gate_label_bystander.json"
run "finalize regen after bystander chatter allowed" 0 "" "$SUMMARY_CMD"

# --- rule A: fail-closed on API failure, distinct message ---
export GH_FIXTURE="$S/fx/gh_no_trigger.json" STUB_FAIL=1
run "API failure fails closed with retry wording" 2 "NOT a protocol block" "$SUMMARY_CMD"
unset STUB_FAIL

# --- bot mode (1.7.0): identity from the project config ---
export GH_FIXTURE="$S/fx/gh_bot_already.json"
RUN_CWD=$BOTREPO run "bot mode: bot-posted summary counts as already-posted" 2 "already" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_bot_human_quote.json"
RUN_CWD=$BOTREPO run "bot mode: human quoting the marker doesn't count" 0 "" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_bot_orphan.json"
RUN_CWD=$BOTREPO run "bot mode: bot-authored unassigned issue denied" 2 "no human gate holder" "$SUMMARY_CMD"
export GH_FIXTURE="$S/fx/gh_bot_human_quote.json"
RUN_CWD=$BOTREPO/sub run "bot mode: config found from a subdirectory" 0 "" "$SUMMARY_CMD"

# --- rule A: GitLab ---
run "glab summary after 'summary' allowed" 0 "" 'glab issue note 7 --message "**[intake] · summary**

**Story** ..."'

# --- guard-acceptance: the acceptance suite is not editable on a spec branch ---
GUARD_ACC="$S/../guard-acceptance.sh"
SPECREPO=$(mktemp -d)
git init -q "$SPECREPO"
cat > "$SPECREPO/CLAUDE.md" <<'EOF'
### Roz Gate config

- forge: github
- acceptance_dir: tests/acceptance
EOF
(cd "$SPECREPO" && git add -A && git -c user.email=t@t -c user.name=t commit -qm init \
  && git checkout -qb spec/63)
# A repo with no Roz Gate config block (created above, before rule D): the
# guard has nothing to enforce.
trap 'rm -f "$STUB_LOG"; rm -rf "$USERREPO" "$BOTREPO" "$QREPO" "$SPECREPO" "$NOCFGREPO" "$BREPO"' EXIT

run_edit() { # name expected_exit stderr_substr repo tool file_path
  local name="$1" want="$2" substr="$3" repo="$4" tool="$5" path="$6"
  local payload err rc
  payload=$(python3 - "$tool" "$repo/$path" <<'PY'
import json, sys
print(json.dumps({"tool_name": sys.argv[1], "tool_input": {"file_path": sys.argv[2]}}))
PY
)
  err=$( (cd "$repo" && printf '%s' "$payload" | "$GUARD_ACC" 2>&1 >/dev/null) ); rc=$?
  if [ "$rc" != "$want" ]; then
    echo "FAIL $name: exit $rc, want $want"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  if [ -n "$substr" ] && ! grep -qF "$substr" <<<"$err"; then
    echo "FAIL $name: stderr missing '$substr'"; echo "  stderr: $err"; fail=$((fail+1)); return
  fi
  echo "PASS $name"; pass=$((pass+1))
}

run_edit "acceptance edit on spec branch blocked" 2 "acceptance suite" \
  "$SPECREPO" Edit "tests/acceptance/offers/test_expiry.py"
run_edit "Write is guarded too" 2 "acceptance suite" \
  "$SPECREPO" Write "tests/acceptance/offers/test_new.py"
run_edit "MultiEdit is guarded too" 2 "acceptance suite" \
  "$SPECREPO" MultiEdit "tests/acceptance/offers/test_expiry.py"
run_edit "implementation code on spec branch allowed" 0 "" \
  "$SPECREPO" Edit "src/offers/repo.py"
run_edit "spec docs on spec branch allowed" 0 "" \
  "$SPECREPO" Edit "docs/specs/63/spec.md"
run_edit "unit tests on spec branch allowed" 0 "" \
  "$SPECREPO" Edit "tests/unit/test_repo.py"
run_edit "sibling dir is not the acceptance dir" 0 "" \
  "$SPECREPO" Edit "tests/acceptance-old/test_x.py"
run_edit "the acceptance dir itself is not a file under it" 0 "" \
  "$SPECREPO" Edit "tests/acceptance"
run_edit "no Roz Gate config: nothing to enforce" 0 "" \
  "$NOCFGREPO" Edit "tests/acceptance/test_x.py"
# A misconfigured acceptance_dir pointing at the repo root would match every
# path — it must enforce nothing rather than deny every edit on spec branches.
ROOTCFGREPO=$(mktemp -d)
git init -q "$ROOTCFGREPO"
printf '### Roz Gate config\n\n- forge: github\n- acceptance_dir: .\n' > "$ROOTCFGREPO/CLAUDE.md"
(cd "$ROOTCFGREPO" && git add -A && git -c user.email=t@t -c user.name=t commit -qm init \
  && git checkout -qb spec/1)
run_edit "acceptance_dir at the repo root enforces nothing" 0 "" \
  "$ROOTCFGREPO" Edit "src/anything.py"
rm -rf "$ROOTCFGREPO"
(cd "$SPECREPO" && git checkout -q -b qa/63)
run_edit "same file on qa/<n> allowed — that is the road" 0 "" \
  "$SPECREPO" Edit "tests/acceptance/offers/test_expiry.py"
(cd "$SPECREPO" && git checkout -q -b feat/63)
run_edit "feat branch unaffected" 0 "" \
  "$SPECREPO" Edit "tests/acceptance/offers/test_expiry.py"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
