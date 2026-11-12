#!/usr/bin/env python3
"""Judgment V1 — historical decisions with block / flag / no-finding gold.

    run_v1.py --check                      schema, approval, leak scan — no tokens
    run_v1.py --redproof [--rejudge]       scorer red-proof (free), then the judge's
    run_v1.py --sut <name> --arm treatment|baseline [--k 3] [item …]
    run_v1.py --report <name>              re-render the report from results

One item is one frozen decision snapshot (snapshots/), one `claude -p`
call with no tools, and a structured answer. Class, next action and
surfaced-or-not are scored by score.py; the judge answers one yes/no per
item — its key point — and only when gold and the answer both surfaced.

The two arms share prompt.md byte for byte. `treatment` puts the seat's
brief, read from the repository at run time, in the frame's context slot;
`baseline` puts one neutral sentence there. On a development set the
baseline is a diagnostic comparator: the report prints the arms side by
side and computes no verdict between them (README § What green proves).

Exit: 0 done · 2 usage / refused · 3 a check or red-proof failed ·
4 the SUT's session failed (quota) — resumable, finished runs are kept.
"""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(S)                              # evals/judgment
ROOT = os.path.dirname(os.path.dirname(J))
sys.path.insert(0, S)
import score as sc  # noqa: E402

REPORT = os.path.join(J, "report", "v1")
ARMS = ("treatment", "baseline")
BASELINE_CONTEXT = "You have no instructions beyond this message."
REQUIRED = ("id", "family", "set", "seat", "brief", "sources", "reconstruction", "snapshot",
            "gold", "materiality", "changes_if_answered_differently",
            "acceptable_alternates", "forbidden_shortcuts", "approved_by", "approved_on")
SESSION_ERR_RE = re.compile(
    r"(?i)hit your session limit|usage limit reached|rate.?limit.?error"
    r"|overloaded.?error|credit balance is too low|invalid x-api-key"
    r"|OAuth token has expired")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_actions():
    return {k: v for k, v in json.loads(read(S, "actions.json")).items()
            if not k.startswith("_")}


def load_items():
    out = {}
    for p in sorted(glob.glob(os.path.join(S, "items", "*.json"))):
        it = json.loads(read(p))
        it["_file"] = os.path.relpath(p, S)
        out[it.get("id", it["_file"])] = it
    return out


# ---- --check ---------------------------------------------------------------
def check(items=None, actions=None):
    """Every defect, as text; empty means the corpus may be run. Lint J2
    calls this on every push."""
    items = load_items() if items is None else items
    actions = load_actions() if actions is None else actions
    bad = []
    sets = {}
    for iid, it in items.items():
        where = "%s (%s)" % (iid, it.get("_file", "?"))
        missing = [k for k in REQUIRED if k not in it]
        if missing:
            bad.append("%s: missing %s" % (where, ", ".join(missing)))
            continue
        if not re.match(r"^J-[a-z0-9-]+$", iid):
            bad.append("%s: id is not J-<kebab>" % where)
        # approval is a state, not a defect: both null (awaiting the
        # maintainer's review of the full record) or both stamped. Anything
        # in between claims a review the repository cannot show.
        by, on = it["approved_by"], it["approved_on"]
        stamped = bool(by) and bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(on)))
        if not stamped and not (by is None and on is None):
            bad.append("%s: half-stamped approval — approved_by and approved_on are both "
                       "null, or a name and a YYYY-MM-DD date" % where)
        if it["set"] not in ("development", "holdout"):
            bad.append("%s: set is %r" % (where, it["set"]))
        sets.setdefault(it["family"], set()).add(it["set"])
        if "actions" in it:
            bad.append("%s: an item defines no actions of its own (actions.json)" % where)
        g = it["gold"]
        if g.get("decision") not in sc.CLASSES:
            bad.append("%s: gold.decision %r" % (where, g.get("decision")))
        if it["seat"] not in actions:
            bad.append("%s: seat %r has no vocabulary in actions.json" % (where, it["seat"]))
        elif g.get("next_action") not in actions[it["seat"]]:
            bad.append("%s: gold.next_action %r is not in the %s vocabulary"
                       % (where, g.get("next_action"), it["seat"]))
        if g.get("surfaced") != (g.get("decision") in sc.SURFACED):
            bad.append("%s: gold.surfaced must be true exactly for BLOCK / FLAG" % where)
        if g.get("decision") in sc.SURFACED and not it.get("key_point"):
            bad.append("%s: a surfaced gold needs a key_point for the judge" % where)
        if not os.path.exists(os.path.join(ROOT, it["brief"])):
            bad.append("%s: brief %s does not exist" % (where, it["brief"]))
        snap = os.path.join(S, it["snapshot"])
        if not os.path.exists(snap):
            bad.append("%s: snapshot %s does not exist" % (where, it["snapshot"]))
            continue
        text = read(snap)
        # the leak scan: nothing from after the decision point
        for n in it["sources"].get("issues", []):
            if re.search(r"#%d\b" % n, text):
                bad.append("%s: the snapshot names its source issue #%d" % (where, n))
        for phrase in it["forbidden_shortcuts"]:
            if phrase.lower() in text.lower():
                bad.append("%s: the snapshot carries the forbidden phrase %r" % (where, phrase))
        for word in sc.CLASSES:
            if word in text:
                bad.append("%s: the snapshot names a decision class (%s)" % (where, word))
    for fam, ss in sorted(sets.items()):
        if len(ss) > 1:
            bad.append("family %s is in both development and holdout" % fam)
    have = set(it["gold"].get("decision") for it in items.values() if "gold" in it)
    for cls in sc.CLASSES:
        if cls not in have:
            bad.append("no item has gold %s" % cls)
    frame = read(S, "prompt.md")
    for slot in ("{context}", "{actions}", "{snapshot}"):
        if frame.count(slot) != 1:
            bad.append("prompt.md must carry %s exactly once" % slot)
    return bad


