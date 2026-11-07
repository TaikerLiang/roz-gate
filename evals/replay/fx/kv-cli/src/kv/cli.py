#!/usr/bin/env python3
"""kv — a file-backed key/value CLI: the kv-cli fixture's **test port**
(evals/replay/fx/kv-cli, #199). The acceptance suite drives this file as a
child process; it is the one file under src/ the QA seat may read.

    python3 src/kv/cli.py [--store PATH] set <key> <value>
    python3 src/kv/cli.py [--store PATH] get <key>        # prints the value
    python3 src/kv/cli.py [--store PATH] del <key>

The store is a JSON file: --store, else $KV_STORE, else ./kv.json. Exit 0
on success. `get` and `del` of a missing key print `kv: not found: <key>`
on stderr and exit 2. A usage error exits 64.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.kv.store import load, save  # noqa: E402

NOT_FOUND = 2
USAGE = 64


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("kv: %s\n" % message)
        sys.exit(USAGE)


def missing(key):
    sys.stderr.write("kv: not found: %s\n" % key)
    return NOT_FOUND


def main(argv):
    p = Parser(prog="kv")
    p.add_argument("--store")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    s = sub.add_parser("set")
    s.add_argument("key")
    s.add_argument("value")
    g = sub.add_parser("get")
    g.add_argument("key")
    d = sub.add_parser("del")
    d.add_argument("key")
    a = p.parse_args(argv)
    path = a.store or os.environ.get("KV_STORE") or "kv.json"
    data = load(path)
    if a.cmd == "set":
        data[a.key] = a.value
        save(path, data)
        return 0
    if a.cmd == "get":
        if a.key not in data:
            return missing(a.key)
        print(data[a.key])
        return 0
    if a.cmd == "del":
        if a.key not in data:
            return missing(a.key)
        del data[a.key]
        save(path, data)
        return 0
    return USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
