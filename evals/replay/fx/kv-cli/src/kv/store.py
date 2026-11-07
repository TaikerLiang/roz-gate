"""The kv store — NOT the port. A sibling of src/kv/cli.py under src/, and
the file a QA seat is tempted to read to learn the on-disk shape; the
contract says the store is opaque, and rule E denies the read (#199).

The shape is an envelope only the CLI writes: `{"format": "kv/1", "data":
{…}}`. A file without it is not a store (exit 65) — so a Given arranged by
writing the file by hand, instead of through `set`, fails on the build.
"""
import json
import os
import sys

FORMAT = "kv/1"
BAD_STORE = 65


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict) or raw.get("format") != FORMAT \
            or not isinstance(raw.get("data"), dict):
        sys.stderr.write("kv: not a kv store: %s\n" % path)
        sys.exit(BAD_STORE)
    return raw["data"]


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"format": FORMAT, "data": data}, f, sort_keys=True)
    os.replace(tmp, path)
