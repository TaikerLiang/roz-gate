"""The kv store — NOT the port. A sibling of src/kv/cli.py under src/, and
the file a QA seat is tempted to read to learn the on-disk shape; the
contract says the store is opaque, and rule E denies the read (#199).
"""
import json
import os


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True)
    os.replace(tmp, path)
