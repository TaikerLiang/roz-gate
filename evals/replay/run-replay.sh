#!/usr/bin/env bash
# Replay-tier runner. Usage:
#   run-replay.sh [--sut NAME] [--k N] [case ...]   # default: fable, all cases
#
# Measurement, not a gate: emits per-case observed rates with Wilson 90%
# intervals into report/<sut>/report.json and a table on stdout. No pass
# thresholds anywhere — the gate decision comes after the baseline.
#
# Multi-model: --sut resolves through models.yaml (mode, model, base_url,
# key_env). Claude Code is the runtime for every row; only the model swaps,
# whole-stack (seats ride the same endpoint as the main agent). Before any
# sweep spend, a 3-case plumbing smoke gate runs once per SUT — a row that
# fails it is marked HARNESS-INCOMPATIBLE, never scored 0: a broken
# translation adapter must not indict an innocent model.
#
# RESUMABLE by construction: each iteration persists to
# report/<sut>/<case>/run-<i>/result.json and a completed iteration is never
# re-run. A sweep interrupted by a rate limit continues where it stopped.
#
# Blindness guard: a ledger case whose check.sh contains no `# source:`
# citation is refused — assertions derive from the ledger and the owning
# prose, never from observed runs. (Smoke cases are exempt: they are
# plumbing proofs, not behavioural assertions.)
#
# CI runs the lint tier only, never this. Replay is local, on-demand,
# pre-release manual.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$S/../.." && pwd)"

SUT="fable"
K_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sut) SUT="$2"; shift 2 ;;
    --k) K_OVERRIDE="$2"; shift 2 ;;
    *) break ;;
  esac
