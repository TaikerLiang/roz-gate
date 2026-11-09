"""branch_names — the one implementation of `references/branch-names.md`
(#135): template validity, Expand, the placeholder patterns the hooks match
with, and Lookup over one remote-heads snapshot.

Who imports it: `bin/roz-branch` (the CLI), `bin/roz-config` (validity),
`hooks/guard_acceptance.py` (is HEAD a spec branch), `hooks/guard_gate.py`
rule K (same-issue siblings). `hooks/guard_blind.py` does not: it denies
the exact `feat=<branch>` the marker names, not a template.

The boundary (#239): everything here is a *fact* about names and refs.
`match_heads` returns every match with its parsed `{seq}` / `{user}` and a
typed outcome; it never names the live attempt, and `expand` never
computes the next `{seq}` — the caller passes it (`1 + max`, the commands'
rule; `roz-check`'s later). A remote that could not be read is `unknown`,
never an empty match set.

Stdlib only. Importable from `hooks/` (the hooks' own dir) and from `bin/`
(which puts `hooks/` on `sys.path`, as `roz-config` does for config_block).
"""

import hashlib
import json
import os
import re
import subprocess
import time

DEFAULT = "{kind}/{n}"
KINDS = ("spec", "feat", "qa", "fast")
PLACEHOLDERS = ("{kind}", "{type}", "{user}", "{n}", "{seq}")
# `{type}` for the two kinds whose type is fixed by the contract; feat and
# fast render the issue's `type:` label, which the caller supplies.
FIXED_TYPE = {"spec": "spec", "qa": "test"}
LOCAL_FILE = os.path.join(".claude", "roz-gate.local.json")

OUTCOMES = ("UNKNOWN", "NO_MATCH", "ONE", "MULTIPLE_SEQ", "MULTIPLE_SAME_SEQ")


class BranchNameError(ValueError):
    """code ∈ INVALID_TEMPLATE · MISSING_REQUIRED_VALUE · INVALID_SEQUENCE."""

    def __init__(self, code, why):
        super().__init__("%s: %s" % (code, why))
        self.code, self.why = code, why


# ---- the template -----------------------------------------------------------

def validate(template):
    """None when valid, else the reason (bin/roz-config's message, verbatim):
    `{n}`, one of `{kind}` / `{type}`, no other placeholder."""
    t = template if template else DEFAULT
    unknown = [p for p in re.findall(r"\{[^{}]*\}", t) if p not in PLACEHOLDERS]
    if unknown:
        return "unknown placeholder %s — the five are %s" % (", ".join(unknown),
                                                              " ".join(PLACEHOLDERS))
    if "{n}" not in t:
        return "it has no {n}, so two issues would share a branch"
    if "{kind}" not in t and "{type}" not in t:
        return "it has neither {kind} nor {type}, so an issue's spec and qa branches would collide"
    found = re.findall(r"\{[a-z]+\}", t)
    dup = sorted({p for p in found if found.count(p) > 1})
    if dup:
        return "placeholder %s appears more than once" % ", ".join(dup)
    return None


def effective(template):
    """The template the loop uses: absent / blank → the default."""
    t = (template or "").strip()
    return t or DEFAULT


def pieces(template):
    return [p for p in re.split(r"(\{[a-z]+\})", effective(template)) if p]


# ---- Expand -------------------------------------------------------------------

