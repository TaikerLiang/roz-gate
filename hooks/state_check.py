"""roz-check — may an operation start from this observed state? (#134)

Mechanical policy over a roz-state snapshot (references/roz-state.md): the
entry preconditions of `integrate` (commands/integrate.md § 1) as rules.
Pure — a snapshot in, a result out; no forge, no git, no file, no mutation.
The comparisons roz-state may not make live here: a record's `reviewed_sha`
against the CR's head, a closed-unmerged CR counted as absent, a thread
count read as "clear".

Every rule is pass / fail / unknown / not_evaluated:
  pass           the precondition holds
  fail           it is known not to hold
  unknown        the fact it needs is `unknown` in the snapshot — neither
                 satisfied nor refuted (#239's invariant); never a pass
  not_evaluated  its prerequisite rule did not pass (failed OR unknown), so
                 there is nothing to evaluate — one root cause, not several

Verdict: any fail → ineligible; else any unknown → unknown; else eligible.
`may_start` is true only for `eligible`: `ineligible` (a known precondition
failed) and `unknown` (the checker could not establish that all pass) stay
distinct, and both mean the operation must not take the lock.

Evidence is the snapshot's own fact, copied whole (path + the envelope with
its status, value, source and reason), so a STOP message or an audit never
reconstructs why a rule came out as it did.

A check result is not a snapshot: `eligible`, `verdict` and the rule codes
live here and stay on the snapshot's policy deny-list. Not a hook; kept in
hooks/ beside state_contract.py for layout convenience. Stdlib only.
"""

import copy

from state_contract import validate

SCHEMA = "roz-check/0.1"
STATUSES = ("pass", "fail", "unknown", "not_evaluated")
VERDICTS = ("eligible", "ineligible", "unknown")
LEGAL_ENTRY = (None, "in-user-review")


def _get(snap, path):
    node = snap
    for k in path.split("."):
        node = node[k]
    return node


def _plain(snap, path):
    return {"path": path, "value": snap[path]}


def _fact(snap, path):
    return {"path": path, "fact": copy.deepcopy(_get(snap, path))}


def _on_fact(snap, path, holds, also=()):
    """A rule over one envelope fact: unknown → unknown (with its reason);
    absent → fail; observed → pass iff `holds(value)`."""
    env = _get(snap, path)
    evidence = [_fact(snap, path)] + [_fact(snap, p) for p in also]
    if env["status"] == "unknown":
        return "unknown", env.get("reason"), evidence
    if env["status"] == "absent":
        return "fail", None, evidence
    return ("pass" if holds(env["value"]) else "fail"), None, evidence


def _on_plain(snap, paths, holds):
    return ("pass" if holds(snap) else "fail"), None, [_plain(snap, p) for p in paths]


def _review_current(snap):
    """The record's reviewed_sha is the CR's head. Both facts are observed —
    the prerequisites passed. A record with no readable sha is not current."""
    rec, cr = _get(snap, "implementation.review_marker"), _get(snap, "implementation.cr")
    evidence = [_fact(snap, "implementation.review_marker"), _fact(snap, "implementation.cr")]
    sha = rec["value"]["reviewed_sha"]
    return ("pass" if sha is not None and sha == cr["value"]["head_sha"] else "fail"), \
        None, evidence


def _live(cr):                      # a closed-unmerged CR counts as absent (integrate.md § 1)
    return cr["state"] in ("open", "merged")


