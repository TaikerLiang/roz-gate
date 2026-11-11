"""The roz-state observation contract as code (references/roz-state.md, #239).

A shared contract and validation module. It lives in hooks/ beside
branch_names.py for layout convenience only: it is not a hook rule and the
hook layer does not own it; #133 (bin/roz-state) imports it and may move
it when a state package exists. Stdlib only, no I/O.

A collector emits exactly one of two things:
- a snapshot — `validate(obj) == []`;
- a typed collection failure — `validate_failure(obj) == []` — when the
  issue's identity, base state or config could not be established. No
  partial snapshot, no fabricated plain field.

Inside a snapshot, identity is plain (PLAIN, CONFIG); every other fact is
an envelope `{"status", "value", "source"[, "reason"]}`:
  observed  the collector asked and got a value (0 and [] are values)
  absent    the entity or fact itself does not exist
  unknown   the collector could not establish it — `reason` required
absent is never a stand-in for zero, and unknown is never read as 0,
false or empty.

Strict within SCHEMA: a key this version does not declare is an error for
a snapshot of this version. Adding an observational field is an additive
revision (the table, this module, the tests, and SCHEMA move together) —
never a policy field: POLICY_KEYS are rejected at every depth, in every
version.
"""

import re
from datetime import datetime

SCHEMA = "roz-state/0.1"
STATUSES = ("observed", "absent", "unknown")
REASONS = ("forge_query_failed", "remote_unreachable", "ambiguous", "depends_on_unknown",
           "unsupported")
# decisions and derived verdicts — roz-check's (#134) or the agent's, never a fact
POLICY_KEYS = ("action", "next_action", "next_stage", "transition", "ready_for_integration",
               "review_clean", "fidelity_current", "eligible")


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _str(v):
    return isinstance(v, str) and v != ""


def _utc(v):
    """One spelling only: UTC, whole seconds, a literal Z — YYYY-MM-DDTHH:MM:SSZ."""
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", v):
        return False
    try:
        datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _opt_str(v):
    return v is None or _str(v)


def _record(spec):
    """A dict with exactly these keys, each passing its predicate."""
    def check(v):
        return (isinstance(v, dict) and set(v) == set(spec)
                and all(spec[k](v[k]) for k in spec))
    return check


def _count(v):
    return _int(v) and v >= 0


def _list_of(item):
    return lambda v: isinstance(v, list) and all(item(x) for x in v)


BRANCH = _record({"name": _str, "sha": _str})
CR = _record({"number": _int, "state": lambda v: v in ("open", "merged", "closed"),
              "draft": lambda v: isinstance(v, bool), "base": _str, "head_sha": _str})
# reviewed_sha null: the record is there and carries no readable sha — the
# fidelity record never does today, only the code-review record (#133)
MARKER = _record({"reviewed_sha": _opt_str, "comment_id": _int})
BLOCKERS = _list_of(_record({"issue": _int, "state": lambda v: v in ("open", "closed"),
                             "url": _str}))

# snapshot identity: plain values — if one cannot be read there is no snapshot
PLAIN = {
    "schema": lambda v: v == SCHEMA,
    "observed_at": _utc,
    "issue": _int,
    "track": _opt_str,          # null: the label is not worn — an established fact
    "status": _opt_str,
    "processing": lambda v: isinstance(v, bool),
    "blocked": lambda v: isinstance(v, bool),
}
# the resolved config values that shaped the observation — not the whole block
CONFIG = {"branch_template": _str, "default_branch": _str, "acceptance_dir": _str}

# every other fact: path → the shape of `value` when observed
FACTS = {
    "branches.spec": BRANCH,
    "branches.implementation": BRANCH,
    "branches.qa": BRANCH,
    "spec.cr": CR,
    "implementation.cr": CR,
    "implementation.open_review_threads": _count,
    "implementation.review_marker": MARKER,
    "qa.cr": CR,
    "qa.open_fidelity_threads": _count,
    "qa.fidelity_marker": MARKER,
    "dependencies.blocked_by": BLOCKERS,
}
# a fact about a CR follows the CR: absent under absent, unknown under unknown
DEPENDS = {
    "implementation.open_review_threads": "implementation.cr",
    "implementation.review_marker": "implementation.cr",
    "qa.open_fidelity_threads": "qa.cr",
    "qa.fidelity_marker": "qa.cr",
}
# counts and collections: established → a value; "nothing there" is 0 / [], not absent
COUNTED = ("implementation.open_review_threads", "qa.open_fidelity_threads")
NEVER_ABSENT = ("dependencies.blocked_by",)     # the issue always exists
ENVELOPE_KEYS = ("status", "value", "source", "reason")


def _get(obj, path):
    for k in path.split("."):
        if not isinstance(obj, dict) or k not in obj:
            return None, False
        obj = obj[k]
    return obj, True


def _policy(obj, path, errs):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (path, k) if path else str(k)
            if k in POLICY_KEYS:
                errs.append("%s: policy field, never a fact" % p)
            _policy(v, p, errs)
    elif isinstance(obj, list):
        for x in obj:
            _policy(x, path, errs)


