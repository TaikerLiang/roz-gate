#!/usr/bin/env python3
"""Export replay run dirs to Langfuse — one run, one trace. Usage:

    export_langfuse.py [--dry-run] [--force] <run-dir> ...
        # e.g. evals/replay/report/opus/A1/run-1 — or a shell glob over a sweep

What a run dir already holds is the whole model interaction; this only
re-shapes it (issue #80):

- the trace is the run: root span `<case>/run-<i>`, Langfuse session
  `<sut>/<case>` (so a case's k runs sit together), tags case / sut /
  verdict, input = the case prompt, output = the result event's text;
  metadata `plugin_sha` only when the runner exports as it goes (a backfill
  cannot know the revision the run executed under, so it carries none and
  `backfilled: true`);
- a **generation** per API call — model, usage (incl. cache tokens), the
  thinking / text / tool_use blocks as output, what it answered as input
  (the user message carrying the tool results; for the first call, the
  case prompt — or in a sub-agent, its Agent tool's input), start = the
  previous message's timestamp. The stream emits one
  assistant event per content block, all sharing the message id — tool
  results interleave between them — and they are merged by that id (A1
  run-1: 30 events, 14 calls);
- a **tool** span per tool_use — arguments in, the tool_result matched by
  `tool_use_id` out, ended at the user message that carried it;
  `is_error` → level ERROR; events tagged `parent_tool_use_id` nest under
  that tool's span (the sub-agent tree);
- the forge journal's **writes** as events, in journal order (the journal
  has no ids or timestamps — nothing links a write to a transcript step);
- **scores** on the trace: `pass`, `valid` (comment = invalid_reason),
  `cost_usd` when known, and one per check.log claim (comment = its source).

Wire: OTLP/HTTP JSON to `$LANGFUSE_HOST/api/public/otel/v1/traces` with
Langfuse's attribute keys, scores to `$LANGFUSE_HOST/api/public/scores`;
Basic auth from `$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY`; the optional
`$LANGFUSE_PROJECT_ID` only completes the printed UI link. Ids are
deterministic (session id, message ids, tool_use ids) — but Langfuse v4
stores observations as immutable events, so a re-export **appends copies**
rather than replacing. An export therefore leaves `langfuse.json` (trace
id, link, time) in the run dir and a run dir carrying one is skipped
unless `--force`. Stdlib only, Python 3.9-compatible, like the rest of the
harness. `--dry-run` prints the payload, touches no network and writes no
marker — the harness red-proof asserts its shape.

`run_replay.py` calls `maybe_export()` after every result.json when the
three variables are set; nothing set → nothing happens; a failure is one
stderr line and never changes a verdict.

Not captured: the system prompt and tool definitions (not in the
transcript), F6 driver runs (no transcript.jsonl → skipped, said so).
"""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(S))
ENV = ("LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
FIELD_CAP = 64 * 1024          # bytes of one input/output before it is cut
BATCH_CAP = 2 * 1024 * 1024    # bytes of JSON per OTLP request
SERVICE = "roz-gate-evals"
SCOPE = "roz-gate.export_langfuse"


class ExportError(Exception):
    pass


class AlreadyExported(ExportError):
    pass


MARKER = "langfuse.json"


def exported(rdir):
    """The run dir's export record, or None."""
    return load_json(os.path.join(rdir, MARKER))


def warn(msg):
    print("export_langfuse: %s" % msg, file=sys.stderr)


# ---- config ---------------------------------------------------------------
def env_config():
    """The three variables, or None (and one warning when only some are set)."""
    vals = {k: os.environ.get(k, "").strip() for k in ENV}
    present = [k for k in ENV if vals[k]]
    if not present:
        return None
    if len(present) < len(ENV):
        warn("skipped — %s unset" % ", ".join(k for k in ENV if not vals[k]))
        return None
    vals["LANGFUSE_HOST"] = vals["LANGFUSE_HOST"].rstrip("/")
    return vals


# ---- small helpers --------------------------------------------------------
def read_jsonl(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def ts_ns(s):
    """'2026-09-07T15:15:01.997Z' → integer nanoseconds since the epoch."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+0000"
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if "." in s else "%Y-%m-%dT%H:%M:%S%z"
    dt = datetime.strptime(s, fmt)
    return int(dt.timestamp()) * 10**9 + dt.microsecond * 1000


def hid(n, *parts):
    return hashlib.md5("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:n]


def clip(s):
    b = s.encode("utf-8")
    if len(b) <= FIELD_CAP:
        return s
    cut = b[:FIELD_CAP].decode("utf-8", "ignore")
    return cut + "…[truncated %d bytes]" % (len(b) - len(cut.encode("utf-8")))


def js(obj):
    if isinstance(obj, str):
        return clip(obj)
    return clip(json.dumps(obj, ensure_ascii=False))


def attr(key, value):
    if isinstance(value, bool):
        v = {"boolValue": value}
    elif isinstance(value, int):
        v = {"intValue": str(value)}
    elif isinstance(value, float):
        v = {"doubleValue": value}
    elif isinstance(value, (list, tuple)):
        v = {"arrayValue": {"values": [attr("", x)["value"] for x in value]}}
    else:
        v = {"stringValue": "" if value is None else str(value)}
    return {"key": key, "value": v}


def span(trace_id, span_id, name, start, end, attrs, parent=None, level=None, status_msg=None):
    s = {"traceId": trace_id, "spanId": span_id, "name": name, "kind": 1,
         "startTimeUnixNano": str(start), "endTimeUnixNano": str(max(start, end)),
         "attributes": [attr(k, v) for k, v in attrs if v is not None and v != ""],
         "status": {"code": 2 if level == "ERROR" else 0}}
    if parent:
        s["parentSpanId"] = parent
    if level:
        s["attributes"].append(attr("langfuse.observation.level", level))
    if status_msg:
        s["attributes"].append(attr("langfuse.observation.status_message", status_msg))
        s["status"]["message"] = status_msg
    return s


def parse_claims(path):
    """check.log lines: `ok   <desc>` / `FAIL <desc>  [<detail>]`."""
    claims = []
    try:
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("ok   "):
                claims.append((line[5:].strip(), True, ""))
            elif line.startswith("FAIL "):
                body = line[5:]
                m = re.match(r"^(.*?)\s+\[(.*)\]\s*$", body)
                if m:
                    claims.append((m.group(1).strip(), False, m.group(2)))
                else:
                    claims.append((body.strip(), False, ""))
    except OSError:
        pass
    return claims


def plugin_sha():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


# ---- the mapping ----------------------------------------------------------
def build(rdir, case, sut, run, prompt, backfilled=False):
    """Return (spans, scores, summary) for one run dir. Raises ExportError
    when the dir has no transcript (F6 driver runs)."""
    transcript = os.path.join(rdir, "transcript.jsonl")
    if not os.path.isfile(transcript):
        raise ExportError("no transcript.jsonl in %s (a driver run?) — skipped" % rdir)
    events = read_jsonl(transcript)
    result = load_json(os.path.join(rdir, "result.json"), {}) or {}
    journal = read_jsonl(os.path.join(rdir, "forge", "journal.jsonl"))
    claims = parse_claims(os.path.join(rdir, "check.log"))
    res_ev = None
    for ev in events:
        if ev.get("type") == "result":
            res_ev = ev
    session_id = (res_ev or {}).get("session_id") or hid(32, "session", os.path.abspath(rdir))
    trace_id = hid(32, "trace", session_id)
    root_id = hid(16, "root", trace_id)
    name = "%s/run-%s" % (case, run)

    stamps = [ts_ns(ev["timestamp"]) for ev in events
              if ev.get("type") in ("assistant", "user") and ev.get("timestamp")]
    if stamps:
        t0, t1 = min(stamps), max(stamps)
    else:
        t0 = t1 = int(datetime.now(timezone.utc).timestamp()) * 10**9
    if res_ev and res_ev.get("duration_ms") and t1 == t0:
        t1 = t0 + int(res_ev["duration_ms"]) * 10**6

    valid = bool(result.get("valid"))
    verdict = "invalid" if not valid else ("pass" if result.get("pass") else "fail")
    model = ""
    spans, tool_spans = [], {}
    last_user = {"": prompt or ""}   # per context: what the next call answers —
    # the main prompt at the root, the Agent tool's input in each sub-agent
    gens = tools = 0
    prev = t0
    gen_by_id = {}    # message id → (span, merged content) — the API call being streamed
    for ev in events:
        kind = ev.get("type")
        if kind not in ("assistant", "user") or not ev.get("timestamp"):
            continue
        ts = ts_ns(ev["timestamp"])
        parent_tool = ev.get("parent_tool_use_id") or ""
        parent = tool_spans[parent_tool]["spanId"] if parent_tool in tool_spans else root_id
        msg = ev.get("message") or {}
        content = msg.get("content")
        if kind == "assistant":
            blocks = content if isinstance(content, list) else []
            mid = msg.get("id") or ""
            if mid and mid in gen_by_id:
                # another block of the same API call (tool results interleave
                # between them): extend, do not add
                g, merged = gen_by_id[mid]
                merged.extend(blocks)
                g["endTimeUnixNano"] = str(max(int(g["startTimeUnixNano"]), ts))
                g["attributes"] = [a for a in g["attributes"]
                                   if a["key"] != "langfuse.observation.output"]
                g["attributes"].append(attr("langfuse.observation.output", js(merged)))
            else:
                gens += 1
                model = msg.get("model") or model
                u = msg.get("usage") or {}
                usage = {"input": u.get("input_tokens", 0),
                         "output": u.get("output_tokens", 0),
                         "cache_read_input_tokens": u.get("cache_read_input_tokens", 0),
                         "cache_creation_input_tokens":
                             u.get("cache_creation_input_tokens", 0)}
                merged = list(blocks)
                g = span(trace_id, hid(16, "gen", trace_id, mid or gens), "generation %d" % gens,
                         prev, ts, [
                             ("langfuse.observation.type", "generation"),
                             ("langfuse.observation.model.name", msg.get("model")),
                             ("langfuse.observation.usage_details", json.dumps(usage)),
                             ("langfuse.observation.input", js(last_user.get(parent_tool, ""))),
                             ("langfuse.observation.output", js(merged)),
                             ("langfuse.observation.metadata.stop_reason", msg.get("stop_reason")),
                             ("langfuse.observation.metadata.message_id", mid),
                         ], parent=parent)
                spans.append(g)
                if mid:
                    gen_by_id[mid] = (g, merged)
            for b in blocks:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
                    tools += 1
                    t = span(trace_id, hid(16, "tool", trace_id, b["id"]), b.get("name") or "tool",
                             ts, ts, [
                                 ("langfuse.observation.type", "tool"),
                                 ("langfuse.observation.input", js(b.get("input"))),
                                 ("langfuse.observation.metadata.tool_use_id", b["id"]),
                             ], parent=parent)
                    t["_open"] = True
                    tool_spans[b["id"]] = t
                    spans.append(t)
                    last_user[b["id"]] = b.get("input")
        else:
            last_user[parent_tool] = content
            for b in content if isinstance(content, list) else []:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                t = tool_spans.get(b.get("tool_use_id"))
                if not t:
                    continue
                t["endTimeUnixNano"] = str(max(int(t["startTimeUnixNano"]), ts))
                t["attributes"].append(attr("langfuse.observation.output", js(b.get("content"))))
                if b.get("is_error"):
                    t["attributes"].append(attr("langfuse.observation.level", "ERROR"))
                    t["status"] = {"code": 2, "message": "tool_result is_error"}
                t.pop("_open", None)
        prev = ts
    for t in tool_spans.values():
        if t.pop("_open", False):
            t["endTimeUnixNano"] = str(t1)
            t["attributes"].append(attr("langfuse.observation.level", "WARNING"))
            t["attributes"].append(attr("langfuse.observation.status_message",
                                        "no tool_result in the transcript"))

    writes = 0
    for i, e in enumerate(journal):
        if not e.get("write"):
            continue
        writes += 1
        at = t1 + i   # journal order, one nanosecond apart — the journal has no clock
        spans.append(span(trace_id, hid(16, "journal", trace_id, i), "journal:%s" % e.get("route"),
                          at, at, [
                              ("langfuse.observation.type", "event"),
                              ("langfuse.observation.input", js(e.get("argv"))),
                              ("langfuse.observation.output", js(e.get("body"))),
                              ("langfuse.observation.metadata.route", e.get("route")),
                              ("langfuse.observation.metadata.seq", i),
                          ], parent=root_id))

    cost = result.get("cost") or {}
    usd = cost.get("usd") if isinstance(cost, dict) else None
    # plugin_sha is the checkout the run executed under: known only when the
    # runner exports in the same breath; a backfill from a later checkout
    # would mislabel the run (codex review, PR #93), so it carries none.
    meta = [("sut", sut), ("case", case), ("run", str(run)), ("model", model),
            ("plugin_sha", None if backfilled else plugin_sha()), ("backfilled", backfilled),
            ("session_id", session_id), ("verdict", verdict),
            ("invalid_reason", result.get("invalid_reason")),
            ("duration_ms", (res_ev or {}).get("duration_ms")),
            ("num_turns", (res_ev or {}).get("num_turns")),
            ("cost_usd", usd)]
    root = span(trace_id, root_id, name, t0, t1 + len(journal), [
        ("langfuse.observation.type", "span"),
        ("langfuse.trace.name", name),
        ("langfuse.session.id", "%s/%s" % (sut, case)),
        ("langfuse.trace.tags", [case, sut, verdict]),
        ("langfuse.trace.input", js(prompt or "")),
        ("langfuse.trace.output", js((res_ev or {}).get("result") or "")),
    ] + [("langfuse.trace.metadata.%s" % k, v) for k, v in meta])
    spans.insert(0, root)

    scores = []

    def score(sname, value, dtype, comment=""):
        scores.append({"id": hid(32, "score", trace_id, sname), "traceId": trace_id,
                       "name": sname, "value": value, "dataType": dtype,
                       "comment": comment or None})
    score("pass", 1 if result.get("pass") else 0, "BOOLEAN")
    score("valid", 1 if valid else 0, "BOOLEAN", result.get("invalid_reason") or "")
    if usd is not None:
        score("cost_usd", float(usd), "NUMERIC")
    for desc, ok, detail in claims:
        score(desc[:100], 1 if ok else 0, "BOOLEAN", detail)

    summary = {"trace_id": trace_id, "name": name, "session": "%s/%s" % (sut, case),
               "verdict": verdict, "spans": len(spans), "generations": gens, "tools": tools,
               "journal_writes": writes, "scores": len(scores)}
    return spans, scores, summary


def otlp_batches(spans):
    """OTLP/JSON ExportTraceServiceRequest bodies, each under BATCH_CAP."""
    batches, cur, size = [], [], 0
    for s in spans:
        n = len(json.dumps(s, ensure_ascii=False).encode("utf-8"))
        if cur and size + n > BATCH_CAP:
            batches.append(cur)
            cur, size = [], 0
        cur.append(s)
        size += n
    if cur:
        batches.append(cur)
    return [{"resourceSpans": [{"resource": {"attributes": [attr("service.name", SERVICE)]},
                                "scopeSpans": [{"scope": {"name": SCOPE}, "spans": b}]}]}
            for b in batches]


# ---- the wire -------------------------------------------------------------
def post(cfg, path, body):
    auth = base64.b64encode(("%s:%s" % (cfg["LANGFUSE_PUBLIC_KEY"],
                                        cfg["LANGFUSE_SECRET_KEY"])).encode()).decode()
    req = urllib.request.Request(cfg["LANGFUSE_HOST"] + path,
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Basic " + auth,
                                          "x-langfuse-ingestion-version": "4"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        raise ExportError("%s → HTTP %d: %s" % (path, e.code, detail))
    except (urllib.error.URLError, OSError) as e:
        raise ExportError("%s → %s" % (path, e))


def send(cfg, spans, scores):
    for body in otlp_batches(spans):
        post(cfg, "/api/public/otel/v1/traces", body)
    for sc in scores:
        post(cfg, "/api/public/scores", sc)


# ---- entry points ---------------------------------------------------------
def export_run(rdir, case, sut, run, prompt, cfg, dry_run=False, backfilled=False,
               force=False):
    spans, scores, summary = build(rdir, case, sut, run, prompt, backfilled=backfilled)
    if dry_run:
        print(json.dumps({"summary": summary, "payloads": otlp_batches(spans), "scores": scores},
                         ensure_ascii=False, indent=1))
        return summary
    prior = exported(rdir)
    if prior and not force:
        raise AlreadyExported("%s already exported (%s) — Langfuse v4 appends, it does not "
                              "replace; --force to send again" % (summary["name"],
                                                                   prior.get("url", "")))
    send(cfg, spans, scores)
    summary["url"] = "%s/project/%s/traces/%s" % (
        cfg["LANGFUSE_HOST"], os.environ.get("LANGFUSE_PROJECT_ID", "").strip() or "_",
        summary["trace_id"])
    summary["exported_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(os.path.join(rdir, MARKER), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    return summary


def maybe_export(rdir, case, sut, run, prompt):
    """The runner's hook: export when the env says so; never raise."""
    cfg = env_config()
    if not cfg:
        return False
    try:
        s = export_run(rdir, case, sut, run, prompt, cfg)
        print("export_langfuse: %s → trace %s" % (s["name"], s["trace_id"]))
        return True
    except ExportError as e:
        warn("%s/run-%s not exported — %s" % (case, run, e))
    except Exception as e:  # the verdict is already on disk; nothing here may change it
        warn("%s/run-%s not exported — %s: %s" % (case, run, type(e).__name__, e))
    return False


def run_meta(rdir):
    """(case, sut, run, prompt) from report/<sut>/<case>/run-<i> — or a
    smoke dir report/<sut>/smoke-S<n>."""
    parts = os.path.abspath(rdir).rstrip(os.sep).split(os.sep)
    m = re.match(r"^run-(\d+)$", parts[-1])
    if m:
        case, sut, run = parts[-2], parts[-3], m.group(1)
    else:
        case, sut, run = parts[-1], parts[-2], "1"
    cdir = (os.path.join(S, "smoke", case[len("smoke-"):]) if case.startswith("smoke-")
            else os.path.join(S, "cases", case))
    prompt = (load_json(os.path.join(cdir, "case.json"), {}) or {}).get("prompt", "")
    return case, sut, run, prompt


def main(argv):
    dry = "--dry-run" in argv
    force = "--force" in argv
    dirs = [a for a in argv if a not in ("--dry-run", "--force")]
    if not dirs:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    cfg = None if dry else env_config()
    if not dry and not cfg:
        warn("set %s to export (or use --dry-run)" % ", ".join(ENV))
        return 2
    failed = 0
    for rdir in dirs:
        case, sut, run, prompt = run_meta(rdir)
        try:
            s = export_run(rdir, case, sut, run, prompt, cfg, dry_run=dry, backfilled=True,
                           force=force)
            if not dry:
                print("%s → %s" % (s["name"], s["url"]))
        except AlreadyExported as e:
            warn(str(e))
        except ExportError as e:
            warn(str(e))
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
