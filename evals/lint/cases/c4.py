"""C4 · track: fast + ready-for-spec refused                 (hook-covered)
The control case: it needs no lint because it has teeth. Enforced by
hooks/guard-gate and proven in hooks/tests/test_guard_gate.py ("gate label
add blocked"), which the same release gate runs. Nothing to check here.
"""

from lib.lintkit import c

META = {
    "id": 'C4',
    "title": 'track: fast + ready-for-spec refused',
    "tier": 'hook (guard-gate)',
    "ledger": None,
}

c.passed += 1
c.ok("C4: covered by guard-gate (see hooks/tests/test_guard_gate.py, run by the same gate)")
