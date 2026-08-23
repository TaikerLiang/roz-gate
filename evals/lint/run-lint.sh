#!/usr/bin/env bash
# Lint tier of the eval ledger — static checks on the plugin's own sources.
#
# Every case here guards against failure mode 2: the RULE ITSELF is broken,
# so every stage faithfully executes it and reports green. Cases that guard
# a runtime check (a grep the model executes from prose) get two layers:
#   pattern proof — the canonical pattern, held here, runs against fixtures;
#   source conformance — the prose must carry that same pattern verbatim.
# Either layer alone is a hole: pattern-only proves a pattern nobody ships;
# conformance-only ships an unproven pattern. See evals/README.md.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
R="$(cd "$S/../.." && pwd)"
FX="$S/fx"
pass=0 fail=0

ok() { echo "PASS $1"; pass=$((pass+1)); }
ko() { echo "FAIL $1${2:+ — $2}"; fail=$((fail+1)); }

# check NAME EXPECT(0|1) CMD... — EXPECT 0: cmd must succeed; 1: must fail
check() {
  local name="$1" want="$2"; shift 2
  if "$@" >/dev/null 2>&1; then rc=0; else rc=1; fi
  [ "$rc" = "$want" ] && ok "$name" || ko "$name" "$(printf '%q ' "$@")"
}
# src NAME FILE FIXED_STRING — source conformance: file carries the literal
src() {
  local name="$1" file="$2" lit="$3"
  grep -qF -- "$lit" "$R/$file" && ok "$name" || ko "$name" "$file lacks the literal: $lit"
}

# ---------------------------------------------------------------------------
# B1 · a compound tag evades the literal it contains        (defect: 1.12.0-)
# Canonical unverified-claim pattern: tag position = start of line (a wrap
# continuation) or after ( or , (its own tag, or illegally merged into one).
UNV='(^|[(,])[[:space:]]*unverified'
check "B1 pattern: compound (from Q4, unverified) found"   0 grep -qE "$UNV" "$FX/b1_compound.md"
check "B1 pattern: conventional (unverified) found"        0 grep -qE "$UNV" "$FX/b1_plain.md"
check "B1 pattern: wrap-split compound found"              0 grep -qE "$UNV" "$FX/b1_wrapped.md"
check "B1 pattern: the word in prose NOT flagged"          1 grep -qE "$UNV" "$FX/b1_negative.md"
src "B1 conformance: Path B check carries the widened pattern" \
  commands/next-stage.md  "grep -nE '$UNV'"
src "B1 conformance: promote check carries the widened pattern" \
  commands/spec-answers.md "grep -nE '$UNV'"
check "B1 conformance: no site still greps only the old literal" 1 \
  grep -rqF "grep -n '(unverified)'" "$R/commands" "$R/references"

# ---------------------------------------------------------------------------
# B2 · a line-wrapped tag survives the check                (defect: 1.12.0-)
# Checks match the OPENING TOKEN only; a wrapped tag is present, never absent.
check "B2 pattern: wrapped (assumed-empirical: detected"   0 grep -qF '(assumed-empirical:' "$FX/b2_wrapped_assumed.md"
check "B2 pattern: wrapped (measured read as present"      0 grep -qF '(measured' "$FX/b2_wrapped_measured.md"
# The anti-pattern this rule forbids — requiring the closing paren on the
# same line — misses exactly the wrapped tag. Kept as executable rationale.
check "B2 rationale: same-line-paren matching would miss it" 1 \
  grep -qE '\(measured[^)]*\)' "$FX/b2_wrapped_measured.md"
src "B2 conformance: the opening-token rule names all three tokens" \
  commands/next-stage.md '`(unverified)`, `(assumed-empirical:`, `(measured`'
src "B2 conformance: opening-token-only is stated as the rule" \
  commands/next-stage.md 'matches the **opening token only**'

# ---------------------------------------------------------------------------
# B3 · the marker convention is identical everywhere        (preventive)
# Canonical marker literals: '**[' (agent write opens) and '✅ [' (resolution).
# The sentences stating the convention legitimately differ; the LITERALS may
# not. Near-miss variants (no space, fullwidth bracket) must not exist.
for f in commands/next-stage.md commands/patrol.md commands/spec-answers.md commands/review-answers.md; do
  src "B3: $f carries the '**[' marker literal" "$f" '**['
done
for f in commands/patrol.md commands/spec-answers.md commands/review-answers.md; do
  src "B3: $f carries the '✅ [' marker literal" "$f" '✅ ['
done
check "B3: no '✅[' (missing space) anywhere" 1 \
  grep -rq '✅\[' "$R/commands" "$R/references" "$R/agents" "$R/templates"
check "B3: no fullwidth-bracket marker variant anywhere" 1 \
  grep -rqE '✅ ?【|\*\*【' "$R/commands" "$R/references" "$R/agents" "$R/templates"

# ---------------------------------------------------------------------------
# B4 · an agent write never opens with a quote block        (defect: 1.11.0-)
# Static layer only: the write rules must be stated where writes happen.
# (Teeth — a guard-gate deny — are a separate, greenlit follow-up change.)
src "B4: question comments must open with the marker" \
  commands/next-stage.md 'MUST start with `**['
