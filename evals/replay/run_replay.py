#!/usr/bin/env python3
"""Replay-tier runner. Usage:

    run_replay.py [--sut NAME] [--k N] [--variant A|B|C] [case ...]    # default: fable, A, all
    run_replay.py --list [case ...]          # each case's default k, baseline status, tier
    run_replay.py --dry-run [--sut NAME] [--k N] [--variant V] [case ...]
                                             # what a run would do: k, done, pending, smoke
    run_replay.py --help

Every argument is checked for the whole batch — the SUT, the variant, each
case, its `# source:` citation, the driver/variant pairing — before the
report dir is created, a variant copied or the smoke gate run (#282).
`--list` and `--dry-run` are read-only: no model, no credentials, nothing
written.

Measurement, not a gate: per-case observed rates with Wilson 90% intervals
into report/<sut>/report.json, no pass thresholds anywhere — the gate
decision comes after the baseline.

Brief variants (#199): --variant names the QA brief the SUT runs under, a
dimension apart from --sut. `A` is references/qa-brief.md as checked out;
`B`, `C`, … are evals/replay/variants/qa-brief/<V>.md. For a variant other
than A the runner copies the plugin root to a temp dir (no .git, no evals/),
replaces ONLY references/qa-brief.md there and passes that dir as
--plugin-dir; the checkout is never touched. Every result.json carries
`variant` and `brief_sha256` — the hash of the brief file READ BACK from the
plugin dir the session ran — beside `plugin_sha` and `case_fp`; a run whose
brief hash differs from the variant file's current one is STALE exactly like
a fingerprint mismatch. `persona_sha256` (#267) is the QA persona
(agents/qa.md) read back the same way; for a case whose case.json declares
"seats": ["qa"] a run under another persona is STALE too. A variant's runs
live in report/<sut>/<case>@<V>/; A's stay in report/<sut>/<case>/ (one A,
never two copies).

Multi-model: --sut resolves through models.yaml (mode, model, base_url,
key_env). Claude Code is the runtime for every row; only the model swaps,
whole-stack. Before any sweep spend, a 3-case smoke gate runs once per
SUT — a failing row is marked HARNESS-INCOMPATIBLE, never scored 0.

RESUMABLE: each iteration persists to report/<sut>/<case>/run-<i>/ and a
completed iteration is never re-run. Each result.json carries `case_fp`
(replaylib.case_fingerprint: the checker, case.json, seed, state) and
`plugin_sha`; the report counts a run whose fingerprint differs from the
current case as STALE and leaves it out of the rate, a run without one as
UNKNOWN and keeps it in (#190). A stale iteration is still done — re-running
it is a quota decision, per case.

Blindness guard: a case whose check.py (or driver) carries no `# source:`
citation is refused. Smoke cases are exempt (plumbing proofs).

CI runs the lint tier only, never this. Replay is local, on-demand,
pre-release manual.
"""

import argparse
import atexit
import filecmp
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(S))  # evals/ — the shared kit
from lib.checkkit import has_citation  # noqa: E402

sys.path.insert(0, S)
import replaylib as rl  # noqa: E402
from export_langfuse import maybe_export  # noqa: E402
from replaylib import has_result_event, session_error  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(S))
REPORT = os.path.join(S, "report")
BASELINES = os.path.join(S, "baselines.json")
SMOKE = ("S1", "S2", "S3")

# ---- brief variants (#199) ---------------------------------------------------
BRIEF_REL = "references/qa-brief.md"
# the QA seat's system prompt (#267) — stamped like the brief; a run under
# another persona is stale for a case that declares "seats": ["qa"]
PERSONA_REL = "agents/qa.md"
VARIANTS = os.path.join(S, "variants", "qa-brief")
# What the temp plugin copy leaves out: nothing the runtime loads. The
# variant copy must differ from the checkout in exactly one file
# (redproof.py § VARIANT), so the list is of trees, never of files.
COPY_IGNORE_NAMES = (".git", ".venv", ".ruff_cache", ".claude", "evals", "docs", "images",
                     "node_modules", "__pycache__")
