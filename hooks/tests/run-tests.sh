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
# A repo with no Roz Gate config block: the guard has nothing to enforce.
NOCFGREPO=$(mktemp -d)
git init -q "$NOCFGREPO" && (cd "$NOCFGREPO" \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init \
  && git checkout -qb spec/1)
trap 'rm -f "$STUB_LOG"; rm -rf "$USERREPO" "$BOTREPO" "$SPECREPO" "$NOCFGREPO"' EXIT

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
