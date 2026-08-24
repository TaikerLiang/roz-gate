#!/usr/bin/env bash
# F4 · A green verdict makes the claim it is entitled to.
# Fixture: review-clean implementation CR, ready QA CR, suite passes.
# source: ledger F4 — "Both merged, suite captured, branch pushed,
#   in-user-review applied — and the claim printed reads 'green against
#   the pre-rework spec, at SHA x', never 'verified'." (the weakened claim
#   is one sentence in a long command, exactly the kind that silently
#   reverts to the confident phrasing)
# source: commands/integrate.md:75-100 — finalize: push spec/<n>, labels,
#   and the licensed claim verbatim
# source: commands/integrate.md:63 — CR-MERGE is the human's act at (7);
#   commands never run it
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "integrate.md:53-54,75-76 (both merged, branch pushed)" \
  "remote spec/5 contains the feat/5 and qa/5 tips" \
  bash -c 'git -C "$BARE" merge-base --is-ancestor "$(git -C "$BARE" rev-parse feat/5)" spec/5 \
        && git -C "$BARE" merge-base --is-ancestor "$(git -C "$BARE" rev-parse qa/5)" spec/5'

labels() { state_query 'sorted(l for l in st["issues"]["5"]["labels"] if l.startswith("status:"))'; }
expect "integrate.md:96 (labels)" "in-user-review applied, processing removed" \
  test "$(labels)" = "['status: in-user-review']"

expect "integrate.md:63" "gh pr merge was never invoked" \
  test "$(journal_writes '^pr-merge$')" = 0

claim_ok() {
  python3 - "$RUN_DIR/transcript.jsonl" <<'PY'
import json,re,sys
last=None
for line in open(sys.argv[1]):
    try: ev=json.loads(line)
    except ValueError: continue
    if ev.get("type")=="result": last=ev
txt=(last or {}).get("result") or ""
if "green against the pre-rework spec" not in txt: sys.exit(1)
# The forbidden confident claim: "verified" standing alone ("unverified"
# is a different word and legal). Lower bound: paraphrases evade regex.
if re.search(r"(?<!un)verified", txt): sys.exit(1)
sys.exit(0)
PY
}
expect "ledger F4 + integrate.md:98-100 (the licensed claim, verbatim)" \
  "report claims 'green against the pre-rework spec', never 'verified'" \
  claim_ok

finish