def _undeclared(obj, errs):
    groups = {}
    for path in FACTS:
        head, leaf = path.split(".")
        groups.setdefault(head, set()).add(leaf)
    for k, v in obj.items():
        if k in POLICY_KEYS or k in PLAIN:
            continue
        if k == "config":
            for ck in (v if isinstance(v, dict) else {}):
                if ck not in CONFIG and ck not in POLICY_KEYS:
                    errs.append("config.%s: undeclared in %s" % (ck, SCHEMA))
        elif k in groups:
            for leaf in (v if isinstance(v, dict) else {}):
                if leaf not in groups[k] and leaf not in POLICY_KEYS:
                    errs.append("%s.%s: undeclared in %s" % (k, leaf, SCHEMA))
        elif k != "collection_failure":
            errs.append("%s: undeclared in %s" % (k, SCHEMA))


def _envelope(path, env, shape, errs):
    """Check one envelope; return its status, or None when it is not one."""
    if not isinstance(env, dict) or "status" not in env:
        errs.append("%s: not an envelope ({status, value, source})" % path)
        return None
    status = env["status"]
    if status not in STATUSES:
        errs.append("%s: status must be one of %s" % (path, ", ".join(STATUSES)))
        return None
    for k in env:
        if k not in ENVELOPE_KEYS and k not in POLICY_KEYS:
            errs.append("%s: undeclared key %s" % (path, k))
    if not _str(env.get("source")):
        errs.append("%s: source is required" % path)
    if status == "unknown":
        if "reason" not in env:
            errs.append("%s: unknown needs a reason" % path)
        elif env["reason"] not in REASONS:
            errs.append("%s: reason must be one of %s" % (path, ", ".join(REASONS)))
    elif "reason" in env:
        errs.append("%s: reason only with unknown" % path)
    if status == "observed":
        if not shape(env.get("value")):
            errs.append("%s: value does not match the contract's shape" % path)
    elif env.get("value") is not None or "value" not in env:
        errs.append("%s: value must be null when %s" % (path, status))
    return status


def validate(snapshot):
    """Errors as `path: message`; an empty list means a valid snapshot."""
    if not isinstance(snapshot, dict):
        return ["snapshot: not an object"]
    errs = []
    if "collection_failure" in snapshot:
        errs.append("not a snapshot: collection_failure (validate_failure checks it)")
    _policy(snapshot, "", errs)
    _undeclared(snapshot, errs)
    for k, pred in PLAIN.items():
        if k not in snapshot:
            errs.append("%s: missing" % k)
        elif k == "schema" and not pred(snapshot[k]):
            errs.append("schema: this validator checks %s" % SCHEMA)
        elif k == "observed_at" and not pred(snapshot[k]):
            errs.append("observed_at: must be UTC as YYYY-MM-DDTHH:MM:SSZ")
        elif not pred(snapshot[k]):
            errs.append("%s: plain value of the wrong type" % k)
    config = snapshot.get("config")
    if not isinstance(config, dict):
        errs.append("config: missing")
    for k, pred in CONFIG.items():
        if not isinstance(config, dict) or k not in config:
            errs.append("config.%s: missing" % k)
        elif not pred(config[k]):
            errs.append("config.%s: plain value of the wrong type" % k)
    for head in sorted({p.split(".")[0] for p in FACTS}):
        if head not in snapshot:
            errs.append("%s: missing" % head)
    status = {}
    for path, shape in FACTS.items():
        env, found = _get(snapshot, path)
        if not found:
            errs.append("%s: missing" % path)
            continue
        status[path] = _envelope(path, env, shape, errs)
    for path, st in status.items():
        if st is None:
            continue
        if path in NEVER_ABSENT and st == "absent":
            errs.append("%s: never absent — observed (possibly empty) or unknown" % path)
        parent = status.get(DEPENDS.get(path))
        if parent == "absent" and st != "absent":
            errs.append("%s: must be absent — %s is absent" % (path, DEPENDS[path]))
        elif parent == "unknown":
            env, _ = _get(snapshot, path)
            if st != "unknown":
                errs.append("%s: must be unknown — %s is unknown" % (path, DEPENDS[path]))
            elif env.get("reason") != "depends_on_unknown":
                errs.append("%s: reason must be depends_on_unknown — %s is unknown"
                            % (path, DEPENDS[path]))
        elif parent == "observed" and st == "absent" and path in COUNTED:
            errs.append("%s: absent under an observed %s — a count that found nothing is "
                        "observed 0" % (path, DEPENDS[path]))
    return errs


def validate_failure(obj):
    """Errors for a typed collection failure; an empty list means valid."""
    if not isinstance(obj, dict):
        return ["failure: not an object"]
    errs = []
    if set(obj) != {"schema", "collection_failure"}:
        errs.append("failure: exactly schema and collection_failure — no snapshot fields")
    if obj.get("schema") != SCHEMA:
        errs.append("schema: this validator checks %s" % SCHEMA)
    f = obj.get("collection_failure")
    if not isinstance(f, dict):
        return errs + ["collection_failure: not an object"]
    if f.get("reason") not in REASONS:
        errs.append("collection_failure.reason: must be one of %s" % ", ".join(REASONS))
    if not _str(f.get("source")):
        errs.append("collection_failure.source: required")
    if "detail" in f and not isinstance(f["detail"], str):
        errs.append("collection_failure.detail: a string")
    for k in f:
        if k not in ("reason", "source", "detail"):
            errs.append("collection_failure.%s: undeclared" % k)
    return errs