def expand(template, *, kind, n, type=None, user=None, seq=None):
    """One name for one kind. Pure: config + arguments → string. A slot the
    template names and the caller left out raises MISSING_REQUIRED_VALUE;
    `{seq}` is never computed here (the caller passes `1 + max`)."""
    t = effective(template)
    why = validate(t)
    if why:
        raise BranchNameError("INVALID_TEMPLATE", why)
    if kind not in KINDS:
        raise BranchNameError("MISSING_REQUIRED_VALUE", "kind must be one of %s" % ", ".join(KINDS))
    if not re.fullmatch(r"[0-9]+", str(n)):
        raise BranchNameError("MISSING_REQUIRED_VALUE", "n must be an issue number")
    values = {"{kind}": kind, "{n}": str(n)}
    if "{type}" in t:
        tv = FIXED_TYPE.get(kind) or (type or "").strip()
        if not tv:
            raise BranchNameError("MISSING_REQUIRED_VALUE",
                                  "{type}: the issue's `type:` label is needed for a %s branch"
                                      % kind)
        values["{type}"] = tv
    if "{user}" in t:
        if not (user or "").strip():
            raise BranchNameError("MISSING_REQUIRED_VALUE",
                                  "{user}: branch_user or the forge login is needed")
        values["{user}"] = user.strip()
    if "{seq}" in t:
        if seq is None or not re.fullmatch(r"[1-9][0-9]*", str(seq)):
            raise BranchNameError("INVALID_SEQUENCE",
                                  "{seq}: a sequence of 1 or more is needed "
                                  "(the caller computes 1 + max)")
        values["{seq}"] = str(seq)
    return "".join(values.get(p, p) for p in pieces(t))


# ---- the patterns -------------------------------------------------------------

def _slot_re(slot, *, kind=None, n=None, type=None):
    if slot == "{kind}":
        return re.escape(kind) if kind else "(?P<kind>%s)" % "|".join(KINDS)
    if slot == "{type}":
        if kind in FIXED_TYPE:
            return re.escape(FIXED_TYPE[kind])
        if type:
            return re.escape(type)
        return "(?P<type>[^/]+)"
    if slot == "{user}":
        return "(?P<user>[^/]+)"
    if slot == "{n}":
        return re.escape(str(n)) if n is not None else "(?P<n>[0-9]+)"
    if slot == "{seq}":
        return "(?P<seq>[0-9]+)"
    return None


def pattern_for_kind(template, kind, *, n=None, type=None):
    """The regex a branch of `kind` matches under `template`; `n=None`
    leaves the issue number as a group. An invalid template compiles to a
    pattern that matches nothing — it enforces nothing rather than
    everything (the hooks' rule)."""
    t = effective(template)
    if validate(t) or kind not in KINDS:
        return re.compile(r"(?!)")
    parts = [_slot_re(p, kind=kind, n=n, type=type) if p.startswith("{") else re.escape(p)
             for p in pieces(t)]
    if kind not in FIXED_TYPE and not type and "{type}" in t:
        # feat / fast with no label: any type but the fixed two. The guard is
        # a lookahead over the *rest of the pattern*, so it holds whatever
        # delimiter the template uses (`{type}-{n}`, `{type}.{n}`) — codex
        # review, PR #254: `spec-5` must not bind as an implementation.
        i = pieces(t).index("{type}")
        rest = re.sub(r"\(\?P<\w+>", "(?:", "".join(parts[i + 1:]))
        parts[i] = r"(?!(?:spec|test)%s\Z)" % rest + parts[i]
    return re.compile("".join(parts) + r"\Z")


_ANY_RE = {}


def parse_branch(name, template):
    """{kind, type, user, n, seq} for a branch of any kind under `template`,
    else None. Slots the template lacks are None, except `type` for spec / qa
    (their fixed value). `kind` is `spec` / `qa`
    when the template has `{kind}` or its `{type}` reads `spec` / `test`;
    otherwise "feat|fast" — a template without `{kind}` cannot tell them
    apart (the issue's `track:` label can; that is the caller's)."""
    t = effective(template)
    if validate(t):
        return None
    if t not in _ANY_RE:
        out = ""
        for p in pieces(t):
            out += _slot_re(p) if p.startswith("{") else re.escape(p)
        _ANY_RE[t] = re.compile(out + r"\Z")
    m = _ANY_RE[t].match(name)
    if not m:
        return None
    g = m.groupdict()
    kind = g.get("kind")
    tv = g.get("type")
    if kind is None:
        kind = {"spec": "spec", "test": "qa"}.get(tv, "feat|fast")
    if tv is None and kind in FIXED_TYPE:
        tv = FIXED_TYPE[kind]          # spec / qa carry their fixed type whatever the template
    return {"kind": kind, "type": tv, "user": g.get("user"), "n": g.get("n"),
            "seq": int(g["seq"]) if g.get("seq") else None}


