#!/usr/bin/env python3
"""kv — a file-backed key/value CLI whose keys expire: the kv-cli-expiry
fixture's **test port** (evals/replay/fx/kv-cli-expiry, #197). The
acceptance suite drives this file as a child process; it is the one file
under src/ the QA seat may read.

    python3 src/kv/cli.py [--store PATH] set <key> <value>
    python3 src/kv/cli.py [--store PATH] get <key>        # prints the value
    python3 src/kv/cli.py [--store PATH] del <key>
    python3 src/kv/cli.py [--store PATH] advance-clock <seconds>

The store is a JSON file: --store, else $KV_STORE, else ./kv.json. Each
store keeps its own clock in whole seconds. `set` stamps the key to
expire TTL seconds later on that clock; a key whose expiry is at or before
the clock is expired and reads as missing. Exit 0 on success. `get` and
`del` of a missing key print `kv: not found: <key>` on stderr and exit 2.
A usage error exits 64; a store file that is not the CLI's own exits 65.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.kv.store import load, save  # noqa: E402

NOT_FOUND = 2
USAGE = 64
TTL = 3600


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("kv: %s\n" % message)
        sys.exit(USAGE)


def missing(key):
    sys.stderr.write("kv: not found: %s\n" % key)
    return NOT_FOUND


def expired(expires_at, now):
    return expires_at <= now


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
    c = sub.add_parser("advance-clock")
    c.add_argument("seconds", type=int)
    a = p.parse_args(argv)
    path = a.store or os.environ.get("KV_STORE") or "kv.json"
    clock, data = load(path)
    if a.cmd == "set":
        data[a.key] = (a.value, clock + TTL)
        save(path, clock, data)
        return 0
    if a.cmd == "advance-clock":
        if a.seconds < 0:
            p.error("advance-clock: seconds must be >= 0")
        save(path, clock + a.seconds, data)
        return 0
    if a.key not in data or expired(data[a.key][1], clock):
        return missing(a.key)
    if a.cmd == "get":
        print(data[a.key][0])
        return 0
    if a.cmd == "del":
        del data[a.key]
        save(path, clock, data)
        return 0
    return USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
