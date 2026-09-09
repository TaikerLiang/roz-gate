#!/usr/bin/env python3
"""Lint tier of the eval ledger — static checks on the plugin's own sources.

Every case here guards against failure mode 2: the RULE ITSELF is broken,
so every stage faithfully executes it and reports green. Cases that guard
a runtime check (a grep the model executes from prose) get two layers:
  pattern proof — the canonical pattern, held here, runs against fixtures;
  source conformance — the prose must carry that same pattern verbatim.
Either layer alone is a hole: pattern-only proves a pattern nobody ships;
conformance-only ships an unproven pattern. See evals/README.md.

Ported one-to-one from run-lint.sh (bash). The language is a design
constraint, not a preference: the suite's owner reads Python, not shell
(evals/README.md § Language). Stdlib-only; runs on every push.
"""

import os
import re
import sys

S = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(S))
FX = os.path.join(S, "fx")

sys.path.insert(0, os.path.dirname(S))  # evals/
from lib.checkkit import Checker  # noqa: E402


class Lint(Checker):
    """The lint tier's line format: PASS/FAIL plus a summary count."""

    def ok(self, desc):
        print("PASS %s" % desc)

    def fail(self, desc, detail):
        print("FAIL %s — %s" % (desc, detail))

    def finish(self):
        print()
        print("%d passed, %d failed" % (self.passed, self.fails))
        sys.exit(0 if self.fails == 0 else 1)


c = Lint()


def read(relpath):
    with open(os.path.join(R, relpath), encoding="utf-8") as f:
        return f.read()


