#!/usr/bin/env python3
"""Judgment-tier runner. Usage:

    run-judgment.py --check                       # fixtures frozen? (no tokens)
    run-judgment.py --redproof [--rejudge]        # judge red-proof (28 judge calls, verdicts cached) — BEFORE any SUT spend
    run-judgment.py [--sut NAME] [--k N] [case ...]   # SUT iterations + judging; default fable, k=1

What this tier measures: not "did the agent follow a rule" but "did the
agent surface the thing that changed the human's mind". Each fixture is a
real ADMC issue at the moment before the loop ran on it (repo at the pin
SHA, forge frozen at T); the SUT runs the current plugin on it; an opus
JUDGE grades the human-facing output against one checkable proposition
per corpus item and must QUOTE the output as evidence — the runner
verifies the quote mechanically (a judge that cannot quote hallucinated).

Two numbers, never blended: recall (P items surfaced / P items) and
precision (N items NOT raised as questions, AND question count within the
fixture's cap). The historical run's own score prints as the reference
row in every report — it is the line the current loop is read against.

The SUT (`--sut`, models.yaml) and the judge (fixed: opus, no tools, empty
cwd) are separate; on the opus row the judge is the SUT's model —
self-grading bias possible, unmeasured (README cannot-see #9).

Reuses the replay tier by import: forge stub, replaylib, invoke /
validity / quota / resumability. Never network: the sandbox is a clone of
the machine-local ADMC checkout named in sources.yaml.
"""

import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
E = os.path.dirname(S)                       # evals/
RS = os.path.join(E, "replay")
sys.path.insert(0, RS)
sys.path.insert(0, E)
from replaylib import Run, has_result_event, session_error  # noqa: E402
_spec = importlib.util.spec_from_file_location("run_replay", os.path.join(RS, "run-replay.py"))
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)
sys.path.insert(0, S)
from materialize import check_frozen  # noqa: E402

ROOT = rr.ROOT
JUDGE_MODEL = "claude-opus-5"
MIN_QUOTE = 40
# A question is a TITLE LINE — `**[role] · Q<k> · label**` (spec threads
# and spec.md items) or `**Q<k> · label**` (intake batches) — counted by
# DISTINCT id: the spec-cr surface carries each item twice (the thread
# body and spec.md's Open Questions, verbatim by A6), and a `**Q6**.`
# cross-reference inside a body is not a question (both caught by the
# judge red-proof's count check on the real F-63 output: 18 for 8).
QUESTION_RE = re.compile(r"^\*\*(?:\[[^\]]+\] · )?Q(\d+) · ", re.M)
SUMMARY_MARKER = "**[intake] · summary**"
SECTION_START = "## Development Workflow (Roz Gate)"
CONFIG_SOURCE = "d2ded1269c1c"   # the last commit whose CLAUDE.md carries the section in git
CRITERIA = json.load(open(os.path.join(S, "criteria.json"), encoding="utf-8"))
JUDGE_PROMPT = open(os.path.join(S, "judge-prompt.md"), encoding="utf-8").read()
# Bump when quote_ok / norm / the re-ask policy change: the policy is code,
# and the fingerprint below must move with it.
QUOTE_POLICY = "v1: whitespace-normalized substring, >=MIN_QUOTE chars, one re-ask then judge-invalid"


def judge_fingerprint():
    """Everything the red-proof's verdicts depend on, hashed: prompt,
    model, quote policy, criteria, expectations, paraphrases, the
    unrelated and historical documents. A cached verdict is reused only
    under the same fingerprint, and the sweep refuses to start unless the
    stored red-proof carries the current one — a judge configuration that
    changed after its last red-proof is an unmeasured judge (codex review,
    PR #10: the stale green this tier exists to prevent)."""
    h = hashlib.sha256()
    for part in (JUDGE_PROMPT, JUDGE_MODEL, str(MIN_QUOTE), QUOTE_POLICY):
        h.update(part.encode("utf-8") + b"\0")
    files = [os.path.join(S, "criteria.json"), os.path.join(S, "redproof", "expected.json"),
             os.path.join(S, "redproof", "paraphrase.json"), os.path.join(S, "redproof", "unrelated.md")]
    files += sorted(glob.glob(os.path.join(S, "redproof", "historical", "*.md")))
    for f in files:
        h.update(os.path.relpath(f, S).encode("utf-8") + b"\0")
        with open(f, "rb") as fh:
            h.update(fh.read() + b"\0")
    return h.hexdigest()[:16]


