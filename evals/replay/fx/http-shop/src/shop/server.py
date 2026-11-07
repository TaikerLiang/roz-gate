"""The shop API — the http-shop fixture's implementation (#199). NOT the
port: the QA seat drives it over HTTP through bin/serve and never reads
this file. One in-memory store per process; orders move NEW → RESERVED →
CONFIRMED.

    POST /orders                 → 201 {"id": n, "status": "NEW"}
    GET  /orders/<id>            → 200 {"id", "status"} | 404 {"error"}
    POST /orders/<id>/reserve    → 200 {"id", "status": "RESERVED"} | 404 | 409 (not NEW)
    POST /orders/<id>/confirm    → 200 {"id", "status": "CONFIRMED"} | 404 | 409 (not RESERVED)
    POST /reset                  → 204 — the Given-state control point: forgets every order

The red-proofs and checkers mutate single lines of this file (a 201 that
answers 200, a reserve that says HELD, a 404 that answers 200) to prove a
suite asserts the contract rather than echoing the build.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

ORDERS = {}
NEXT = [1]


def reset():
    ORDERS.clear()
    NEXT[0] = 1


def create():
    oid = NEXT[0]
    NEXT[0] += 1
    ORDERS[oid] = {"id": oid, "status": "NEW"}
    return 201, ORDERS[oid]


def show(oid):
    o = ORDERS.get(oid)
    return (200, o) if o else (404, {"error": "no such order"})


def reserve(oid):
    o = ORDERS.get(oid)
    if not o:
        return 404, {"error": "no such order"}
    if o["status"] != "NEW":
        return 409, {"error": "not NEW", "status": o["status"]}
    o["status"] = "RESERVED"
    return 200, o


def confirm(oid):
    o = ORDERS.get(oid)
    if not o:
        return 404, {"error": "no such order"}
    if o["status"] != "RESERVED":
        return 409, {"error": "not RESERVED", "status": o["status"]}
    o["status"] = "CONFIRMED"
    return 200, o


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body=None):
        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        self.send_response(code)
        if payload:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def do_GET(self):
        m = re.fullmatch(r"/orders/(\d+)", self.path)
        if m:
            return self._send(*show(int(m.group(1))))
        self._send(404, {"error": "no such route"})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/orders":
            return self._send(*create())
        if self.path == "/reset":
            reset()
            return self._send(204)
        m = re.fullmatch(r"/orders/(\d+)/(reserve|confirm)", self.path)
        if m:
            step = reserve if m.group(2) == "reserve" else confirm
            return self._send(*step(int(m.group(1))))
        self._send(404, {"error": "no such route"})


def serve(port):
    HTTPServer.allow_reuse_address = True
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print("listening on %d" % srv.server_address[1], flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
