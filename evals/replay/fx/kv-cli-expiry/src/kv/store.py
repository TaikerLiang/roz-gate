"""The kv store — NOT the port. A sibling of src/kv/cli.py under src/, and
the file a QA seat is tempted to read to learn the on-disk shape; the
contract says the store is opaque, and rule E denies the read (#197).

The shape is an envelope only the CLI writes: the format tag, the store's
clock, and each key's value with the clock second it expires at. A file
without it is not a store (exit 65) — so a Given arranged by writing the
file by hand, or by editing a key's expiry in it, depends on this layout,
which the contract never promises.
"""
import json
import os
import sys

FORMAT, CLOCK, DATA, VALUE, EXPIRES = "kv/1", "clock", "data", "value", "expires_at"
BAD_STORE = 65


def load(path):
    """(clock, {key: (value, expires_at)}); a path that does not exist yet
    is a new store, its clock at 0."""
    if not os.path.exists(path):
        return 0, {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        clock = raw[CLOCK]
        data = {k: (e[VALUE], e[EXPIRES]) for k, e in raw[DATA].items()}
        ok = raw.get("format") == FORMAT and isinstance(clock, int) \
            and all(isinstance(x, int) for _, x in data.values())
    except (ValueError, KeyError, TypeError, AttributeError):
        ok = False
    if not ok:
        sys.stderr.write("kv: not a kv store: %s\n" % path)
        sys.exit(BAD_STORE)
    return clock, data


def save(path, clock, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, CLOCK: clock,
                   DATA: {k: {VALUE: v, EXPIRES: x} for k, (v, x) in data.items()}},
                  f, sort_keys=True)
    os.replace(tmp, path)