JUDGE_FP = judge_fingerprint()


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def admc_path():
    for line in open(os.path.join(S, "sources.yaml"), encoding="utf-8"):
        m = re.match(r"^admc:\s*(.+?)\s*$", line)
        if m:
            return os.path.expanduser(m.group(1))
    die("sources.yaml: no admc path")


def git(cwd, *args, check=True):
    out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        die("git %s failed in %s: %s" % (" ".join(args), cwd, out.stderr.strip()))
    return out.stdout


# ---- judge ----------------------------------------------------------------
def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def quote_ok(quote, document):
    q = norm(quote)
    return len(q) >= MIN_QUOTE and q in norm(document)


def ask_judge(criterion, document, note=""):
    prompt = JUDGE_PROMPT.replace("{criterion}", criterion).replace("{document}", document)
    if note:
        prompt += "\n\n" + note
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(
            ["claude", "-p", prompt, "--model", JUDGE_MODEL, "--tools", "",
             "--output-format", "json"],
            cwd=d, capture_output=True, text=True, timeout=600)
    try:
        res = json.loads(out.stdout)
    except ValueError:
        return {"answer": "judge-error", "quote": "", "raw": out.stdout[-400:] + out.stderr[-400:], "tokens": {}}
    text = res.get("result") or ""
    usage = res.get("usage") or {}
    tokens = {"in": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
              + usage.get("cache_read_input_tokens", 0),
              "out": usage.get("output_tokens", 0)}
    m = re.search(r"\{.*\}", text, re.S)
    try:
        obj = json.loads(m.group(0)) if m else {}
    except ValueError:
        obj = {}
    answer = str(obj.get("answer", "")).strip().lower()
    if answer not in ("yes", "no"):
        answer = "judge-error"
    return {"answer": answer, "quote": obj.get("quote") or "", "raw": text[-400:],
            "tokens": tokens, "is_error": bool(res.get("is_error"))}


def verdict(cid, document):
    """yes (quote verified) / no / judge-invalid. A yes whose quote is not
    a verbatim excerpt is re-asked once with the failure stated; a second
    failure is judge-invalid — never yes, never no."""
    crit = CRITERIA[cid]["criterion"]
    v = ask_judge(crit, document)
    calls = [v]
    if v["answer"] == "yes" and not quote_ok(v["quote"], document) or v["answer"] == "judge-error":
        v = ask_judge(crit, document,
                      "Your previous answer's quote was not a verbatim excerpt of the "
                      "document (or the answer was not valid JSON). Answer again. If you "
                      "cannot copy an excerpt of at least %d characters exactly as it "
                      "appears, the answer is no." % MIN_QUOTE)
        calls.append(v)
    valid = v["answer"] == "no" or (v["answer"] == "yes" and quote_ok(v["quote"], document))
    return {"answer": v["answer"] if valid else "judge-invalid", "quote": v["quote"],
            "valid": valid, "calls": len(calls),
            "tokens": {"in": sum(c["tokens"].get("in", 0) for c in calls),
                       "out": sum(c["tokens"].get("out", 0) for c in calls)}}


def question_count(document):
    return len(set(QUESTION_RE.findall(document)))