COPY_IGNORE = shutil.ignore_patterns(*COPY_IGNORE_NAMES)


def variant_file(variant):
    """The brief a variant stands for: the checkout's for A, else the frozen
    file under variants/qa-brief/. None when no such variant exists."""
    if variant == "A":
        return os.path.join(ROOT, BRIEF_REL)
    path = os.path.join(VARIANTS, "%s.md" % variant)
    return path if os.path.isfile(path) else None


def variant_plugin(variant):
    """The plugin dir a session runs: ROOT for A; for any other variant a
    temp copy of ROOT with ONLY references/qa-brief.md replaced, removed at
    exit. The checkout is never written."""
    if variant == "A":
        return ROOT
    src = variant_file(variant)
    if not src:
        die("unknown variant '%s' (no %s)" % (variant, os.path.join(VARIANTS, variant + ".md")))
    tmp = tempfile.mkdtemp(prefix="roz-gate-variant-%s-" % variant)
    atexit.register(shutil.rmtree, tmp, True)
    plugin = os.path.join(tmp, "plugin")
    shutil.copytree(ROOT, plugin, ignore=COPY_IGNORE, symlinks=True)
    shutil.copyfile(src, os.path.join(plugin, BRIEF_REL))
    return plugin


def variant_diff(plugin):
    """The files that differ between the checkout and a variant plugin copy
    (relative paths), trees in COPY_IGNORE left out of the comparison —
    the proof that injection touched one file (redproof.py § VARIANT)."""
    out = []

    def walk(cmp, prefix=""):
        out.extend(prefix + n for n in cmp.diff_files + cmp.left_only + cmp.right_only
                   + cmp.funny_files)
        for name, sub in cmp.subdirs.items():
            walk(sub, prefix + name + "/")

    walk(filecmp.dircmp(ROOT, plugin, ignore=list(COPY_IGNORE_NAMES)))
    return sorted(out)


def case_key(case, variant):
    """The report dir a (case, variant) scores into: A keeps the plain name."""
    return case if variant == "A" else "%s@%s" % (case, variant)


def split_key(key):
    case, _, variant = key.partition("@")
    return case, variant or "A"


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
        # HEAD → main: the remote's default branch is the sandbox's trunk,
        # never whatever init.defaultBranch is on the machine running it (#291)
        (["git", "init", "-q", "--bare", "-b", "main", bare], sbx),
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
    env.update(rl.SUT_ENV)
    if sut["mode"] == "api":
        env["ANTHROPIC_BASE_URL"] = sut["base_url"]
        env["ANTHROPIC_API_KEY"] = os.environ.get(sut["key_env"], "")
    return env


def invoke_claude(sut, work, forge_state, prompt, timeout, transcript,
                  stderr_log, resume=None, plugin_dir=ROOT):
    args = ["claude", "-p", prompt]
    if resume:
        args += ["--resume", resume]
    args += ["--model", sut["model"], "--output-format", "stream-json",
             "--verbose", "--dangerously-skip-permissions"] + rl.SUT_ISOLATION_ARGS
    if plugin_dir:      # None: no plugin at all — the Workflow Value baseline (#259)
        args += ["--plugin-dir", plugin_dir]
    with open(transcript, "w") as t, open(stderr_log, "a") as e:
        try:
            sh(args, cwd=work, env=claude_env(sut, forge_state),
               timeout=timeout, out=t, err=e)
        except subprocess.TimeoutExpired:
            # A killed session may still hold result events (one per
            # finished turn): say so in stderr, where cut_short() reads it.
            e.write("\n" + rl.TIMEOUT_NOTE % timeout + "\n")