# code → (prerequisite, the rule, the sentence of commands/integrate.md § 1 it implements)
INTEGRATE = (
    ("TRACK_NOT_FAST", None,
     lambda s: _on_plain(s, ["track"], lambda x: x["track"] != "fast"),
     "`track: fast` → stop: the fast track has no integration stage"),
    ("NOT_LOCKED", None,
     lambda s: _on_plain(s, ["processing"], lambda x: x["processing"] is False),
     "`status: processing` → stop: another command holds it."),
    ("NOT_BLOCKED", None,
     lambda s: _on_plain(s, ["blocked"], lambda x: x["blocked"] is False),
     "`status: blocked` → stop: waiting on the human"),
    ("ENTRY_STATUS_LEGAL", None,
     lambda s: _on_plain(s, ["status"], lambda x: x["status"] in LEGAL_ENTRY),
     "The legal entries are **no `status:`** (patrol's route, or the human cleared "
     "`blocked`) and **`status: in-user-review`**"),
    ("SPEC_BRANCH_EXISTS", None,
     lambda s: _on_fact(s, "branches.spec", lambda v: True),
     "the spec branch `<spec-branch>`"),
    ("IMPLEMENTATION_CR_EXISTS", None,
     lambda s: _on_fact(s, "implementation.cr", _live),
     "the implementation CR (head `<feat-branch>`)"),
    ("QA_CR_EXISTS", None,
     lambda s: _on_fact(s, "qa.cr", _live),
     "a closed-unmerged CR counts as absent, and a CR that is absent stops the run"),
    ("IMPLEMENTATION_REVIEW_THREADS_CLEAR", "IMPLEMENTATION_CR_EXISTS",
     lambda s: _on_fact(s, "implementation.open_review_threads", lambda v: v == 0),
     "THREADS-LIST shows **no open review threads**"),
    ("IMPLEMENTATION_REVIEW_RECORDED", "IMPLEMENTATION_CR_EXISTS",
     lambda s: _on_fact(s, "implementation.review_marker", lambda v: True),
     "carries a `**[reviewer] · code-review**` comment"),
    ("IMPLEMENTATION_REVIEW_CURRENT", "IMPLEMENTATION_REVIEW_RECORDED", _review_current,
     "whose `reviewed-sha:` is the CR's head"),
    ("QA_CR_NOT_DRAFT", "QA_CR_EXISTS",
     lambda s: _on_fact(s, "qa.cr", lambda v: v["draft"] is False),
     "Verify the **QA CR is not a draft** (CR-VIEW)"),
    ("FIDELITY_THREADS_CLEAR", "QA_CR_EXISTS",
     lambda s: _on_fact(s, "qa.open_fidelity_threads", lambda v: v == 0),
     "Verify the **QA CR has no open fidelity threads** (THREADS-LIST)"),
    ("FIDELITY_AUDIT_RECORDED", "QA_CR_EXISTS",
     lambda s: _on_fact(s, "qa.fidelity_marker", lambda v: True),
     "Verify the **QA CR carries a `**[reviewer] · fidelity**` comment**"),
)
OPERATIONS = {"integrate": INTEGRATE}


class InvalidSnapshot(ValueError):
    """The input is not a snapshot the contract accepts — never checked."""


def check(operation, snapshot):
    """The result for `operation` over `snapshot`. Raises InvalidSnapshot for
    anything state_contract.validate rejects, KeyError for an unknown
    operation. The snapshot is not modified."""
    rules = OPERATIONS[operation]
    errs = validate(snapshot)
    if errs:
        raise InvalidSnapshot("; ".join(errs[:5]))
    out, status = [], {}
    for code, requires, rule, _source in rules:
        if requires and status[requires] != "pass":
            # prerequisite fail or unknown → nothing to evaluate (transitive:
            # a not_evaluated prerequisite is not a pass either)
            status[code] = "not_evaluated"
            out.append({"code": code, "status": "not_evaluated", "requires": requires,
                        "evidence": []})
            continue
        st, reason, evidence = rule(snapshot)
        status[code] = st
        entry = {"code": code, "status": st, "evidence": evidence}
        if requires:
            entry["requires"] = requires
        if st == "unknown":
            entry["reason"] = reason
        out.append(entry)
    failed = [r["code"] for r in out if r["status"] == "fail"]
    unknown = [r["code"] for r in out if r["status"] == "unknown"]
    verdict = "ineligible" if failed else "unknown" if unknown else "eligible"
    return {"schema": SCHEMA, "operation": operation, "issue": snapshot["issue"],
            "verdict": verdict, "may_start": verdict == "eligible", "rules": out,
            "failed": failed, "unknown": unknown}


def check_integrate(snapshot):
    return check("integrate", snapshot)