def unapproved(items):
    """Ids whose full gold record the maintainer has not signed. Approving
    a plan, a class table or a pull request is not this signature."""
    return sorted(iid for iid, it in items.items()
                  if not (it.get("approved_by") and it.get("approved_on")))


def spend_refusal(items):
    """Why no model call may be made on `items`, or None. SUT and judge
    alike: an unreviewed oracle produces numbers nobody may read."""
    todo = unapproved(items)
    if not todo:
        return None
    return ("refused: %d item(s) await the maintainer's review of their full gold record "
            "(approved_by / approved_on are null): %s" % (len(todo), ", ".join(todo)))


def class_counts(items):
    return {c: sum(1 for it in items.values() if it["gold"]["decision"] == c)
            for c in sc.CLASSES}


# ---- scorer red-proof — no model --------------------------------------------
def canned(items, actions, policy, k=1):
    """Answer sets with known scores. `policy` names what every run says."""
    rows = []
    for iid, it in sorted(items.items()):
        g = it["gold"]
        for run in range(1, k + 1):
            a = {"item": iid, "arm": policy, "run": run, "valid": True,
                 "decision": g["decision"], "next_action": g["next_action"],
                 "surfaced": g["surfaced"], "key_point": "yes" if g["surfaced"] else None}
            if policy == "all-block":
                a.update(decision="BLOCK", surfaced=True)
            elif policy == "all-no-finding":
                a.update(decision="NO_FINDING", surfaced=False, key_point=None)
            elif policy == "ask-or-ignore" and g["decision"] == "FLAG_AND_CONTINUE":
                a.update(decision="BLOCK")
            elif policy == "flag-wrong-action" and g["decision"] == "FLAG_AND_CONTINUE":
                a.update(next_action=next(x for x in sorted(actions[it["seat"]])
                                          if x != g["next_action"]))
            elif policy == "one-item-invalid" and iid == sorted(items)[0]:
                a.update(valid=False, decision=None, next_action=None, surfaced=None,
                         key_point=None)
            rows.append(a)
    return rows


def scorer_redproof(items=None, actions=None):
    items = load_items() if items is None else items
    actions = load_actions() if actions is None else actions
    exp = json.loads(read(S, "redproof", "scorer.json"))
    bad = []
    for policy, want in exp["policies"].items():
        rep = sc.score(items, canned(items, actions, policy, want.get("k", 1)))[policy]
        got = {m: [rep[m]["n"], rep[m]["of"]] for m in
               ("recall", "precision", "false_block", "missed_block", "flag_accuracy")}
        got["validity"] = [rep["validity"]["scheduled"], rep["validity"]["valid"],
                           rep["validity"]["invalid"]]
        for m, v in want.items():
            if m != "k" and got.get(m) != v:
                bad.append("scorer red-proof %s: %s is %s, expected %s"
                           % (policy, m, got.get(m), v))
        text = sc.render({policy: rep})
        if "scheduled %d · valid %d · invalid %d" % tuple(got["validity"]) not in text:
            bad.append("scorer red-proof %s: the report hides the validity line" % policy)
    return bad