# ---- red-proof --------------------------------------------------------------
def redproof(report, rejudge=False):
    """Judge verdicts already recorded in report/judge-redproof.json are
    reused (a judge call is ~11k tokens; the mechanical checks are free)
    unless --rejudge — and only under the SAME judge fingerprint: a
    changed prompt, model, quote policy, criterion, expectation or
    document misses the cache and re-judges."""
    exp = json.load(open(os.path.join(S, "redproof", "expected.json"), encoding="utf-8"))
    para = json.load(open(os.path.join(S, "redproof", "paraphrase.json"), encoding="utf-8"))
    rows, mism, tok = [], 0, {"in": 0, "out": 0}
    stored = rr.load_json(os.path.join(report, "judge-redproof.json")) or {}
    prior = {} if rejudge or stored.get("fingerprint") != JUDGE_FP else {
        (r["doc"], r["criterion"], r.get("key")): r
        for r in stored.get("rows", []) if r.get("got") in ("yes", "no") and r.get("key")}
    if stored and not prior and not rejudge:
        print("judge configuration changed since the last red-proof (fingerprint %s → %s): re-judging"
              % (stored.get("fingerprint"), JUDGE_FP))

    def key(cid, text):
        return hashlib.sha256((JUDGE_FP + "\0" + CRITERIA[cid]["criterion"] + "\0" + text).encode("utf-8")).hexdigest()[:16]

    def judged(doc, cid, text):
        k = key(cid, text)
        hit = prior.get((doc, cid, k))
        if hit:
            return {"answer": hit["got"], "quote": hit.get("quote", ""), "tokens": {"in": 0, "out": 0}, "cached": True}, k
        return verdict(cid, text), k

    def record(doc, cid, want, got, quote="", k=None, cached=False):
        nonlocal mism
        ok = str(got) == str(want)
        mism += 0 if ok else 1
        rows.append({"doc": doc, "criterion": cid, "want": want, "got": got, "ok": ok, "quote": quote, "key": k})
        print("%s %-22s %-5s want %-4s got %-13s %s%s" % ("ok " if ok else "XX ", doc, cid, want, got,
                                                        ("— " + norm(quote)[:70]) if quote else "",
                                                        "  (cached)" if cached else ""))

    for doc, expect in exp["documents"].items():
        text = open(os.path.join(S, "redproof", doc), encoding="utf-8").read()
        for cid, want in expect.items():
            if cid == "question_count":
                record(doc, cid, want, question_count(text))
                continue
            v, k = judged(doc, cid, text)
            tok["in"] += v["tokens"]["in"]; tok["out"] += v["tokens"]["out"]
            record(doc, cid, want, v["answer"], v["quote"], k, v.get("cached", False))
    for cid, sets in para.items():
        if cid.startswith("_"):
            continue
        for kind in ("yes", "no"):
            for i, d in enumerate(sets[kind]):
                doc = "paraphrase/%s-%s%d" % (cid, kind, i + 1)
                v, k = judged(doc, cid, d)
                tok["in"] += v["tokens"]["in"]; tok["out"] += v["tokens"]["out"]
                record(doc, cid, kind, v["answer"], v["quote"], k, v.get("cached", False))
    os.makedirs(report, exist_ok=True)
    with open(os.path.join(report, "judge-redproof.json"), "w", encoding="utf-8") as f:
        json.dump({"judge": JUDGE_MODEL, "fingerprint": JUDGE_FP, "rows": rows, "mismatches": mism, "tokens": tok},
                  f, indent=1, ensure_ascii=False)
    print("\njudge red-proof: %d checks, %d mismatches, judge tokens %d in / %d out (fingerprint %s)"
          % (len(rows), mism, tok["in"], tok["out"], JUDGE_FP))
    return mism == 0


# ---- sandbox ----------------------------------------------------------------
def overlay(work, fx, admc):
    """The Roz Gate config block, restored from the last commit that
    carried it in git (ADMC's PR #62 moved it to an untracked
    CLAUDE.local.md; the hooks and commands read CLAUDE.md), restamped
    with the current template stamp as seed-common does, identity lines
    added for the fixtures whose dates were already in bot mode."""
    src = git(admc, "show", "%s:CLAUDE.md" % CONFIG_SOURCE)
    i = src.index(SECTION_START)
    section = src[i:]
    stamp = re.search(r"<!-- roz-gate workflow-template v\d+ -->",
                      open(os.path.join(ROOT, "templates", "CLAUDE-workflow.md"), encoding="utf-8").read()).group(0)
    section = re.sub(r"<!-- roz-gate workflow-template v\d+ -->", stamp, section)
    if fx.get("identity") == "bot":
        section = section.replace("- forge: github\n",
                                  "- forge: github\n- agent_identity: bot\n- bot_login: roz-gatekeeper\n", 1)
    path = os.path.join(work, "CLAUDE.md")
    cur = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    if SECTION_START in cur:
        cur = cur[:cur.index(SECTION_START)] + section
    else:
        cur = cur.rstrip("\n") + "\n\n" + section
    with open(path, "w", encoding="utf-8") as f:
        f.write(cur)