# ---- the remote snapshot --------------------------------------------------------

def collect_remote_heads(remote="origin", cwd=None, timeout=60):
    """One `git ls-remote --heads <remote>`: the fallible read. status is
    `observed` with the heads and each head's commit (`shas`: branch -> sha;
    a `reviewed-sha:` is compared against it — codex review, PR #254), or
    `unknown` with the reason and no heads — never an empty observed list
    standing in for a failure."""
    base = {"remote": remote, "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        p = subprocess.run(["git", "ls-remote", "--heads", remote], cwd=cwd,
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {**base, "status": "unknown", "reason": type(e).__name__, "heads": [],
                "shas": {}, "heads_sha256": None}
    if p.returncode != 0:
        return {**base, "status": "unknown",
                "reason": (p.stderr.strip().splitlines() or ["git ls-remote failed"])[-1][:200],
                "heads": [], "shas": {}, "heads_sha256": None}
    shas = {}
    for line in p.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            shas[ref[len("refs/heads/"):]] = sha.strip()
    return {**base, **_heads_fields(shas)}


def _heads_fields(shas):
    heads = sorted(shas)
    lines = "\n".join("%s %s" % (shas[h] or "", h) for h in heads)
    return {"status": "observed", "heads": heads, "shas": dict(sorted(shas.items())),
            "heads_sha256": hashlib.sha256(lines.encode("utf-8")).hexdigest()}


def snapshot_from_heads(heads, remote="origin"):
    """A snapshot from heads already in hand — a branch -> sha mapping, or a
    bare list of names (sha unknown: None)."""
    shas = dict(heads) if isinstance(heads, dict) else {h: None for h in heads}
    return {"remote": remote, "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **_heads_fields(shas)}


# ---- Lookup -----------------------------------------------------------------------

def match_heads(snapshot, template, *, kind, n, type=None):
    """Every remote head of `kind` for issue `n`, sorted by (seq, name), each
    with its parsed `{user}` / `{seq}`, and the outcome. Facts only: no
    "live" attempt is chosen."""
    if snapshot.get("status") != "observed":
        return {"outcome": "UNKNOWN", "matches": [], "reason": snapshot.get("reason")}
    pat = pattern_for_kind(template, kind, n=n, type=type)
    found = []
    for h in snapshot.get("heads", []):
        m = pat.match(h)
        if m:
            g = m.groupdict()
            found.append({"branch": h, "user": g.get("user"),
                          "seq": int(g["seq"]) if g.get("seq") else None,
                          "sha": (snapshot.get("shas") or {}).get(h)})
    found.sort(key=lambda x: (x["seq"] if x["seq"] is not None else 0, x["branch"]))
    if not found:
        outcome = "NO_MATCH"
    elif len(found) == 1:
        outcome = "ONE"
    else:
        seqs = [x["seq"] for x in found]
        outcome = "MULTIPLE_SAME_SEQ" if len(set(seqs)) < len(seqs) else "MULTIPLE_SEQ"
    return {"outcome": outcome, "matches": found}


def kinds_for(track):
    return ("spec", "feat", "qa") if track == "spec" else ("fast",) if track == "fast" else KINDS


def match_issue(snapshot, template, n, *, track=None, type=None):
    return {k: match_heads(snapshot, template, kind=k, n=n, type=type) for k in kinds_for(track)}


# ---- the local keys -----------------------------------------------------------------

def local_key(tops, key):
    """A local key from bin/roz-config's file — the first toplevel that holds
    the key wins: a stored "" is a chosen default (→ None); a file without
    the key passes to the next (guard_acceptance's rule, PR #169)."""
    for top in tops:
        if not top:
            continue
        try:
            with open(os.path.join(top, LOCAL_FILE), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and key in data:
            v = data[key]
            return v.strip() if isinstance(v, str) and v.strip() else None
    return None
