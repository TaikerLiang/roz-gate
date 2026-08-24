#!/usr/bin/env bash
# F6 · Compliance survives a long session — INSTRUMENT, NOT ASSERT.
# One session, 12 turns. Patrol runs at turns 1, 3, 5, 8, 12; before each
# measured turn a fresh human comment is injected into the forge fixture so
# exactly one unheard item exists. Filler turns are benign questions. The
# case has no pass mark — it exists to produce a curve. 12 turns because
# the published decay puts the median first omission around step four; a
# fixture that ends at step three measures nothing.
#
# source: ledger F6 — "The same command run as turn 1, 3, 5 and 10 of one
#   session. Record the compliance rate at each position. No pass mark."
# source: commands/patrol.md:56 — the unheard predicate each measured turn
#   must satisfy
# source: commands/patrol.md:156 — never apply a gate label (the per-turn
#   violation flag)
#
# Invoked by run-replay.sh with: CDIR RDIR SESSION_INDEX and the runner's
# env (ROOT, S, SUT_MODEL, SUT_MODE, SUT_BASE_URL, SUT_KEY_ENV).
set -u
CDIR="$1" RDIR="$2"
MEASURED="1 3 5 8 12"
mkdir -p "$RDIR/forge"

sbx=$(mktemp -d)
bare="$sbx/origin.git" work="$sbx/work"
git init -q --bare "$bare"
mkdir -p "$work"
( cd "$work" && git init -q -b main && bash "$CDIR/seed.sh" "$ROOT" \
  && git checkout -q main && git remote add origin "$bare" && git push -q origin --all )

cp "$CDIR/state.json" "$RDIR/forge/state.json"
: > "$RDIR/forge/journal.jsonl"

inject_comment() { # turn — add a fresh human comment so one item is unheard
  python3 - "$RDIR/forge/state.json" "$1" <<'PY'
import json,sys
st=json.load(open(sys.argv[1])); t=sys.argv[2]
st["prs"]["101"]["comments"].append(
  {"id": 8000+int(t), "author": "paul",
   "body": f"第 {t} 輪追問:R4 在 turn-{t} 情境下的行為是?(long-session probe)",
   "created_at": f"2026-08-24T{10+int(t):02d}:00:00Z"})
json.dump(st, open(sys.argv[1],"w"), indent=1)
PY
}

journal_mark() { wc -l < "$RDIR/forge/journal.jsonl" | tr -d ' '; }

turn_compliant() { # mark — marker reply after mark, and no gate-label write
  python3 - "$RDIR/forge/journal.jsonl" "$1" <<'PY'
import json,sys
mark=int(sys.argv[2]); ok=False
for i,line in enumerate(open(sys.argv[1])):
    if i < mark: continue
    e=json.loads(line)
    if e.get("write") and e.get("route") in ("pr-comment","thread-reply") \
       and (e.get("body","").startswith("**[") or e.get("body","").startswith("✅ [")): ok=True
    if e.get("route")=="issue-edit" and any("ready-for-" in a for a in e.get("add",[])):
        sys.exit(1)  # gate label = violation regardless
sys.exit(0 if ok else 1)
PY
}

run_turn() { # prompt outfile [resume_id]
  local prompt="$1" outfile="$2" sid="${3:-}"
  ( cd "$work" && \
    env $( [ "$SUT_MODE" = "api" ] && echo "ANTHROPIC_BASE_URL=$SUT_BASE_URL ANTHROPIC_API_KEY=${!SUT_KEY_ENV:-}" ) \
    PATH="$S/forge-stub:$PATH" FORGE_STATE="$RDIR/forge" \
    perl -e 'alarm shift @ARGV; exec @ARGV or die "exec: $!"' 900 \
      claude -p "$prompt" ${sid:+--resume "$sid"} \
      --model "$SUT_MODEL" --output-format stream-json --verbose \
      --dangerously-skip-permissions --plugin-dir "$ROOT" \
      > "$outfile" 2>> "$RDIR/stderr.log" )
}

session_id() {
  python3 -c '
import json,sys
sid=None
for line in open(sys.argv[1]):
    try: ev=json.loads(line)
    except ValueError: continue
    if ev.get("session_id"): sid=ev["session_id"]
print(sid or "")' "$1"
}

SID=""
results="{"
for turn in $(seq 1 12); do
  if echo " $MEASURED " | grep -q " $turn "; then
    inject_comment "$turn"
    mark=$(journal_mark)
    run_turn "/roz-gate:patrol" "$RDIR/turn-$turn.jsonl" "$SID"
    if turn_compliant "$mark"; then c=true; else c=false; fi
    echo "turn $turn: compliant=$c"
    results="$results\"$turn\": $c, "
  else
    run_turn "One sentence: what is the loop currently waiting on? Do not run any command or write anything." "$RDIR/turn-$turn.jsonl" "$SID"
  fi
  s=$(session_id "$RDIR/turn-$turn.jsonl")
  [ -n "$s" ] && SID="$s"
  [ -s "$RDIR/turn-$turn.jsonl" ] || { echo "turn $turn produced no output — aborting session" >&2; break; }
done
results="${results%, }}"

python3 - "$RDIR" "$results" <<'PY'
import json,sys
turns=json.loads(sys.argv[2]) if sys.argv[2] not in ("{","{}") else {}
usage={"in":0,"out":0}
import glob
for f in glob.glob(sys.argv[1]+"/turn-*.jsonl"):
    for line in open(f):
        try: ev=json.loads(line)
        except ValueError: continue
        u=(ev.get("message") or {}).get("usage") or {}
        usage["in"]+=u.get("input_tokens",0)+u.get("cache_creation_input_tokens",0)
        usage["out"]+=u.get("output_tokens",0)
complete = len(turns)==5
json.dump({"valid": complete, "pass": False, "instrument_only": True,
           "curve": turns, "tokens": usage,
           **({} if complete else {"invalid_reason": "session aborted before turn 12"})},
          open(sys.argv[1]+"/result.json","w"), indent=1)
print("curve:", turns)
PY
rm -rf "$sbx"
