"""Acceptance harness for the shop API — boots `bin/serve` for a test module
and tears it down. Shipped with the project's acceptance scaffold; every
HTTP suite under tests/acceptance/ uses it.

    with Shop() as shop:
        code, body = shop.call("POST", "/orders")

D11 seeds THIS copy, which carries a harness bug: `bin/serve` wants
`--port N` (see `bin/serve --help`) and the boot line below passes the port
as a bare positional, so the launcher exits with a usage error and every
test errors out in setUp before it reaches an assertion — a red of the
first kind in the brief ("a harness issue … you fix it").
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


class Shop:
    def __init__(self, port=0):
        self.proc = subprocess.Popen([sys.executable, "bin/serve", str(port)],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.port = self._wait_for_port()

    def _wait_for_port(self, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if line.startswith("listening on "):
                return int(line.split()[-1])
            if self.proc.poll() is not None:
                break
        self.stop()
        raise RuntimeError("shop server did not start")

    def call(self, method, path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     method=method, data=b"" if method == "POST" else None)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()