def usage_and_cost(transcript, mode):
    """The session's tokens (replaylib.session_tokens, #308) and its cost."""
    usage = rl.session_tokens([transcript])
    cost = None
    for line in open(transcript, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result" and ev.get("total_cost_usd") is not None:
            cost = ev["total_cost_usd"]
    if mode == "api":
        return usage, {"usd": cost}
    return usage, {"quota_tokens": usage,
                   "note": "subscription quota, no dollar figure"}


def write_result(rdir, obj, stamp=None):
    """stamp: {case_fp, plugin_sha, variant, brief_sha256} — the case as
    scored and the brief it ran under, on every result the runner writes,
    invalid ones included (#190, #199)."""
    if stamp:
        obj = {**obj, **stamp}
    with open(os.path.join(rdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def case_stamp(cdir, variant="A", plugin_dir=ROOT):
    """The brief hash is read back from the plugin dir the session loads,
    never from the variant's source — the stamp says what ran."""
    return {"case_fp": rl.case_fingerprint(cdir), "plugin_sha": rl.plugin_sha(),
            "variant": variant,
            "brief_sha256": rl.brief_sha256(os.path.join(plugin_dir, BRIEF_REL)),
            "persona_sha256": rl.brief_sha256(os.path.join(plugin_dir, PERSONA_REL))}


def stamp_result(rdir, stamp):
    """A driver writes its own result.json; the runner stamps it after."""
    r = load_json(os.path.join(rdir, "result.json"))
    if isinstance(r, dict):
        write_result(rdir, r, stamp)


def hit_unknown_route(journal):
    try:
        for line in open(journal, encoding="utf-8"):
            if '"route": "UNKNOWN"' in line:
                return True
    except OSError:
        pass
    return False


def run_one(sut, cdir, rdir, prompt, timeout, variant="A", plugin_dir=ROOT):
    """0 = pass, 2 = fail, 1 = invalid, 3 = invalid AND quota-exhausted
    (the caller must stop the sweep: every further iteration burns
    nothing and writes junk). Validity ≠ red: an empty session or an
    unrouted forge call is a harness/fixture failure, not the model's —
    an empty run must never vacuously pass a zero-writes case."""
    rc = _run_one(sut, cdir, rdir, prompt, timeout, variant, plugin_dir)
    # The iteration is on disk; export it to Langfuse when the env says so
    # (#80). maybe_export never raises and nothing here reads its answer —
    # a failed export is a stderr line, never a changed verdict.
    maybe_export(rdir, case_key(os.path.basename(cdir), variant), sut["name"],
                 os.path.basename(rdir).replace("run-", ""), prompt)
    return rc


def score(cdir, rdir, work, bare):
    """Run the case's check.py on the iteration: ("pass" | "fail" |
    "invalid", reason). Exit 0 passes, replaylib.CHECK_INVALID (3) says the
    iteration never exercised the rule — its `INVALID <reason>` line is the
    reason (#199) — and anything else fails."""
    env = dict(os.environ)
    env.update({"RUN_DIR": rdir, "WORK": work, "BARE": bare, "ROOT": ROOT})
    log = os.path.join(rdir, "check.log")
    with open(log, "w") as out:
        rc = sh(["python3", os.path.join(cdir, "check.py")],
                env=env, out=out, err=subprocess.STDOUT).returncode
    if rc == 0:
        return "pass", None
    if rc == rl.CHECK_INVALID:
        return "invalid", rl.invalid_reason(log)
    return "fail", None


def _run_one(sut, cdir, rdir, prompt, timeout, variant, plugin_dir):
    os.makedirs(os.path.join(rdir, "forge"), exist_ok=True)
    stamp = case_stamp(cdir, variant, plugin_dir)
    sbx, work, bare = build_sandbox(cdir)
    if not sbx:
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "seed failed"}, stamp)
        return 1
    shutil.copy(os.path.join(cdir, "state.json"),
                os.path.join(rdir, "forge", "state.json"))
    journal = os.path.join(rdir, "forge", "journal.jsonl")
    open(journal, "w").close()
    # A retry reuses this directory (no result.json → re-run); stderr is
    # appended to, and cut_short() reads all of it — so a previous
    # attempt's termination line would invalidate this one (codex review,
    # PR #34). Each attempt starts with an empty stderr.log.
    open(os.path.join(rdir, "stderr.log"), "w").close()
    transcript = os.path.join(rdir, "transcript.jsonl")

    invoke_claude(sut, work, os.path.join(rdir, "forge"), prompt, timeout,
                  transcript, os.path.join(rdir, "stderr.log"), plugin_dir=plugin_dir)
    # What the session actually loaded (#307), on every result from here on.
    stamp = {**stamp, "plugins": rl.session_plugins(transcript)}

    if not has_result_event(transcript):
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "no result event — the session never completed"},
                     stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    err = session_error(transcript)
    if err:
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": err}, stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 3 if err == "quota-exhausted" else 1
    leak = rl.isolation_breach(transcript, plugin_dir)
    if leak:
        write_result(rdir, {"valid": False, "pass": False, "invalid_reason": leak}, stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    short = rl.cut_short(os.path.join(rdir, "stderr.log"))
    if short:
        write_result(rdir, {"valid": False, "pass": False, "invalid_reason": short}, stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    if hit_unknown_route(journal):
        write_result(rdir, {"valid": False, "pass": False,
                            "invalid_reason": "forge stub hit an UNKNOWN route"}, stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 1

    verdict, why = score(cdir, rdir, work, bare)
    usage, cost = usage_and_cost(transcript, sut["mode"])
    if verdict == "invalid":
        write_result(rdir, {"valid": False, "pass": False, "invalid_reason": why,
                            "tokens": usage, "cost": cost}, stamp)
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    ok = verdict == "pass"
    result = {"valid": True, "pass": ok, "tokens": usage, "cost": cost}
    # A checker may report signals — attempts the hook DENIED (D2), shell
    # writes to the acceptance suite (D4) — each in its own column, never a
    # breach. `signals` names the counts so the report sums them without
    # knowing; `details` names the evidence that rides along (#290).
    attempts = load_json(os.path.join(rdir, "attempts.json"), {}) or {}
    result.update(attempts)
    signals, details = split_attempts(attempts)
    if signals:
        result["signals"] = signals
    if details:
        result["details"] = details
    write_result(rdir, result, stamp)
    shutil.rmtree(sbx, ignore_errors=True)
    return 0 if ok else 2


def smoke_passed(report, sc):
    """A smoke case already passed for this SUT — skipped by the gate."""
    return bool((load_json(os.path.join(report, "smoke-" + sc, "result.json")) or {}).get("pass"))


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
    for sc in SMOKE:
        scdir = os.path.join(S, "smoke", sc)
        srdir = os.path.join(report, "smoke-" + sc)
        if smoke_passed(report, sc):
            print("smoke %s: already passed" % sc)
            continue
        prompt = load_json(os.path.join(scdir, "case.json"))["prompt"]
        rc = run_one(sut, scdir, srdir, prompt, 300)
        if rc == 3:  # quota, not plumbing — never mark incompatible
            die("quota exhausted at smoke-%s; resume after reset with the "
                "same command" % sc, 4)
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


def is_count(v):
    """A signal is a count: an int, and nothing else. Not a bool (a flag is
    not a count), not a float (a ratio or a latency would become a summable
    column by accident) — `Run.signal` is a count contract (#290)."""
    return type(v) is int


def split_attempts(attempts):
    """(signals, details): the keys of a run's attempts.json whose value is
    a count, and every other key. Both stay in result.json; only a signal
    is a report column."""
    signals = sorted(k for k, v in attempts.items() if is_count(v))
    return signals, sorted(k for k in attempts if k not in signals)


def aggregate(sut, report):
    rows = []
    for key in sorted(os.listdir(report)):
        d = os.path.join(report, key)
        if not os.path.isdir(d) or key.startswith("smoke-"):
            continue
        case, variant = split_key(key)
        n = p = inv = stale = unknown = tin = tout = tcr = old_counter = 0
        usd = 0.0
        signals = {}
        cdir = os.path.join(S, "cases", case)
        current = rl.case_fingerprint(cdir) if os.path.isdir(cdir) else None
        # The brief as scored (#199): the variant file's hash now; a run
        # stamped with another is a measurement of another brief.
        vfile = variant_file(variant)
        brief_now = rl.brief_sha256(vfile) if vfile else None
        # The QA persona as scored (#267): only for a case that dispatches
        # the seat — a persona edit is no measurement change for the rest.
        cjson = load_json(os.path.join(cdir, "case.json")) or {}
        persona_now = (rl.brief_sha256(os.path.join(ROOT, PERSONA_REL))
                       if "qa" in (cjson.get("seats") or []) else None)
        for run in sorted(os.listdir(d)):
            r = load_json(os.path.join(d, run, "result.json"))
            if r is None:
                continue
            # The case as scored (#190): a fingerprint that differs from the
            # case's current one is a measurement of another case — counted,
            # never scored; a result without one predates the stamp and
            # stays in, its case version unrecorded rather than known to
            # differ. The brief hash follows the same rule.
            if r.get("case_fp") is None:
                unknown += 1
            elif current is not None and r["case_fp"] != current:
                stale += 1
                continue
            if (r.get("brief_sha256") is not None and brief_now is not None
                    and r["brief_sha256"] != brief_now):
                stale += 1
                continue
            if (r.get("persona_sha256") is not None and persona_now is not None
                    and r["persona_sha256"] != persona_now):
                stale += 1
                continue
            if not r.get("valid"):
                inv += 1  # instrument runs included: an aborted session's
                continue  # partial curve is never published
            if r.get("instrument_only"):
                rows.append({"case": key, "run": run, "instrument": True,
                             "curve": r.get("curve", {}),
                             "tokens": r.get("tokens")})
                continue
            n += 1
            p += 1 if r.get("pass") else 0
            # results written before `signals` existed carry attempts_denied only
            for sig in r.get("signals") or (["attempts_denied"] if "attempts_denied" in r else []):
                # a result written before #290 lists its detail dicts here
                # too: evidence, never summed
                if is_count(r.get(sig)):
                    signals[sig] = signals.get(sig, 0) + r[sig]
            # tokens counted another way are never summed with these (#308)
            t = r.get("tokens", {})
            if rl.current_counter(t):
                tin += t.get("in", 0)
                tout += t.get("out", 0)
                tcr += t.get("cache_read", 0)
            else:
                old_counter += 1
            usd += (r.get("cost") or {}).get("usd") or 0
        if n == 0 and inv == 0 and stale == 0:
            continue
        counts = {"invalid": inv, **({"stale": stale} if stale else {}),
                  **({"unknown": unknown} if unknown else {}),
                  **({"tokens_old_counter": old_counter} if old_counter else {})}
        tokens = {"in": tin, "out": tout, "cache_read": tcr}
        if n == 0:
            # All iterations invalid or stale: a harness failure or another
            # case's measurement, never a scored 0% — publishing it as a
            # rate would break invalid-never-red.
            note = ("unavailable — every iteration invalid" if not stale else
                    "unavailable — every iteration is stale under the current case"
                    if not inv else "unavailable — every iteration invalid or stale")
            rows.append({"case": key, "variant": variant, "runs": 0, "passes": 0, **counts,
                         "rate": None, "wilson90": None, "note": note,
                         "tokens": tokens})
            continue
        lo, hi = wilson90(p, n)
        rows.append({"case": key, "variant": variant, "runs": n, "passes": p, **counts,
                     "rate": round(p / n, 3),
                     "wilson90": [round(lo, 3), round(hi, 3)],
                     "tokens": tokens,
                     **signals, **({"signals": sorted(signals)} if signals else {}),
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
            print("%-8s n/a — %s (%d invalid, %d stale)"
                  % (r["case"], r["note"], r["invalid"], r.get("stale", 0)))
            continue
        extra = "  (%d invalid)" % r["invalid"] if r["invalid"] else ""
        for key in ("stale", "unknown", "tokens_old_counter"):
            if r.get(key):
                extra += "  %s=%d" % (key, r[key])
        for key in r.get("signals", []):
            extra += "  %s=%d" % (key.replace("_", "-"), r[key])
        print("%-8s %5.0f%% %3d  [%.0f%%,%.0f%%]      %d/%d%s"
              % (r["case"], r["rate"] * 100, r["runs"],
                 r["wilson90"][0] * 100, r["wilson90"][1] * 100,
                 r["tokens"]["in"], r["tokens"]["out"], extra))


def positive_int(text):
    """argparse type for --k: an integer >= 1, else a usage error."""
    try:
        n = int(text)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError("must be a positive integer, got %r" % text)
    return n


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="run_replay.py", allow_abbrev=False,
        description="Replay-tier runner: per-case observed rates, no pass thresholds. "
                    "Every argument is checked before any model session starts.")
    p.add_argument("--sut", default="fable", help="a row of models.yaml (default: fable)")
    p.add_argument("--k", type=positive_int, help="iterations per case (default: the case's k)")
    p.add_argument("--variant", default="A",
                   help="the QA brief: A (the checkout's) or a file under variants/qa-brief/")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true",
                      help="list the cases: default k, baseline status, tier — no model")
    mode.add_argument("--dry-run", action="store_true",
                      help="print each case's k, done and pending iterations and the smoke "
                           "sessions a run would start — no model, nothing written")
    p.add_argument("cases", nargs="*", metavar="case", help="case ids (default: every case)")
    return p.parse_args(argv)


def selected(args):
    """(sut, [(case, cdir, meta)]): every check a run makes before spend,
    over the whole batch, before anything is written or started (#282)."""
    sut = resolve_sut(args.sut)
    if not sut:
        die("unknown SUT '%s' (see models.yaml)" % args.sut)
    if not variant_file(args.variant):
        die("unknown variant '%s' (A, or a file under %s)" % (args.variant, VARIANTS))
    chosen = []
    for case in args.cases or sorted(os.listdir(os.path.join(S, "cases"))):
        cdir = os.path.join(S, "cases", case)
        if not os.path.isdir(cdir):
            die("no such case: %s" % case)
        meta = load_json(os.path.join(cdir, "case.json"), {})
        driver = meta.get("driver", "")
        guard = os.path.join(cdir, driver or "check.py")
        if not has_citation(guard):
            die("REFUSED %s: %s has no '# source:' citation (blindness guard)"
                % (case, os.path.basename(guard)))
        if driver and args.variant != "A":
            die("REFUSED %s: a driver case runs the checkout's plugin; --variant is for "
                "check.py cases" % case)
        chosen.append((case, cdir, meta))
    return sut, chosen


def baseline_status(case, batches):
    """The case's entries in baselines.json: `current`, `superseded` or
    `none`, with the batch ids. Current is a result neither it nor its
    batch marks superseded — tools/ledger.py's rule (#293)."""
    cur, old = [], []
    for b in batches:
        for r in b.get("results", []):
            if r.get("case") == case:
                (old if b.get("superseded") or r.get("superseded") else cur).append(b["id"])
    if cur:
        return "current: " + ", ".join(cur)
    return "superseded: " + ", ".join(old) if old else "none"


def list_cases(chosen):
    batches = (load_json(BASELINES) or {}).get("replay", [])
    print("%-5s %3s  %-48s  %s" % ("case", "k", "baseline", "tier"))
    for case, _, meta in chosen:
        print("%-5s %3d  %-48s  %s" % (case, meta.get("k", 5), baseline_status(case, batches),
                                       meta.get("tier", "")))


def dry_run(sut, chosen, k_override, variant):
    report = os.path.join(REPORT, sut["name"])
    print("dry run — SUT %s (%s, %s), variant %s: no model, nothing written"
          % (sut["name"], sut["model"], sut["mode"], variant))
    smoke = 0
    if os.path.isfile(os.path.join(report, "smoke-pass")):
        print("smoke gate: passed — 0 sessions")
    elif os.path.isfile(os.path.join(report, "HARNESS_INCOMPATIBLE")):
        print("smoke gate: SUT marked harness-incompatible — the run refuses (remove %s)"
              % os.path.join(report, "HARNESS_INCOMPATIBLE"))
    else:
        todo = [sc for sc in SMOKE if not smoke_passed(report, sc)]
        smoke = len(todo)
        print("smoke gate: %d session(s)%s" % (smoke, " — " + ", ".join(todo) if todo else ""))
    print("%-8s %3s %5s %8s" % ("case", "k", "done", "pending"))
    pending = 0
    for case, _, meta in chosen:
        key = case_key(case, variant)
        k = k_override or meta.get("k", 5)
        done = sum(1 for i in range(1, k + 1)
                   if rl.iteration_done(os.path.join(report, key, "run-%d" % i)))
        pending += k - done
        print("%-8s %3d %5d %8d%s" % (key, k, done, k - done,
                                      "  (driver: its own sessions per iteration)"
                                      if meta.get("driver") else ""))
    print("total: %d pending iteration(s) over %d case(s), plus %d smoke session(s)"
          % (pending, len(chosen), smoke))


def main(argv):
    args = parse_args(argv)
    sut, chosen = selected(args)
    if args.list:
        list_cases(chosen)
        return
    if args.dry_run:
        dry_run(sut, chosen, args.k, args.variant)
        return
    if sut["mode"] == "api" and not os.environ.get(sut["key_env"], ""):
        die("SUT '%s' is api-mode but $%s is unset" % (sut["name"], sut["key_env"]))

    variant = args.variant
    report = os.path.join(REPORT, sut["name"])
    os.makedirs(report, exist_ok=True)
    smoke_gate(sut, report)   # plumbing, under the checkout: the brief is not involved
    plugin_dir = variant_plugin(variant)
    if variant != "A":
        print("variant %s: plugin copy at %s, brief sha256 %s" %
              (variant, plugin_dir, rl.brief_sha256(os.path.join(plugin_dir, BRIEF_REL))))

    for case, cdir, meta in chosen:
        driver = meta.get("driver", "")
        k = args.k or meta.get("k", 5)
        for i in range(1, k + 1):
            rdir = os.path.join(report, case_key(case, variant), "run-%d" % i)
            if rl.iteration_done(rdir):
                print("skip %s run-%d (done)" % (case_key(case, variant), i))
                continue
            print("run  %s run-%d ..." % (case_key(case, variant), i))
            if driver:
                env = dict(os.environ)
                env.update({"ROOT": ROOT, "S": S, "SUT_NAME": sut["name"],
                            "SUT_MODEL": sut["model"], "SUT_MODE": sut["mode"],
                            "SUT_BASE_URL": sut["base_url"],
                            "SUT_KEY_ENV": sut["key_env"]})
                rc = sh(["python3", os.path.join(cdir, driver), cdir, rdir,
                         str(i)], env=env).returncode
                stamp_result(rdir, case_stamp(cdir))
                if rc == 3:  # the driver's quota signal — same stop as below
                    die("quota exhausted at %s/run-%d; resume after reset "
                        "with the same command" % (case, i), 4)
                continue
            rc = run_one(sut, cdir, rdir, meta["prompt"],
                         meta.get("timeout", 900), variant, plugin_dir)
            print({0: "PASS", 2: "FAIL"}.get(rc, "INVALID"),
                  "%s run-%d" % (case_key(case, variant), i))
            if rc == 3:
                die("quota exhausted at %s/run-%d; resume after reset "
                    "with the same command" % (case, i), 4)

    aggregate(sut, report)


if __name__ == "__main__":
    main(sys.argv[1:])