def fixture(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return f.read()


def dir_files(*reldirs):
    for d in reldirs:
        for base, _, names in os.walk(os.path.join(R, d)):
            for n in sorted(names):
                yield os.path.join(base, n)


def dirs_text(*reldirs):
    out = []
    for p in dir_files(*reldirs):
        with open(p, encoding="utf-8") as f:
            out.append(f.read())
    return "\n".join(out)


def must_match(name, pattern, text):
    """The pattern (regex, MULTILINE) must occur — grep must succeed."""
    c.expect("pattern", name, re.search(pattern, text, re.M) is not None)


def must_not_match(name, pattern, text):
    """The pattern must NOT occur — the near-miss / anti-pattern layer."""
    c.expect("pattern", name, re.search(pattern, text, re.M) is None)


def src(name, relpath, literal):
    """Source conformance: the file carries the literal byte-for-byte."""
    if literal in read(relpath):
        c.passed += 1
        c.ok(name)
    else:
        c.fails += 1
        c.fail(name, "%s lacks the literal: %s" % (relpath, literal))


def section(text, start_re, end_re):
    """awk '/start/,/end/' — start line through end-marker line inclusive."""
    lines = text.splitlines()
    out, active = [], False
    for ln in lines:
        if not active and re.search(start_re, ln):
            active = True
        if active:
            out.append(ln)
            if out[:-1] and re.search(end_re, ln):
                break
    return "\n".join(out)


# ---------------------------------------------------------------------------
# B1 · a compound tag evades the literal it contains        (defect: 1.12.0-)
# Canonical unverified-claim pattern: tag position = start of line (a wrap
# continuation) or after ( or , (its own tag, or illegally merged into one).
UNV = r"(^|[(,])[ \t]*unverified"
must_match("B1 pattern: compound (from Q4, unverified) found",
           UNV, fixture("b1_compound.md"))
must_match("B1 pattern: conventional (unverified) found",
           UNV, fixture("b1_plain.md"))
must_match("B1 pattern: wrap-split compound found",
           UNV, fixture("b1_wrapped.md"))
must_not_match("B1 pattern: the word in prose NOT flagged",
               UNV, fixture("b1_negative.md"))
src("B1 conformance: Path B check carries the widened pattern",
    "commands/next-stage.md", "grep -nE '(^|[(,])[[:space:]]*unverified'")
src("B1 conformance: promote check carries the widened pattern",
    "commands/spec-answers.md", "grep -nE '(^|[(,])[[:space:]]*unverified'")
c.expect("pattern", "B1 conformance: no site still greps only the old literal",
         "grep -n '(unverified)'" not in dirs_text("commands", "references"))

# ---------------------------------------------------------------------------
# B2 · a line-wrapped tag survives the check                (defect: 1.12.0-)
# Checks match the OPENING TOKEN only; a wrapped tag is present, never absent.
c.expect("pattern", "B2 pattern: wrapped (assumed-empirical: detected",
         "(assumed-empirical:" in fixture("b2_wrapped_assumed.md"))
c.expect("pattern", "B2 pattern: wrapped (measured read as present",
         "(measured" in fixture("b2_wrapped_measured.md"))
# The anti-pattern this rule forbids — requiring the closing paren on the
# same line — misses exactly the wrapped tag. Kept as executable rationale.
# ([^)\n]: grep is line-scoped; Python's [^)] would cross the wrap and
# defeat the very subtlety this check demonstrates.)
must_not_match("B2 rationale: same-line-paren matching would miss it",
               r"\(measured[^)\n]*\)", fixture("b2_wrapped_measured.md"))
src("B2 conformance: the opening-token rule names all three tokens",
    "commands/next-stage.md", "`(unverified)`, `(assumed-empirical:`, `(measured`")
src("B2 conformance: opening-token-only is stated as the rule",
    "commands/next-stage.md", "matches the **opening token only**")

# ---------------------------------------------------------------------------
# B3 · the marker convention is identical everywhere        (preventive)
# Canonical marker literals: '**[' (agent write opens) and '✅ [' (resolution).
# The sentences stating the convention legitimately differ; the LITERALS may
# not. Near-miss variants (no space, fullwidth bracket) must not exist.
for f in ("commands/next-stage.md", "commands/patrol.md",
          "commands/spec-answers.md", "commands/review-answers.md"):
    src("B3: %s carries the '**[' marker literal" % f, f, "**[")
for f in ("commands/patrol.md", "commands/spec-answers.md",
          "commands/review-answers.md"):
    src("B3: %s carries the '✅ [' marker literal" % f, f, "✅ [")
B3_DIRS = ("commands", "references", "agents", "templates")
c.expect("pattern", "B3: no '✅[' (missing space) anywhere",
         "✅[" not in dirs_text(*B3_DIRS))
must_not_match("B3: no fullwidth-bracket marker variant anywhere",
               r"✅ ?【|\*\*【", dirs_text(*B3_DIRS))

# ---------------------------------------------------------------------------
# B4 · an agent write never opens with a quote block        (defect: 1.11.0-)
# Static layer: the write rules must be stated where writes happen. Teeth
# since 1.14.0: guard-gate rule C denies the quote-opening marker-carrying
# comment itself (proven in hooks/tests/run-tests.sh, run by the same
# release gate).
src("B4: question comments must open with the marker",
    "commands/next-stage.md", "MUST start with `**[")
src("B4: the quote-block opening is forbidden in review replies",
    "commands/review-answers.md", "Never open with a quote block")

# ---------------------------------------------------------------------------
# C3 · `processing` coexists with a phase label             (preventive)
# Oracle (patrol.md's coexistence sentence, executable): `processing` is a
# mutex; all other `status:` labels are phases, at most one at a time.
MUTEX = "processing"
PHASES = ("ready-for-spec", "in-spec-review", "ready-for-dev",
          "in-user-review", "blocked")
TRACKS = ("spec", "fast")


def legal(labels):
    """Space-separated status label names -> True legal / False illegal."""
    n = 0
    for l in labels.split():
        if l == MUTEX:
            continue
        if l not in PHASES:
            return False
        n += 1
    return n <= 1


c.expect("oracle", "C3: phase + processing is legal (a stale pair names the death stage)",
         legal("in-spec-review processing"))
c.expect("oracle", "C3: two phase labels are illegal",
         not legal("in-spec-review in-user-review"))
c.expect("oracle", "C3: an unknown status label is illegal",
         not legal("shipping"))
# Completeness — the drift alarm: every backticked label literal in the
# sources must be in the oracle, or the suite goes red on the new label.
label_text = dirs_text("commands", "references", "templates", "agents")
drift = []
for m in sorted(set(re.findall(r"`status: ([a-z-]+)`", label_text))):
    if m not in PHASES and m != MUTEX:
        drift.append("`status: %s`" % m)
for m in sorted(set(re.findall(r"`track: ([a-z]+)`", label_text))):
    if m not in TRACKS:
        drift.append("`track: %s`" % m)
if not drift:
    c.passed += 1
    c.ok("C3 completeness: every source label is in the oracle")
else:
    c.fails += 1
    c.fail("C3 completeness", "labels missing from the oracle: %s"
           % " ".join(drift))

# ---------------------------------------------------------------------------
# C4 · track: fast + ready-for-spec refused                 (hook-covered)
# The control case: it needs no lint because it has teeth. Enforced by
# hooks/guard-gate and proven in hooks/tests/run-tests.sh ("gate label add
# blocked"), which the same release gate runs. Nothing to check here.
c.passed += 1
c.ok("C4: covered by guard-gate (see hooks/tests/run-tests.sh, run by the same gate)")

# ---------------------------------------------------------------------------
# C6 · CR lookup sees merged CRs where it must              (defect: 1.11.0-)
gh_crfind = "\n".join(l for l in read("references/forge-github.md").splitlines()
                      if "CR-FIND" in l)
gl_crfind = "\n".join(l for l in read("references/forge-gitlab.md").splitlines()
                      if "CR-FIND" in l)
c.expect("pattern", "C6: github adapter CR-FIND documents --state all for merged CRs",
         "--state all" in gh_crfind)
c.expect("pattern", "C6: gitlab adapter CR-FIND documents --all for merged MRs",
         "--all" in gl_crfind)
src("C6: the post-integration detection path cites the all-states form",
    "commands/spec-answers.md", "all-states form")
inflight = "\n".join(l for l in read("commands/patrol.md").splitlines()
                     if "no `status:`, `track: spec`" in l)
must_not_match("C6: patrol's in-flight row keeps the open-only default",
               r"all-states|--state all|--all\b", inflight)

# ---------------------------------------------------------------------------
# D1 · the reviewer receives the claim it reviews against   (defect: 1.8.0-)
b5 = section(read("commands/next-stage.md"), r"^### B5\. ", r"^### B5b\. ")
c.expect("pattern", "D1: stage-(5) dispatch attaches spec.md",
         "spec.md" in b5)
c.expect("pattern", "D1: stage-(5) dispatch attaches technical-spec.md",
         "technical-spec.md" in b5)
c.expect("pattern", "D1: attachment is stated as receiving the claim, not inferring it",
         "inference of intent" in b5)

# ---------------------------------------------------------------------------
# E3 · the implementer can stop and ask at stage (3)        (defect: 1.12.0-)
b3 = section(read("commands/next-stage.md"), r"^### B3\. Dispatch", r"^### B4\. ")
c.expect("pattern", "E3: stage-(3) dispatch states the contract-gap stop route",
         "A contract gap you cannot resolve" in b3)
c.expect("pattern", "E3: unilateral in-code decisions are forbidden explicitly",
         "never decide unilaterally" in b3)

# ---------------------------------------------------------------------------
# E4 · the stage-(5) reviewer has the same route            (defect: 1.12.0-)
c.expect("pattern", "E4: a contract-ambiguity finding routes to the spec CR",
         "contract ambiguity routes to a spec-CR" in b5)
c.expect("pattern", "E4: reviewer-to-implementer settlement is forbidden explicitly",
         "never settled" in b5)

c.finish()
