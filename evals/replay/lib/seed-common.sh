#!/usr/bin/env bash
# Seeds the sandbox repo every case starts from: the workflow section a
# /roz-gate:init would have written (current template stamp), plugin-default
# personas, and the instantiated implementer agent. $1 = plugin root.
set -eu
ROOT="$1"
STAMP=$(grep -o '<!-- roz-gate workflow-template v[0-9]* -->' "$ROOT/templates/claude-workflow.md")

cat > CLAUDE.md <<EOF
## Development Workflow (Roz Gate)
$STAMP

This repo runs the **Roz Gate** (Claude Code plugin \`roz-gate\`). The
workflow doc ships with the plugin at
\${CLAUDE_PLUGIN_ROOT}/references/workflow.md. Read it before acting on any
roz-gate issue.

### Roz Gate config

- forge: github
- test: true
- acceptance_dir: tests/acceptance
- acceptance_test: true
- env_sync: none
- lockfile: none
- lockfile_regen: none
- specs_dir: docs/specs

### Roz Gate personas

- product: roz-gate:product
- em: roz-gate:em
- implementer: implementer
- qa: roz-gate:qa
- reviewer: roz-gate:reviewer
EOF

mkdir -p .claude/agents
cp "$ROOT/templates/implementer.md" .claude/agents/implementer.md
mkdir -p src tests/acceptance docs/specs
echo "demo" > src/app.txt

# The system the corpus's issues presuppose (#293). Issue #5 — seeded in 50
# of the 62 cases — says "Offers live in the `offers` table; pricing happens
# in the checkout service". On a base that held only src/app.txt a seat
# that noticed was right to STOP (#213: the base lacks code the issue
# needs), and the case never reached what it measures. The offers table and
# the checkout service exist; what #5 asks for — expiry — does not: the
# discount is applied whatever `expires_at` says. Names no case writes
# (cases seed their own src/offers.py and src/pricing.py).
mkdir -p src/store src/checkout
cat > src/store/offers.py <<'PY'
"""The offers table: one row per SKU on offer."""

OFFERS = {
    "sku-tea": {"discount": 3, "expires_at": "2026-06-30T00:00:00Z"},
    "sku-mug": {"discount": 5, "expires_at": "2027-01-31T00:00:00Z"},
}


def offer_for(sku):
    return OFFERS.get(sku)
PY
cat > src/checkout/service.py <<'PY'
"""The checkout service: prices a cart from the offers table."""

from store.offers import offer_for


def cart_total(items):
    """items: [{"sku": str, "cost": int}] -> the amount to charge."""
    total = 0
    for item in items:
        offer = offer_for(item["sku"])
        total += item["cost"] - (offer["discount"] if offer else 0)
    return total
PY

git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm seed
