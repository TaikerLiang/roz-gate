#!/usr/bin/env bash
# F15 sandbox: ConsoleAPI #28's shape (#205) — four gated issues whose forge
# relationships say what may run (state.json `blocked_by`): #10 and #11
# wait on open #9 (#11 also names closed #8), #12's only blocker (#8) is
# closed, and #13's lookup is refused (HTTP 403). The local key
# `inbox_label: discuss` keeps the blockers themselves (track-less, no
# `discuss`) out of the inbox, so the pass's one actionable row is #12.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# What the closed #8 delivered (#367): the order ledger schema #12 builds on.
# On a base without it a seat rightly STOPs #12 (#213: the base lacks code
# the issue needs) and the closed blocker releases nothing. Nothing of the
# open #9 (the payment provider adapter) is here.
mkdir -p src/orders
cat > src/orders/ledger.py <<'PY'
"""The order ledger: one row per order, append-only (#8)."""

COLUMNS = ("order_id", "customer_id", "placed_at", "total", "currency", "status")
STATUSES = ("placed", "paid", "refunded", "cancelled")

LEDGER = []


def record(order_id, customer_id, placed_at, total, currency, status="placed"):
    """Append one order row; placed_at is an ISO-8601 UTC string."""
    if status not in STATUSES:
        raise ValueError("unknown status: %s" % status)
    row = dict(zip(COLUMNS, (order_id, customer_id, placed_at, total, currency, status)))
    LEDGER.append(row)
    return row


def orders_for(customer_id):
    """A customer's rows, oldest first."""
    return [row for row in LEDGER if row["customer_id"] == customer_id]
PY
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "orders: the order ledger schema (closes #8)"
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
grep -q '"inbox_label"' .claude/roz-gate.local.json
