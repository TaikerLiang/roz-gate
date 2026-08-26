#!/usr/bin/env python3
"""Replay-tier runner. Usage:

    run-replay.py [--sut NAME] [--k N] [case ...]    # default: fable, all

Measurement, not a gate: per-case observed rates with Wilson 90% intervals
into report/<sut>/report.json, no pass thresholds anywhere — the gate
decision comes after the baseline.

Multi-model: --sut resolves through models.yaml (mode, model, base_url,
key_env). Claude Code is the runtime for every row; only the model swaps,
whole-stack. Before any sweep spend, a 3-case smoke gate runs once per
SUT — a failing row is marked HARNESS-INCOMPATIBLE, never scored 0.

RESUMABLE: each iteration persists to report/<sut>/<case>/run-<i>/ and a
completed iteration is never re-run.

Blindness guard: a case whose check.py (or driver) carries no `# source:`
citation is refused. Smoke cases are exempt (plumbing proofs).

CI runs the lint tier only, never this. Replay is local, on-demand,
pre-release manual.
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(S))


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def resolve_sut(name):
    for line in open(os.path.join(S, "models.yaml"), encoding="utf-8"):
        m = re.match(r"^(\w+):\s*\{(.*)\}\s*$", line.strip())
        if not m or m.group(1) != name:
            continue
        kv = dict(p.split(":", 1) for p in m.group(2).split(","))
        kv = {k.strip(): v.strip().strip('"') for k, v in kv.items()}
        return {"name": name, "mode": kv.get("mode", "subscription"),
                "model": kv["model"], "base_url": kv.get("base_url", ""),
                "key_env": kv.get("key_env", "")}
    return None


def sh(args, cwd=None, env=None, timeout=None, out=None, err=None):
    return subprocess.run(args, cwd=cwd, env=env, timeout=timeout,
                          stdout=out, stderr=err)


def build_sandbox(cdir):
    """Sandbox repo + local bare remote. Contract: seed.sh leaves a repo
    with >=1 commit, ending on main; extra branches allowed; all refs
    pushed. Pushes are observable refs; nothing leaves the machine."""
    sbx = tempfile.mkdtemp()
    bare = os.path.join(sbx, "origin.git")
    work = os.path.join(sbx, "work")
    os.makedirs(work)
    steps = [
        (["git", "init", "-q", "--bare", bare], sbx),
        (["git", "init", "-q", "-b", "main"], work),
        (["bash", os.path.join(cdir, "seed.sh"), ROOT], work),
        (["git", "checkout", "-q", "main"], work),
        (["git", "remote", "add", "origin", bare], work),
        (["git", "push", "-q", "origin", "--all"], work),
    ]
    for args, cwd in steps:
        if sh(args, cwd=cwd).returncode != 0:
            shutil.rmtree(sbx, ignore_errors=True)
            return None, None, None
    return sbx, work, bare


def claude_env(sut, forge_state):
    env = dict(os.environ)
    env["PATH"] = os.path.join(S, "forge-stub") + os.pathsep + env["PATH"]
    env["FORGE_STATE"] = forge_state
    if sut["mode"] == "api":
        env["ANTHROPIC_BASE_URL"] = sut["base_url"]
        env["ANTHROPIC_API_KEY"] = os.environ.get(sut["key_env"], "")
    return env


def invoke_claude(sut, work, forge_state, prompt, timeout, transcript,
                  stderr_log, resume=None):
    args = ["claude", "-p", prompt]
    if resume:
        args += ["--resume", resume]
    args += ["--model", sut["model"], "--output-format", "stream-json",
             "--verbose", "--dangerously-skip-permissions",
             "--plugin-dir", ROOT]
    with open(transcript, "w") as t, open(stderr_log, "a") as e:
        try:
            sh(args, cwd=work, env=claude_env(sut, forge_state),
               timeout=timeout, out=t, err=e)
        except subprocess.TimeoutExpired:
            pass  # partial transcript -> no result event -> invalid


def usage_and_cost(transcript, mode):
    usage = {"in": 0, "out": 0}
    cost = None
    for line in open(transcript, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        u = (ev.get("message") or {}).get("usage") or {}
        usage["in"] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        usage["out"] += u.get("output_tokens", 0)
        if ev.get("type") == "result" and ev.get("total_cost_usd") is not None:
            cost = ev["total_cost_usd"]
    if mode == "api":
        return usage, {"usd": cost}
    return usage, {"quota_tokens": usage,
                   "note": "subscription quota, no dollar figure"}


def write_result(rdir, obj):
    with open(os.path.join(rdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def has_result_event(transcript):
    try:
        for line in open(transcript, encoding="utf-8"):
            if re.search(r'"type":\s*"result"', line):
                return True
    except OSError:
        pass
    return False


def hit_unknown_route(journal):
    try:
        for line in open(journal, encoding="utf-8"):
            if '"route": "UNKNOWN"' in line:
                return True
    except OSError:
        pass
    return False


def run_one(sut, cdir, rdir, prompt, timeout):
    """0 = pass, 2 = fail, 1 = invalid. Validity ≠ red: an empty session or
    an unrouted forge call is a harness/fixture failure, not the model's —
    an empty run must never vacuously pass a zero-writes case."""
    os.makedirs(os.path.join(rdir, "forge"), exist_ok=True)
    sbx, work, bare = build_sandbox(cdir)
    if not sbx:
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "seed failed"})
        return 1
    shutil.copy(os.path.join(cdir, "state.json"),
                os.path.join(rdir, "forge", "state.json"))
    journal = os.path.join(rdir, "forge", "journal.jsonl")
    open(journal, "w").close()
    transcript = os.path.join(rdir, "transcript.jsonl")

    invoke_claude(sut, work, os.path.join(rdir, "forge"), prompt, timeout,
                  transcript, os.path.join(rdir, "stderr.log"))

    if not has_result_event(transcript):
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "no result event — the session never completed"})
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    if hit_unknown_route(journal):
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "forge stub hit an UNKNOWN route"})
        shutil.rmtree(sbx, ignore_errors=True)
        return 1

    env = dict(os.environ)
    env.update({"RUN_DIR": rdir, "WORK": work, "BARE": bare, "ROOT": ROOT})
    with open(os.path.join(rdir, "check.log"), "w") as log:
        ok = sh(["python3", os.path.join(cdir, "check.py")],
                env=env, out=log, err=subprocess.STDOUT).returncode == 0
    usage, cost = usage_and_cost(transcript, sut["mode"])
    write_result(rdir, {"valid": True, "pass": ok, "tokens": usage,
                        "cost": cost})
    shutil.rmtree(sbx, ignore_errors=True)
    return 0 if ok else 2


def smoke_gate(sut, report):
    marker = os.path.join(report, "smoke-pass")
    incompat = os.path.join(report, "HARNESS_INCOMPATIBLE")
    if os.path.isfile(marker):
        return
    if os.path.isfile(incompat):
        die("SUT '%s' is marked harness-incompatible; remove %s to retry"
            % (sut["name"], incompat), 3)
    print("== smoke gate for SUT '%s' (%s, %s) =="
          % (sut["name"], sut["model"], sut["mode"]))
    failed = False
    for sc in ("S1", "S2", "S3"):
        scdir = os.path.join(S, "smoke", sc)
        srdir = os.path.join(report, "smoke-" + sc)
        prior = load_json(os.path.join(srdir, "result.json"))
        if prior and prior.get("pass"):
            print("smoke %s: already passed" % sc)
            continue
        prompt = load_json(os.path.join(scdir, "case.json"))["prompt"]
        rc = run_one(sut, scdir, srdir, prompt, 300)
        print("smoke %s: %s" % (sc, "PASS" if rc == 0 else "FAIL"))
        failed = failed or rc != 0
    if failed:
        os.makedirs(report, exist_ok=True)
        with open(incompat, "w") as f:
            f.write("smoke gate failed — see report/%s/smoke-*/\n" % sut["name"])
        die("SUT '%s': HARNESS-INCOMPATIBLE (plumbing, not compliance). "
            "Row is not scored." % sut["name"], 3)
    open(marker, "w").close()


def wilson90(p, n):
    if not n:
        return (0.0, 0.0)
    z = 1.6449
    rate = p / n
    c = (rate + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def aggregate(sut, report):
    rows = []
    for case in sorted(os.listdir(report)):
        d = os.path.join(report, case)
        if not os.path.isdir(d) or case.startswith("smoke-"):
            continue
        n = p = inv = tin = tout = 0
        usd = 0.0
        for run in sorted(os.listdir(d)):
            r = load_json(os.path.join(d, run, "result.json"))
            if r is None:
                continue
            if not r.get("valid"):
                inv += 1  # instrument runs included: an aborted session's
                continue  # partial curve is never published
            if r.get("instrument_only"):
                rows.append({"case": case, "run": run, "instrument": True,
                             "curve": r.get("curve", {}),
                             "tokens": r.get("tokens")})
                continue
            n += 1
            p += 1 if r.get("pass") else 0
            t = r.get("tokens", {})
            tin += t.get("in", 0)
            tout += t.get("out", 0)
            usd += (r.get("cost") or {}).get("usd") or 0
        if n == 0 and inv == 0:
            continue
        if n == 0:
            # All iterations invalid: a harness failure, never a scored 0%
            # — publishing it as a rate would break invalid-never-red.
            rows.append({"case": case, "runs": 0, "passes": 0, "invalid": inv,
                         "rate": None, "wilson90": None,
                         "note": "unavailable — every iteration invalid",
                         "tokens": {"in": tin, "out": tout}})
            continue
        lo, hi = wilson90(p, n)
        rows.append({"case": case, "runs": n, "passes": p, "invalid": inv,
                     "rate": round(p / n, 3),
                     "wilson90": [round(lo, 3), round(hi, 3)],
                     "tokens": {"in": tin, "out": tout},
                     **({"cost_usd": round(usd, 4)} if sut["mode"] == "api"
                        else {"cost": "quota"})})
    smoke = all((load_json(os.path.join(report, "smoke-S%d" % i, "result.json"))
                 or {}).get("pass") for i in (1, 2, 3))
    with open(os.path.join(report, "report.json"), "w", encoding="utf-8") as f:
        json.dump({"sut": sut["name"], "model": sut["model"],
                   "mode": sut["mode"],
                   "smoke_gate": "pass" if smoke else "incomplete",
                   "baseline_note":
                       "opus is the protocol's ceiling reference, not "
                       "necessarily the production loop's current operator; "
                       "the current operator appears as its own row.",
                   "cases": rows}, f, indent=1)
    print("\nSUT %s (%s, %s) — smoke gate: %s"
          % (sut["name"], sut["model"], sut["mode"],
             "pass" if smoke else "incomplete"))
    print("%-8s %6s %3s  %-15s %s" % ("case", "rate", "k", "wilson90",
                                      "tokens(in/out)"))
    for r in rows:
        if r.get("instrument"):
            print("%-8s instrument-only  curve: %s" % (r["case"], r["curve"]))
            continue
        if r["rate"] is None:
            print("%-8s n/a — every iteration invalid (%d invalid)"
                  % (r["case"], r["invalid"]))
            continue
        extra = "  (%d invalid)" % r["invalid"] if r["invalid"] else ""
        print("%-8s %5.0f%% %3d  [%.0f%%,%.0f%%]      %d/%d%s"
              % (r["case"], r["rate"] * 100, r["runs"],
                 r["wilson90"][0] * 100, r["wilson90"][1] * 100,
                 r["tokens"]["in"], r["tokens"]["out"], extra))


def main(argv):
    sut_name, k_override, cases = "fable", None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--sut":
            sut_name = argv[i + 1]
            i += 2
        elif argv[i] == "--k":
            k_override = int(argv[i + 1])
            i += 2
        else:
            cases.append(argv[i])
            i += 1
    if not cases:
        cases = sorted(os.listdir(os.path.join(S, "cases")))

    sut = resolve_sut(sut_name)
    if not sut:
        die("unknown SUT '%s' (see models.yaml)" % sut_name)
    if sut["mode"] == "api" and not os.environ.get(sut["key_env"], ""):
        die("SUT '%s' is api-mode but $%s is unset" % (sut_name, sut["key_env"]))

    report = os.path.join(S, "report", sut_name)
    os.makedirs(report, exist_ok=True)
    smoke_gate(sut, report)

    for case in cases:
        cdir = os.path.join(S, "cases", case)
        if not os.path.isdir(cdir):
            die("no such case: %s" % case)
        meta = load_json(os.path.join(cdir, "case.json"), {})
        driver = meta.get("driver", "")
        guard = os.path.join(cdir, driver or "check.py")
        if "# source:" not in open(guard, encoding="utf-8").read():
            die("REFUSED %s: %s has no '# source:' citation (blindness guard)"
                % (case, os.path.basename(guard)))
        k = k_override or meta.get("k", 5)
        for i in range(1, k + 1):
            rdir = os.path.join(report, case, "run-%d" % i)
            if os.path.isfile(os.path.join(rdir, "result.json")):
                print("skip %s run-%d (done)" % (case, i))
                continue
            print("run  %s run-%d ..." % (case, i))
            if driver:
                env = dict(os.environ)
                env.update({"ROOT": ROOT, "S": S, "SUT_NAME": sut["name"],
                            "SUT_MODEL": sut["model"], "SUT_MODE": sut["mode"],
                            "SUT_BASE_URL": sut["base_url"],
                            "SUT_KEY_ENV": sut["key_env"]})
                sh(["python3", os.path.join(cdir, driver), cdir, rdir, str(i)],
                   env=env)
                continue
            rc = run_one(sut, cdir, rdir, meta["prompt"],
                         meta.get("timeout", 900))
            print({0: "PASS", 2: "FAIL"}.get(rc, "INVALID"),
                  "%s run-%d" % (case, i))

    aggregate(sut, report)


if __name__ == "__main__":
    main(sys.argv[1:])