# ---- the judge — one proposition per item -----------------------------------
def judged_document(answer):
    return "Surfaced to the human: %s\n\nRationale: %s" % (
        answer.get("surfaced") or "(nothing)", answer.get("rationale") or "")


def judge_module():
    """The existing tier's judge, imported only when a judge call is due."""
    sys.path.insert(0, J)
    import run_judgment
    return run_judgment


def judge_fingerprint(items):
    rj = judge_module()
    h = hashlib.sha256()
    for part in (rj.JUDGE_PROMPT, rj.JUDGE_MODEL, str(rj.MIN_QUOTE), rj.QUOTE_POLICY,
                 read(S, "redproof", "judge.json")):
        h.update(part.encode("utf-8") + b"\0")
    for iid, it in sorted(items.items()):
        h.update((iid + "\0" + it.get("key_point", "") + "\0").encode("utf-8"))
    return h.hexdigest()[:16]


def judge_config_fingerprint():
    """The judge as configured — prompt, model, quote policy. A key-point
    verdict is evidence only under the configuration that produced it; the
    item's key point is already part of the run fingerprint."""
    rj = judge_module()
    return sha("\0".join((rj.JUDGE_PROMPT, rj.JUDGE_MODEL, str(rj.MIN_QUOTE),
                          rj.QUOTE_POLICY)))


def judge_answer(it, answer):
    """The key-point fields of a result, for a surfaced answer to a
    surfaced gold; all None otherwise."""
    if not (it["gold"]["surfaced"] and answer["decision"] in sc.SURFACED):
        return {"key_point": None}
    v = judge_module().verdict_on(it["key_point"], judged_document(answer))
    return {"key_point": v["answer"], "key_point_quote": v["quote"],
            "judge_fingerprint": judge_config_fingerprint()}