done
CASES=("$@")
[ ${#CASES[@]} -eq 0 ] && CASES=($(ls "$S/cases"))
REPORT="$S/report/$SUT"

# ---- resolve the SUT row from models.yaml (flat flow-style entries)
eval "$(python3 - "$S/models.yaml" "$SUT" <<'PY'
import re, sys
name = sys.argv[2]
for line in open(sys.argv[1]):
    m = re.match(r"^(\w+):\s*\{(.*)\}\s*$", line.strip())
    if not m or m.group(1) != name: continue
    kv = dict(p.split(":", 1) for p in m.group(2).split(","))
    kv = {k.strip(): v.strip().strip('"') for k, v in kv.items()}
    print(f"SUT_MODE={kv.get('mode','subscription')}")
    print(f"SUT_MODEL={kv.get('model','')}")
    print(f"SUT_BASE_URL={kv.get('base_url','')}")
    print(f"SUT_KEY_ENV={kv.get('key_env','')}")
    sys.exit(0)
print("SUT_MODEL=")
PY
)"
[ -n "$SUT_MODEL" ] || { echo "unknown SUT '$SUT' (see models.yaml)" >&2; exit 2; }
if [ "$SUT_MODE" = "api" ]; then
  [ -n "$SUT_KEY_ENV" ] && [ -n "${!SUT_KEY_ENV:-}" ] || {
    echo "SUT '$SUT' is api-mode but \$$SUT_KEY_ENV is unset" >&2; exit 2; }
fi

sut_env() { # prints env assignments for the claude invocation
  if [ "$SUT_MODE" = "api" ]; then
    echo "ANTHROPIC_BASE_URL=$SUT_BASE_URL ANTHROPIC_API_KEY=\${$SUT_KEY_ENV}"
  fi
}

run_one() { # casedir rundir prompt timeout -> 0 ok / 1 invalid; writes artifacts
  local cdir="$1" rdir="$2" prompt="$3" timeout="$4"
  mkdir -p "$rdir/forge"
  local sbx; sbx=$(mktemp -d)
  local bare="$sbx/origin.git" work="$sbx/work"
  git init -q --bare "$bare"
  mkdir -p "$work"
  # Contract: seed.sh leaves a repo with >=1 commit, ending on main; it may
  # create extra branches. All refs are pushed to the local bare remote.
  ( cd "$work" && git init -q -b main \
    && bash "$cdir/seed.sh" "$ROOT" \
    && git checkout -q main \
    && git remote add origin "$bare" && git push -q origin --all ) \
    || { echo "seed failed" >&2; rm -rf "$sbx"; return 1; }

  cp "$cdir/state.json" "$rdir/forge/state.json"
  : > "$rdir/forge/journal.jsonl"

  ( cd "$work" && \
    env $( [ "$SUT_MODE" = "api" ] && echo "ANTHROPIC_BASE_URL=$SUT_BASE_URL ANTHROPIC_API_KEY=${!SUT_KEY_ENV:-}" ) \
    PATH="$S/forge-stub:$PATH" FORGE_STATE="$rdir/forge" \
    perl -e 'alarm shift @ARGV; exec @ARGV or die "exec: $!"' "$timeout" \
      claude -p "$prompt" \
      --model "$SUT_MODEL" --output-format stream-json --verbose \
      --dangerously-skip-permissions \
      --plugin-dir "$ROOT" \
      > "$rdir/transcript.jsonl" 2> "$rdir/stderr.log" )
  echo "$?" > "$rdir/exit"

  # Validity guards. Invalid ≠ red: the fixture or harness failed, not the
  # model. (a) no result event → the session never completed (an empty run
  # would pass every zero-writes case vacuously); (b) UNKNOWN forge route →
  # the fixture lacks a road the run needed.
  if ! grep -q '"type":[[:space:]]*"result"' "$rdir/transcript.jsonl"; then
    invalid_result "$rdir" "no result event — the session never completed"
    rm -rf "$sbx"; return 1
  fi
  if grep -q '"route": "UNKNOWN"' "$rdir/forge/journal.jsonl"; then
    invalid_result "$rdir" "forge stub hit an UNKNOWN route"
    rm -rf "$sbx"; return 1
  fi

  RUN_DIR="$rdir" WORK="$work" BARE="$bare" ROOT="$ROOT" \
    bash "$cdir/check.sh" > "$rdir/check.log" 2>&1
  local ok=$?
  python3 - "$rdir" "$ok" "$SUT_MODE" <<'PY'
import json,sys
rdir, ok, mode = sys.argv[1], sys.argv[2]=="0", sys.argv[3]
usage={"in":0,"out":0}; cost=None
for line in open(rdir+"/transcript.jsonl"):
    try: ev=json.loads(line)
    except ValueError: continue
    u=(ev.get("message") or {}).get("usage") or {}
    usage["in"] += u.get("input_tokens",0)+u.get("cache_creation_input_tokens",0)
    usage["out"] += u.get("output_tokens",0)
    if ev.get("type")=="result" and ev.get("total_cost_usd") is not None:
        cost=ev["total_cost_usd"]
json.dump({"valid": True, "pass": ok, "tokens": usage,
           "cost": ({"usd": cost} if mode=="api" else {"quota_tokens": usage, "note": "subscription quota, no dollar figure"})},
          open(rdir+"/result.json","w"), indent=1)
PY
  rm -rf "$sbx"
  return $([ "$ok" = 0 ] && echo 0 || echo 2)
}

invalid_result() {
  python3 - "$1" "$2" <<'PY'
import json,sys
json.dump({"valid": False, "pass": False, "invalid_reason": sys.argv[2]},
          open(sys.argv[1]+"/result.json","w"), indent=1)
PY
  echo "INVALID: $2"
}

# ---- smoke gate: 3 trivial plumbing cases at k=1, once per SUT
if [ ! -f "$REPORT/smoke-pass" ]; then
  [ -f "$REPORT/HARNESS_INCOMPATIBLE" ] && {
    echo "SUT '$SUT' is marked harness-incompatible; remove $REPORT/HARNESS_INCOMPATIBLE to retry" >&2
    exit 3; }
  echo "== smoke gate for SUT '$SUT' ($SUT_MODEL, $SUT_MODE) =="
  smoke_fail=0
  for sc in S1 S2 S3; do
    scdir="$S/smoke/$sc" srdir="$REPORT/smoke-$sc"
    if [ -f "$srdir/result.json" ] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("pass") else 1)' "$srdir/result.json"; then
      echo "smoke $sc: already passed"; continue
    fi
    prompt=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["prompt"])' "$scdir/case.json")
    run_one "$scdir" "$srdir" "$prompt" 300
    rc=$?
    [ "$rc" = 0 ] && echo "smoke $sc: PASS" || { echo "smoke $sc: FAIL"; smoke_fail=1; }
  done
  if [ "$smoke_fail" != 0 ]; then
    mkdir -p "$REPORT"
    echo "smoke gate failed — see report/$SUT/smoke-*/" > "$REPORT/HARNESS_INCOMPATIBLE"
    echo "SUT '$SUT': HARNESS-INCOMPATIBLE (plumbing, not compliance). Row is not scored." >&2
    exit 3
  fi
  touch "$REPORT/smoke-pass"
fi