def build_sandbox(fx):
    """ADMC at the pin: clone the local checkout (never network), main
    reset to the pin, every other ref and the reflog dropped so nothing
    after T is reachable by name, the config overlay committed on top,
    then a local bare remote as replay does. Returns (sbx, work, bare,
    overlay_sha)."""
    admc = admc_path()
    if subprocess.run(["git", "-C", admc, "rev-parse", "--verify", "-q", fx["pin"] + "^{commit}"],
                      capture_output=True).returncode != 0:
        die("pin %s not in %s" % (fx["pin"], admc))
    sbx = tempfile.mkdtemp()
    work, bare = os.path.join(sbx, "work"), os.path.join(sbx, "origin.git")
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", admc, work], check=True)
    git(work, "checkout", "-q", "-B", "main", fx["pin"])
    for ref in git(work, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes", "refs/tags").split():
        if ref != "refs/heads/main":
            git(work, "update-ref", "-d", ref)
    git(work, "remote", "remove", "origin")
    git(work, "reflog", "expire", "--expire=now", "--all")
    git(work, "gc", "--prune=now", "--quiet")   # post-T objects are gone, not merely unnamed
    overlay(work, fx, admc)
    git(work, "add", "-A")
    # --allow-empty: at a pin whose CLAUDE.md already carries the section
    # the overlay is a no-op, and the overlay SHA must still exist.
    git(work, "-c", "user.email=fixture@roz-gate", "-c", "user.name=fixture", "commit", "-q",
        "--allow-empty", "-m", "fixture: roz-gate config overlay (judgment tier, pin %s)" % fx["pin"])
    sha = git(work, "rev-parse", "HEAD").strip()
    subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
    git(work, "remote", "add", "origin", bare)
    git(work, "push", "-q", "origin", "--all")
    return sbx, work, bare, sha


# ---- one iteration ------------------------------------------------------------
def judged_surface(fx, rdir, bare):
    """The human-facing output: spec-cr → every write on the spec CR plus
    spec.md's Open Questions at the pushed spec/<n> head; issue → every
    comment written on the fixture's issue."""
    os.environ["BARE"] = bare
    r = Run(rdir)
    n = str(fx["issue"])
    parts = []
    for e in r.journal():
        if not e.get("write"):
            continue
        if fx["surface"] == "spec-cr" and e.get("route") in ("thread-post-inline", "pr-comment"):
            parts.append("--- [%s] ---\n%s" % (e["route"], (e.get("body") or "").strip()))
        elif fx["surface"] == "issue" and e.get("route") == "issue-comment" and str(e.get("issue")) == n:
            parts.append("--- [issue-comment] ---\n%s" % (e.get("body") or "").strip())
    if fx["surface"] == "spec-cr":
        spec = r.remote_file("spec/%s" % n, "specs/%s/spec.md" % n) or ""
        m = re.search(r"^## Open Questions\s*$(.*?)(?=^## |\Z)", spec, re.M | re.S)
        if m:
            parts.append("--- [spec.md: Open Questions] ---\n" + m.group(1).strip())
    return "\n\n".join(parts) + ("\n" if parts else "")


def unknown_routes(rdir):
    out = []
    for e in Run(rdir).journal():
        if e.get("route") == "UNKNOWN":
            out.append({"argv": e.get("argv"), "note": e.get("note")})
    return out


def run_case(sut, name, fx, rdir):
    """0 pass-through (valid), 1 invalid, 3 invalid + quota (stop)."""
    os.makedirs(os.path.join(rdir, "forge"), exist_ok=True)
    shutil.copy(os.path.join(S, "cases", name, "state.json"), os.path.join(rdir, "forge", "state.json"))
    open(os.path.join(rdir, "forge", "journal.jsonl"), "w").close()
    sbx, work, bare, overlay_sha = build_sandbox(fx)
    transcript = os.path.join(rdir, "transcript.jsonl")
    rr.invoke_claude(sut, work, os.path.join(rdir, "forge"), fx["command"], fx["timeout"],
                     transcript, os.path.join(rdir, "stderr.log"))
    base = {"fixture": name, "pin": fx["pin"], "overlay_sha": overlay_sha, "sut": sut["name"]}
    if not has_result_event(transcript):
        rr.write_result(rdir, {**base, "valid": False, "invalid_reason": "no result event — the session never completed"})
        shutil.rmtree(sbx, ignore_errors=True)
        return 1
    err = session_error(transcript)
    usage, cost = rr.usage_and_cost(transcript, sut["mode"])
    if err:
        rr.write_result(rdir, {**base, "valid": False, "invalid_reason": err, "tokens": usage})
        shutil.rmtree(sbx, ignore_errors=True)
        return 3 if err == "quota-exhausted" else 1
    surface = judged_surface(fx, rdir, bare)
    with open(os.path.join(rdir, "surface.md"), "w", encoding="utf-8") as f:
        f.write(surface)
    unknowns = unknown_routes(rdir)
    count = question_count(surface)
    shutil.rmtree(sbx, ignore_errors=True)
    if unknowns:
        rr.write_result(rdir, {**base, "valid": False, "invalid_reason": "forge stub hit %d UNKNOWN route(s)" % len(unknowns),
                               "unknown_routes": unknowns, "question_count": count, "tokens": usage, "cost": cost})
        return 1
    verdicts = {cid: verdict(cid, surface) for cid in fx["criteria"]}
    p_ids = [c for c in fx["criteria"] if CRITERIA[c]["polarity"] == "P"]
    n_ids = [c for c in fx["criteria"] if CRITERIA[c]["polarity"] == "N"]
    recall = [sum(1 for c in p_ids if verdicts[c]["answer"] == "yes"), len(p_ids)]
    n_ok = 0
    for c in n_ids:
        if c == "N10":  # both halves: mechanical silence + judged assumptions
            summary_posted = any(e.get("write") and e.get("route") == "issue-comment"
                                 and (e.get("body") or "").startswith(SUMMARY_MARKER) for e in Run(rdir).journal())
            n_ok += 1 if (count == 0 and summary_posted and verdicts[c]["answer"] == "yes") else 0
        else:
            n_ok += 1 if verdicts[c]["answer"] == "no" else 0
    cap_ok = count <= fx["question_cap"]
    judge_tokens = {"in": sum(v["tokens"]["in"] for v in verdicts.values()),
                    "out": sum(v["tokens"]["out"] for v in verdicts.values())}
    rr.write_result(rdir, {**base, "valid": True, "question_count": count, "question_cap": fx["question_cap"],
                           "cap_ok": cap_ok, "recall": recall, "precision": [n_ok, len(n_ids)],
                           "judge_invalid": sum(1 for v in verdicts.values() if not v["valid"]),
                           "verdicts": verdicts, "tokens": usage, "cost": cost, "judge_tokens": judge_tokens})
    return 0


# ---- report ---------------------------------------------------------------------
def aggregate(sut, report):
    print("\nSUT %s (%s) — judge %s" % (sut["name"], sut["model"], JUDGE_MODEL))
    print("%-6s %-10s %-9s %-9s %-8s %-14s %s" % ("case", "row", "recall", "precision", "cap", "questions", "tokens(in/out) [judge]"))
    rows = []
    for name in sorted(os.listdir(os.path.join(S, "cases"))):
        fx = json.load(open(os.path.join(S, "cases", name, "fixture.json"), encoding="utf-8"))
        h = fx["historical"]
        print("%-6s %-10s %-9s %-9s %-8s %-14s %s" % (name, "historical", h["recall"], h["precision"],
                                                      "fail" if h["count"] > fx["question_cap"] else "ok",
                                                      "%d (cap %d)" % (h["count"], fx["question_cap"]), "—  " + h["note"]))
        d = os.path.join(report, name)
        runs = []
        if os.path.isdir(d):
            for run in sorted(os.listdir(d)):
                r = rr.load_json(os.path.join(d, run, "result.json"))
                if r:
                    runs.append((run, r))
        inv = [(run, r) for run, r in runs if not r.get("valid")]
        val = [(run, r) for run, r in runs if r.get("valid")]
        for run, r in val:
            print("%-6s %-10s %-9s %-9s %-8s %-14s %d/%d [%d/%d]%s" % (
                name, run, "%d/%d" % tuple(r["recall"]), "%d/%d" % tuple(r["precision"]),
                "ok" if r["cap_ok"] else "fail", "%d (cap %d)" % (r["question_count"], r["question_cap"]),
                r["tokens"]["in"], r["tokens"]["out"], r["judge_tokens"]["in"], r["judge_tokens"]["out"],
                "  judge-invalid=%d" % r["judge_invalid"] if r["judge_invalid"] else ""))
        for run, r in inv:
            print("%-6s %-10s INVALID — %s%s" % (name, run, r.get("invalid_reason"),
                                                 "  tokens %s" % r.get("tokens") if r.get("tokens") else ""))
            for u in r.get("unknown_routes", []):
                print("         UNKNOWN: gh %s  (%s)" % (" ".join(u.get("argv") or []), u.get("note")))
        if val:
            rows.append({"case": name, "runs": len(val), "invalid": len(inv),
                         "recall_rate": round(sum(r["recall"][0] for _, r in val) / max(1, sum(r["recall"][1] for _, r in val)), 3)
                         if sum(r["recall"][1] for _, r in val) else None,
                         "precision_rate": round(sum(r["precision"][0] for _, r in val) / max(1, sum(r["precision"][1] for _, r in val)), 3)
                         if sum(r["precision"][1] for _, r in val) else None,
                         "cap_pass": sum(1 for _, r in val if r["cap_ok"]),
                         "question_counts": [r["question_count"] for _, r in val],
                         "judge_invalid": sum(r["judge_invalid"] for _, r in val),
                         "tokens": {"in": sum(r["tokens"]["in"] for _, r in val), "out": sum(r["tokens"]["out"] for _, r in val)},
                         "historical": h})
        elif inv:
            rows.append({"case": name, "runs": 0, "invalid": len(inv), "note": "every iteration invalid", "historical": h})
    with open(os.path.join(report, "report.json"), "w", encoding="utf-8") as f:
        json.dump({"sut": sut["name"], "model": sut["model"], "judge": JUDGE_MODEL,
                   "note": "recall and precision are reported separately and never blended; the historical row is the reference",
                   "cases": rows}, f, indent=1, ensure_ascii=False)


def main(argv):
    sut_name, k, cases, mode, rejudge = "fable", 1, [], "run", False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--sut":
            sut_name = argv[i + 1]; i += 2
        elif a == "--k":
            k = int(argv[i + 1]); i += 2
        elif a in ("--check", "--redproof"):
            mode = a[2:]; i += 1
        elif a == "--rejudge":
            rejudge = True; i += 1
        else:
            cases.append(a); i += 1
    bad = check_frozen(os.path.join(S, "cases"))
    if bad:
        die("REFUSED — fixtures not frozen:\n  " + "\n  ".join(bad))
    if mode == "check":
        print("frozen: every timestamp <= T in every fixture")
        return
    report_root = os.path.join(S, "report")
    if mode == "redproof":
        sys.exit(0 if redproof(report_root, rejudge) else 1)
    sut = rr.resolve_sut(sut_name)
    if not sut:
        die("unknown SUT '%s' (see replay/models.yaml)" % sut_name)
    stored = rr.load_json(os.path.join(report_root, "judge-redproof.json")) or {}
    if not stored.get("rows") or stored.get("mismatches"):
        die("run `--redproof` first (and green) — the judge is unmeasured until then")
    if stored.get("fingerprint") != JUDGE_FP:
        die("judge configuration changed since the last red-proof (stored %s, current %s) — "
            "the judge is unmeasured; run `--redproof` first" % (stored.get("fingerprint"), JUDGE_FP))
    report = os.path.join(report_root, sut_name)
    os.makedirs(report, exist_ok=True)
    for name in cases or sorted(os.listdir(os.path.join(S, "cases"))):
        fx = json.load(open(os.path.join(S, "cases", name, "fixture.json"), encoding="utf-8"))
        for it in range(1, k + 1):
            rdir = os.path.join(report, name, "run-%d" % it)
            if os.path.isfile(os.path.join(rdir, "result.json")):
                print("skip %s run-%d (done)" % (name, it))
                continue
            print("run  %s run-%d (%s, timeout %ds) ..." % (name, it, fx["command"], fx["timeout"]))
            rc = run_case(sut, name, fx, rdir)
            print({0: "VALID", 1: "INVALID"}.get(rc, "INVALID"), "%s run-%d" % (name, it))
            if rc == 3:
                die("quota exhausted at %s/run-%d; resume after reset with the same command" % (name, it), 4)
    aggregate(sut, report)


if __name__ == "__main__":
    main(sys.argv[1:])