def judge_redproof(items, rejudge=False):
    """Per judged item: documents that must read yes, documents that must
    read no (a real but different concern; an unrelated answer). Verdicts
    are cached under the judge fingerprint."""
    rj = judge_module()
    fp = judge_fingerprint(items)
    exp = json.loads(read(S, "redproof", "judge.json"))
    path = os.path.join(REPORT, "judge-redproof.json")
    stored = json.loads(read(path)) if os.path.exists(path) else {}
    prior = {} if rejudge or stored.get("fingerprint") != fp else {
        (r["item"], r["doc"]): r for r in stored.get("rows", [])}
    rows, mism = [], 0
    for iid, it in sorted(items.items()):
        if not it["gold"]["surfaced"]:
            continue
        docs = exp.get(iid)
        if not docs or not docs.get("yes") or len(docs.get("no", [])) < 2:
            die("judge red-proof: %s needs yes documents and two no documents" % iid, 3)
        for want in ("yes", "no"):
            for doc in docs[want]:
                r = prior.get((iid, doc))
                if r is None:
                    v = rj.verdict_on(it["key_point"], doc)
                    r = {"item": iid, "doc": doc, "want": want, "got": v["answer"]}
                ok = r["got"] == want
                mism += not ok
                rows.append(r)
                print("%s judge red-proof %s: wanted %s, got %s"
                      % ("PASS" if ok else "FAIL", iid, want, r["got"]))
    os.makedirs(REPORT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": fp, "green": mism == 0, "rows": rows}, f, indent=1)
    return mism


def judge_is_green(items):
    path = os.path.join(REPORT, "judge-redproof.json")
    if not os.path.exists(path):
        return False
    stored = json.loads(read(path))
    return bool(stored.get("green")) and stored.get("fingerprint") == judge_fingerprint(items)


# ---- one run -----------------------------------------------------------------
def build_prompt(it, arm, actions):
    context = BASELINE_CONTEXT if arm == "baseline" else (
        "You hold the `%s` seat. Its instructions:\n\n<<<BRIEF\n%s\nBRIEF>>>"
        % (it["seat"], read(ROOT, it["brief"])))
    menu = "\n".join("- `%s` — %s" % kv for kv in actions[it["seat"]].items())
    frame = read(S, "prompt.md")
    return (frame.replace("{context}", context).replace("{actions}", menu)
            .replace("{snapshot}", read(S, it["snapshot"]).rstrip("\n")))


def parse_answer(text, it, actions):
    """(answer, invalid_reason). Nothing is coerced: an answer outside the
    classes or the seat's vocabulary is INVALID, never a class."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        obj = json.loads(m.group(0)) if m else None
    except ValueError:
        obj = None
    if not isinstance(obj, dict):
        return None, "no JSON object in the answer"
    # types first: an array or an object is not hashable, and a membership
    # test on it would raise instead of recording the run as INVALID
    for key in ("decision", "next_action"):
        if not isinstance(obj.get(key), str):
            return None, "%s is not a string (%r)" % (key, obj.get(key))
    if obj["decision"] not in sc.CLASSES:
        return None, "decision %r is not a class" % obj["decision"]
    if obj["next_action"] not in actions[it["seat"]]:
        return None, "next_action %r is not in the %s vocabulary" % (
            obj["next_action"], it["seat"])
    surfaced = obj.get("surfaced")
    if surfaced is not None and not isinstance(surfaced, str):
        return None, "surfaced is neither a string nor null (%r)" % (surfaced,)
    if not isinstance(obj.get("rationale") or "", str):
        return None, "rationale is not a string"
    if isinstance(surfaced, str) and surfaced.strip().lower() in ("", "null", "none"):
        surfaced = None
    return {"decision": obj["decision"], "next_action": obj["next_action"],
            "surfaced": surfaced, "rationale": obj.get("rationale") or ""}, None


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def item_hash(it):
    return sha(json.dumps({k: v for k, v in it.items() if k != "_file"}, sort_keys=True))


def run_fingerprint(it, arm, actions):
    """What a result is evidence about: the prompt as sent (frame, brief or
    baseline sentence, vocabulary, snapshot) and the item's record (gold,
    key point). A result lives under `fp-<this>`; when any of it changes
    the old results stay on disk, are reported as stale and are never
    scored with the new ones — and the sweep runs the item again."""
    return sha(build_prompt(it, arm, actions) + "\0" + item_hash(it))


def run_one(model, it, arm, actions):
    prompt = build_prompt(it, arm, actions)
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(["claude", "-p", prompt, "--model", model, "--tools", "",
                              "--output-format", "json"],
                             cwd=d, capture_output=True, text=True, timeout=600)
    try:
        res = json.loads(out.stdout)
    except ValueError:
        res = {"result": "", "is_error": True}
    text = res.get("result") or ""
    if SESSION_ERR_RE.search(text) or SESSION_ERR_RE.search(out.stderr or ""):
        die("the SUT's session failed (%s) — resume after reset; finished runs are kept"
            % (text or out.stderr)[:120], 4)
    stamp = {"item": it["id"], "arm": arm, "model": model, "prompt_sha256": sha(prompt),
             "item_sha256": item_hash(it), "fingerprint": run_fingerprint(it, arm, actions),
             "brief_sha256": sha(read(ROOT, it["brief"])),
             "frame_sha256": sha(read(S, "prompt.md"))}
    answer, why = parse_answer(text, it, actions)
    if answer is None:
        return dict(stamp, valid=False, invalid_reason=why, raw=text[-600:])
    result = dict(stamp, valid=True, **answer, surfaced_text=answer["surfaced"])
    result["surfaced"] = bool(answer["surfaced"])
    result.update(judge_answer(it, answer))
    return result


def judgment_is_stale(result, judge_fp):
    return result.get("key_point") is not None and result.get("judge_fingerprint") != judge_fp


def rejudge(path, it):
    """Re-ask the judge about a stored answer; the SUT is not called."""
    r = json.loads(read(path))
    r.update(judge_answer(it, {"decision": r["decision"], "surfaced": r.get("surfaced_text"),
                               "rationale": r.get("rationale")}))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)


def run_dir(sut, it, arm, actions, i, root=None):
    return os.path.join(root or REPORT, sut, arm, it["id"],
                        "fp-%s" % run_fingerprint(it, arm, actions), "run-%d" % i)


def load_results(sut, items, actions, root=None, judge_fp=None):
    """(current, stale). Current: recorded under today's fingerprint for
    its item and arm. Stale: anything else on disk — another brief,
    snapshot, frame, vocabulary or gold, or an item that left the corpus.
    A current answer whose key-point verdict came from another judge
    configuration keeps its class and action and reads `judge-stale` in
    the judged column until the sweep re-judges it."""
    judge_fp = judge_fp or judge_config_fingerprint()
    current, stale = [], []
    pattern = os.path.join(root or REPORT, sut, "*", "*", "fp-*", "run-*", "result.json")
    for p in sorted(glob.glob(pattern)):
        r = json.loads(read(p))
        rdir = os.path.dirname(p)
        r["run"] = int(os.path.basename(rdir).split("-")[1])
        fp = os.path.basename(os.path.dirname(rdir))[len("fp-"):]
        it = items.get(r.get("item"))
        if it and r.get("arm") in ARMS and fp == run_fingerprint(it, r["arm"], actions):
            if judgment_is_stale(r, judge_fp):
                r["key_point"] = "judge-stale"
            current.append(r)
        else:
            stale.append(r)
    return current, stale


def report(sut, items, actions):
    rows, stale = load_results(sut, items, actions)
    if not rows:
        die("no current results under %s (%d stale)" % (os.path.join(REPORT, sut), len(stale)))
    rep = sc.score(items, rows)
    meta = {"fingerprints": {arm: {iid: run_fingerprint(it, arm, actions)
                                   for iid, it in sorted(items.items())} for arm in ARMS},
            "stale_excluded": len(stale)}
    with open(os.path.join(REPORT, sut, "report.json"), "w", encoding="utf-8") as f:
        json.dump(dict(rep, _meta=meta), f, indent=1)
    if stale:
        by = {}
        for r in stale:
            key = "%s/%s" % (r.get("arm"), r.get("item"))
            by[key] = by.get(key, 0) + 1
        print("!! %d stale result(s) excluded — recorded under an older brief, snapshot, "
              "frame, vocabulary or gold: %s"
              % (len(stale), ", ".join("%s ×%d" % kv for kv in sorted(by.items()))))
    print(sc.render(rep))
    print("\nDevelopment set only: these numbers show whether today's briefs keep the "
          "judgment each incident taught.\nThey do not show that a brief adds value over "
          "the baseline — that needs holdout evidence.")


def main(argv):
    items, actions = load_items(), load_actions()
    if "--check" in argv:
        bad = check(items, actions)
        for b in bad:
            print("FAIL " + b)
        cc = class_counts(items) if not bad else {}
        print("%d items%s — %s" % (len(items), "".join(" · %s %d" % kv for kv in cc.items()),
                                   "ok" if not bad else "%d defect(s)" % len(bad)))
        todo = unapproved(items)
        print("approved %d/%d%s" % (len(items) - len(todo), len(items),
                                    "" if not todo else " — not runnable until reviewed: "
                                    + ", ".join(todo)))
        return 3 if bad else 0
    bad = check(items, actions) + scorer_redproof(items, actions)
    if bad:
        for b in bad:
            print("FAIL " + b)
        return 3
    if "--redproof" in argv:
        print("PASS scorer red-proof (no model)")
        if spend_refusal(items):
            die("judge red-proof " + spend_refusal(items), 3)
        return 3 if judge_redproof(items, "--rejudge" in argv) else 0
    if "--report" in argv:
        report(argv[argv.index("--report") + 1], items, actions)
        return 0
    if "--sut" not in argv or "--arm" not in argv:
        die(__doc__)
    sut, arm = argv[argv.index("--sut") + 1], argv[argv.index("--arm") + 1]
    k = int(argv[argv.index("--k") + 1]) if "--k" in argv else 3
    if arm not in ARMS:
        die("--arm is treatment or baseline")
    rr = judge_module().rr
    row = rr.resolve_sut(sut)
    if not row:
        die("unknown SUT '%s' (evals/replay/models.yaml)" % sut)
    if row["mode"] != "subscription":
        die("Judgment V1 runs subscription rows only (%s is %s)" % (sut, row["mode"]))
    flags = {"--sut", "--arm", "--k"}
    named = [a for i, a in enumerate(argv) if not a.startswith("--") and argv[i - 1] not in flags]
    for iid in named:
        if iid not in items:
            die("unknown item %s" % iid)
    refusal = spend_refusal({i: items[i] for i in named} if named else items)
    if refusal:
        die(refusal, 3)
    if not judge_is_green(items):
        die("the judge red-proof is not green under the current fingerprint — "
            "run --redproof first", 3)
    for iid in named or sorted(items):
        for i in range(1, k + 1):
            rdir = run_dir(sut, items[iid], arm, actions, i)
            done = os.path.join(rdir, "result.json")
            if os.path.exists(done):
                if judgment_is_stale(json.loads(read(done)), judge_config_fingerprint()):
                    rejudge(done, items[iid])
                    print("rejudge %s %s run-%d (the judge changed; the answer is kept)"
                          % (arm, iid, i))
                else:
                    print("skip %s %s run-%d (done)" % (arm, iid, i))
                continue
            result = run_one(row["model"], items[iid], arm, actions)
            os.makedirs(rdir, exist_ok=True)
            with open(os.path.join(rdir, "result.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, indent=1, ensure_ascii=False)
            print("%s %s run-%d: %s" % (arm, iid, i, result.get("decision") or "INVALID"))
    report(sut, items, actions)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