src "B4: the quote-block opening is forbidden in review replies" \
  commands/review-answers.md 'Never open with a quote block'

# ---------------------------------------------------------------------------
# C3 · `processing` coexists with a phase label             (preventive)
# Oracle (patrol.md's coexistence sentence, executable): `processing` is a
# mutex; all other `status:` labels are phases, at most one at a time.
MUTEX='processing'
PHASES='ready-for-spec in-spec-review ready-for-dev in-user-review blocked'
TRACKS='spec fast'
legal() { # space-separated status label names -> 0 legal / 1 illegal
  local n=0 l
  for l in $1; do
    [ "$l" = "$MUTEX" ] && continue
    case " $PHASES " in *" $l "*) n=$((n+1)) ;; *) return 1 ;; esac
  done
  [ "$n" -le 1 ]
}
check "C3: phase + processing is legal (a stale pair names the death stage)" 0 \
  legal 'in-spec-review processing'
check "C3: two phase labels are illegal" 1 legal 'in-spec-review in-user-review'
check "C3: an unknown status label is illegal" 1 legal 'shipping'
# Completeness — the drift alarm: every backticked label literal in the
# sources must be in the oracle, or the suite goes red on the new label.
c3_drift=""
while IFS= read -r l; do
  name=${l#\`status: }; name=${name%\`}
  case " $PHASES $MUTEX " in *" $name "*) ;; *) c3_drift="$c3_drift $l" ;; esac
done < <(grep -rhoE '`status: [a-z-]+`' "$R/commands" "$R/references" "$R/templates" "$R/agents" | sort -u)
while IFS= read -r l; do
  name=${l#\`track: }; name=${name%\`}
  case " $TRACKS " in *" $name "*) ;; *) c3_drift="$c3_drift $l" ;; esac
done < <(grep -rhoE '`track: [a-z]+`' "$R/commands" "$R/references" "$R/templates" "$R/agents" | sort -u)
[ -z "$c3_drift" ] && ok "C3 completeness: every source label is in the oracle" \
  || ko "C3 completeness: labels missing from the oracle:$c3_drift"

# ---------------------------------------------------------------------------
# C4 · track: fast + ready-for-spec refused                 (hook-covered)
# The control case: it needs no lint because it has teeth. Enforced by
# hooks/guard-gate and proven in hooks/tests/run-tests.sh ("gate label add
# blocked"), which the same release gate runs. Nothing to check here.
ok "C4: covered by guard-gate (see hooks/tests/run-tests.sh, run by the same gate)"

# ---------------------------------------------------------------------------
# C6 · CR lookup sees merged CRs where it must              (defect: 1.11.0-)
gh_crfind=$(grep -F 'CR-FIND' "$R/references/forge-github.md")
gl_crfind=$(grep -F 'CR-FIND' "$R/references/forge-gitlab.md")
check "C6: github adapter CR-FIND documents --state all for merged CRs" 0 \
  grep -qF -- '--state all' <<<"$gh_crfind"
check "C6: gitlab adapter CR-FIND documents --all for merged MRs" 0 \
  grep -qF -- '--all' <<<"$gl_crfind"
src "C6: the post-integration detection path cites the all-states form" \
  commands/spec-answers.md 'all-states form'
inflight=$(grep -F 'no `status:`, `track: spec`' "$R/commands/patrol.md")
check "C6: patrol's in-flight row keeps the open-only default" 1 \
  grep -qE -- 'all-states|--state all|--all\b' <<<"$inflight"

# ---------------------------------------------------------------------------
# D1 · the reviewer receives the claim it reviews against   (defect: 1.8.0-)
b5=$(awk '/^### B5\. /,/^### B5b\. /' "$R/commands/next-stage.md")
check "D1: stage-(5) dispatch attaches spec.md" 0 grep -qF 'spec.md' <<<"$b5"
check "D1: stage-(5) dispatch attaches technical-spec.md" 0 grep -qF 'technical-spec.md' <<<"$b5"
check "D1: attachment is stated as receiving the claim, not inferring it" 0 \
  grep -qF 'inference of intent' <<<"$b5"

# ---------------------------------------------------------------------------
# E3 · the implementer can stop and ask at stage (3)        (defect: 1.12.0-)
b3=$(awk '/^### B3\. Dispatch/,/^### B4\. /' "$R/commands/next-stage.md")
check "E3: stage-(3) dispatch states the contract-gap stop route" 0 \
  grep -qF 'A contract gap you cannot resolve' <<<"$b3"
check "E3: unilateral in-code decisions are forbidden explicitly" 0 \
  grep -qF 'never decide unilaterally' <<<"$b3"

# ---------------------------------------------------------------------------
# E4 · the stage-(5) reviewer has the same route            (defect: 1.12.0-)
check "E4: a contract-ambiguity finding routes to the spec CR" 0 \
  grep -qF 'contract ambiguity routes to a spec-CR' <<<"$b5"
check "E4: reviewer-to-implementer settlement is forbidden explicitly" 0 \
  grep -qF 'never settled' <<<"$b5"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