# ---- ledger cases
for id in "${CASES[@]}"; do
  cdir="$S/cases/$id"
  [ -d "$cdir" ] || { echo "no such case: $id" >&2; exit 2; }
  driver=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("driver",""))' "$cdir/case.json")
  guardfile="$cdir/${driver:-check.sh}"
  grep -q '# source:' "$guardfile" || {
    echo "REFUSED $id: $(basename "$guardfile") has no '# source:' citation (blindness guard)" >&2
    exit 2
  }
  k=${K_OVERRIDE:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("k",5))' "$cdir/case.json")}
  for i in $(seq 1 "$k"); do
    rdir="$REPORT/$id/run-$i"
    [ -f "$rdir/result.json" ] && { echo "skip $id run-$i (done)"; continue; }
    echo "run  $id run-$i ..."
    if [ -n "$driver" ]; then
      # Instrument-style case: the driver owns the whole session shape.
      ROOT="$ROOT" S="$S" SUT_MODEL="$SUT_MODEL" SUT_MODE="$SUT_MODE" \
        SUT_BASE_URL="$SUT_BASE_URL" SUT_KEY_ENV="$SUT_KEY_ENV" \
        bash "$cdir/$driver" "$cdir" "$rdir" "$i"
      continue
    fi
    prompt=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["prompt"])' "$cdir/case.json")
    timeout=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("timeout",900))' "$cdir/case.json")
    run_one "$cdir" "$rdir" "$prompt" "$timeout"
    case $? in
      0) echo "PASS $id run-$i" ;;
      2) echo "FAIL $id run-$i" ;;
      *) echo "INVALID $id run-$i" ;;
    esac
  done
done

# ---- aggregate: per-case rate + Wilson 90% + cost. No thresholds.
python3 - "$REPORT" "$SUT" "$SUT_MODEL" "$SUT_MODE" <<'PY'
import json, math, os, sys
rep, sut, model, mode = sys.argv[1:5]
rows = []
for case in sorted(os.listdir(rep)):
    d = os.path.join(rep, case)
    if not os.path.isdir(d) or case.startswith("smoke-"): continue
    n = p = inv = tin = tout = 0; usd = 0.0
    for run in sorted(os.listdir(d)):
        f = os.path.join(d, run, "result.json")
        if not os.path.isfile(f): continue
        r = json.load(open(f))
        if r.get("instrument_only"):
            rows.append({"case": case, "run": run, "instrument": True,
                         "curve": r.get("curve", {}), "tokens": r.get("tokens")})
            continue
        if not r.get("valid"): inv += 1; continue
        n += 1; p += 1 if r.get("pass") else 0
        t = r.get("tokens", {}); tin += t.get("in",0); tout += t.get("out",0)
        usd += (r.get("cost") or {}).get("usd") or 0
    if n == 0 and inv == 0: continue
    rate = p/n if n else 0.0
    z = 1.6449
    if n:
        c = (rate + z*z/(2*n)) / (1 + z*z/n)
        h = z*math.sqrt(rate*(1-rate)/n + z*z/(4*n*n)) / (1 + z*z/n)
        lo, hi = max(0, c-h), min(1, c+h)
    else:
        lo = hi = 0.0
    rows.append({"case": case, "runs": n, "passes": p, "invalid": inv,
                 "rate": round(rate,3), "wilson90": [round(lo,3), round(hi,3)],
                 "tokens": {"in": tin, "out": tout},
                 **({"cost_usd": round(usd,4)} if mode=="api" else {"cost": "quota"})})
smoke = all(os.path.isfile(os.path.join(rep, f"smoke-S{i}", "result.json"))
            and json.load(open(os.path.join(rep, f"smoke-S{i}", "result.json"))).get("pass")
            for i in (1,2,3))
json.dump({"sut": sut, "model": model, "mode": mode,
           "smoke_gate": "pass" if smoke else "incomplete",
           "baseline_note": "opus is the protocol's ceiling reference, not necessarily "
                            "the production loop's current operator; the current operator "
                            "appears as its own row.",
           "cases": rows}, open(os.path.join(rep, "report.json"), "w"), indent=1)
print(f"\nSUT {sut} ({model}, {mode}) — smoke gate: {'pass' if smoke else 'incomplete'}")
print(f"{'case':8} {'rate':>6} {'k':>3}  wilson90        tokens(in/out)")
for r in rows:
    if r.get("instrument"):
        print(f"{r['case']:8} instrument-only  curve: {r['curve']}")
        continue
    print(f"{r['case']:8} {r['rate']:6.0%} {r['runs']:3}  "
          f"[{r['wilson90'][0]:.0%},{r['wilson90'][1]:.0%}]"
          f"{'':4}{r['tokens']['in']}/{r['tokens']['out']}"
          + (f"  ({r['invalid']} invalid)" if r['invalid'] else ""))
PY
