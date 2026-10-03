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

import json
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
# comment itself (proven in hooks/tests/, run by the same
# release gate).
src("B4: question comments must open with the marker",
    "commands/next-stage.md", "MUST start with `**[")
src("B4: the quote-block opening is forbidden in review replies",
    "commands/review-answers.md", "Never open with a quote block")

# ---------------------------------------------------------------------------
# E2 · a question left behind in the source document        (defect: 1.14.2-)
# The first opus baseline: A6 said "relocate it verbatim", 5/5 runs copied;
# the prose was made explicit ("move … delete it from the source document"),
# 5/5 runs still left the section behind (F3 the same). Teeth since 1.15.0:
# guard-gate rule D denies the commit. Three holders of ONE predicate — the
# hook, the E2 replay checker, and this proof — kept byte-identical here;
# then the repo's own specs tree is swept as the push-time backstop
# (web-UI edits, --no-verify, a hook-less client — a client-side hook binds
# this agent, this lint binds this push; neither binds the repository).
# Heading-only by design: "TBD"/"open:" items are ordinary prose too often
# to deny on (see the e2_clean fixture); the section heading is the shape
# every observed miss took.
OPEN_Q = "^#+ .*open questions"
must_match("E2 pattern: an open-questions section heading is detected",
           "(?i)" + OPEN_Q, fixture("e2_section.md"))
must_match("E2 pattern: a heading kept as a pointer-only section still counts",
           "(?i)" + OPEN_Q, fixture("e2_pointer_section.md"))
must_not_match("E2 pattern: a pointer line under another heading / prose mention NOT flagged",
               "(?i)" + OPEN_Q, fixture("e2_clean.md"))
src("E2 conformance: guard-gate rule D carries the predicate literal",
    "hooks/guard_gate.py", OPEN_Q)
src("E2 conformance: the E2 replay checker carries the same literal",
    "evals/replay/cases/E2/check.py", OPEN_Q)
src("E2 conformance: A6 prose states the move AND names the enforcement",
    "commands/next-stage.md", "delete it from the source document")
src("E2 conformance: A6 prose names guard-gate as the enforcement",
    "commands/next-stage.md", "guard-gate denies the commit")


def specs_dir():
    """This repo's specs_dir: from its CLAUDE.md config block, else the
    documented default — the same resolution the hook applies."""
    try:
        text = read("CLAUDE.md")
    except OSError:
        return "docs/specs"
    m = re.search(r"^-\s*specs_dir:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("`") if m else "docs/specs"


left_behind = []
for base, _, names in os.walk(os.path.join(R, specs_dir())):
    if "technical-spec.md" in names:
        with open(os.path.join(base, "technical-spec.md"), encoding="utf-8") as f:
            if re.search("(?i)" + OPEN_Q, f.read(), re.M):
                left_behind.append(os.path.relpath(base, R))
c.expect("hook rule D, push-time backstop",
         "E2 backstop: no technical-spec.md under %s carries an open-questions "
         "section%s" % (specs_dir(), "" if not left_behind
                        else " — left behind in: " + ", ".join(left_behind)),
         not left_behind)

# ---------------------------------------------------------------------------
# D2 · the fidelity dispatch is blind by topology           (defect: 1.15.0-)
# First opus baseline, 4/5: one QA child ran `cat src/app.txt` under the
# fidelity dispatch — the prose "Do NOT read src/" was the only guard and a
# GREEN looks identical either way. Teeth since 1.16.0: guard-blind rule E,
# ON while the dispatching command's marker exists. The predicate is the D2
# replay checker's three regexes; the hook carries them byte-identical, and
# this case proves it by extracting each `NAME = re.compile(...)` block
# from the checker and requiring the same text in the hook — then runs the
# hook's own predicate against the shapes that matter.
import importlib.util  # noqa: E402

D2_CHECK = read("evals/replay/cases/D2/check.py")
D2_HOOK = read("hooks/guard_blind.py")
for name in ("GIT_TOUCH", "SRC_PATH", "SRC_EXCLUDED", "SRC_MENTIONED"):
    m = re.search(r"^%s = re\.compile\((?:.|\n)*?\)\n" % name, D2_CHECK, re.M)
    if not m:
        c.fails += 1
        c.fail("D2 conformance: %s block found in the replay checker" % name,
               "evals/replay/cases/D2/check.py lacks `%s = re.compile(...)`" % name)
        continue
    src("D2 conformance: guard-blind carries the checker's %s byte-for-byte" % name,
        "hooks/guard_blind.py", m.group(0))
_spec = importlib.util.spec_from_file_location("guard_blind",
                                               os.path.join(R, "hooks/guard_blind.py"))
_gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gb)
c.expect("hook rule E (D2 run-4's exact command)",
         "D2 pattern: `… && cat src/app.txt` is a read of src/",
         _gb.violation("Bash", {"command": "git status --short && git rev-parse --abbrev-ref HEAD"
                                           " && cat src/app.txt"}) is not None)
c.expect("hook rule E", "D2 pattern: `git checkout feat/5` is a feat/ touch",
         _gb.violation("Bash", {"command": "git checkout feat/5"}) is not None)
c.expect("hook rule E", "D2 pattern: a Read of an absolute src/ path is a read",
         _gb.violation("Read", {"file_path": "/tmp/work/src/app.txt"}) is not None)
c.expect("hook rule E (exclusion is not a touch)",
         "D2 pattern: `grep -v '^src/'` and `':!src/**'` are NOT reads",
         _gb.violation("Bash", {"command": "git ls-files | grep -v '^src/'"}) is None
         and _gb.violation("Bash", {"command": "git grep -n price -- ':!src/**'"}) is None)
c.expect("hook rule E (mention is not use, third form)",
         "D2 pattern: src/ inside an echo string next to a blanked ':!src/**' is NOT a read",
         _gb.violation("Bash", {"command":
                                "git ls-files"
                                " && echo \"--- grep fixtures (tracked files, excluding src/)\""
                                " && git grep -n -E 'expires' -- ':!src/**'"
                                " ; echo \"--- diff of fix\""
                                " && git show e61367c -- tests/acceptance/"}) is None
         and _gb.violation("Bash", {"command": "# src/ is off-limits here\ncat tests/x"}) is None)
c.expect("hook rule E (echo is a command, never an argument)",
         "D2 pattern: `grep echo src/app.txt` and `printf_helper src/x` are reads",
         _gb.violation("Bash", {"command": "grep echo src/app.txt"}) is not None
         and _gb.violation("Bash", {"command": "grep -n echo src/a.py"}) is not None
         and _gb.violation("Bash", {"command": "printf_helper src/x"}) is not None)
c.expect("hook rule E (echo in command position)",
         "D2 pattern: `FOO=1 echo src/ && ls` and `ls && echo src/ | cat` are NOT reads",
         _gb.violation("Bash", {"command": "FOO=1 echo src/ && ls"}) is None
         and _gb.violation("Bash", {"command": "ls && echo src/ | cat"}) is None
         and _gb.violation("Bash", {"command": "echo \"excluding src/\" && ls tests"}) is None)
c.expect("hook rule E", "D2 pattern: a read after an echo mention is still a read",
         _gb.violation("Bash",
                       {"command": "echo \"excluding src/\" && cat src/app.txt"}) is not None)
src("D2 conformance: the checker pairs denials by guard-blind's own message literal",
    "evals/replay/cases/D2/check.py", "Roz Gate: blocked — this is a fidelity dispatch")
src("D2 conformance: guard-blind's deny message opens with that literal",
    "hooks/guard_blind.py", "Roz Gate: blocked — this is a fidelity dispatch")
c.expect("hook rule E", "D2 pattern: qa/<n> work (tests/, spec docs) is untouched",
         _gb.violation("Bash", {"command": "cat tests/acceptance/test_expiry.py"
                                           " docs/specs/5/spec.md"}) is None
         and _gb.violation("Read",
                           {"file_path": "/tmp/work/docs/specs/5/technical-spec.md"}) is None)
src("D2 conformance: B5b states the fidelity-dispatch procedure (marker on)",
    "commands/next-stage.md", "roz-gate/fidelity-dispatch")
src("D2 conformance: patrol's address-review cites the procedure",
    "commands/patrol.md", "fidelity-dispatch procedure")
src("D2 conformance: the fidelity brief names the enforcement",
    "references/fidelity-brief.md", "guard-blind")
src("D2 conformance: hooks.json wires guard-blind on Bash|Read|Glob|Grep",
    "hooks/hooks.json", '"matcher": "Bash|Read|Glob|Grep"')

# ---------------------------------------------------------------------------
# C7 · a branch is cut only from a base the remote has         (defect: 1.18.0-)
#      Issue #38: the base is config default_branch at every site, and a
#      base the remote lacks stops the cut instead of cutting from nothing.
_ns = read("commands/next-stage.md")
_a2 = section(_ns, r"^### A2\. Branch", r"^### A3\. ")
_c2 = section(_ns, r"^### C2\. Branch", r"^### C3\. ")
for _nm, _blk in (("A2", _a2), ("C2", _c2)):
    c.expect("pattern", "C7: %s cuts from `<default_branch>`" % _nm,
             "from `<default_branch>`" in _blk)
    c.expect("pattern", "C7: %s prunes stale tracking refs before the check" % _nm,
             "git fetch --prune" in _blk)
    c.expect("pattern", "C7: %s verifies the base exists on the remote before cutting" % _nm,
             "git rev-parse --verify -q origin/<default_branch>" in _blk)
    c.expect("pattern", "C7: %s stops when the base is missing" % _nm,
             "**STOP**" in _blk)
src("C7: A5 targets `<default_branch>`", "commands/next-stage.md",
    "CR-OPEN from `spec/<n>` targeting `<default_branch>`")
src("C7: C5 targets `<default_branch>`", "commands/next-stage.md",
    "CR-OPEN from `fast/<n>` targeting `<default_branch>`")
src("C7: C6 diffs against `<default_branch>`", "commands/next-stage.md",
    "git diff <default_branch>...fast/<n>")
src("C7: integrate merges `<default_branch>` in", "commands/integrate.md",
    "git merge --no-edit <default_branch>")
for _f in ("commands/next-stage.md", "commands/integrate.md"):
    c.expect("pattern", "C7: %s names no literal trunk as a base" % _f,
             re.search(r"from `(main|master)`|--base (main|master)\b|targeting `(main|master)`",
                       read(_f)) is None)

# ---------------------------------------------------------------------------
# C9 · a command's git work lives in a worktree it removes on every exit
#      (defect: 1.19.0-) Issue #37: a scheduled patrol fires while the user is
#      mid-edit on the checkout; commands used to checkout/merge/reset there.
_wt = "roz-gate/wt/"
_wf = read("references/workflow.md")
c.expect("pattern", "C9: workflow.md states the workspace rule (the worktree is the surface)",
         "entire\nworking surface is a linked worktree" in _wf and _wt in _wf)
c.expect("pattern", "C9: workflow.md names scheduled patrol as the motivating case",
         "scheduled patrol fires" in _wf)
c.expect("pattern", "C9: the STOP protocol's first obligation is removing the worktree",
         "(1) remove the command's worktree(s)" in _wf)
_ns = read("commands/next-stage.md")
for _nm, _s, _e in (("A2", r"^### A2\. Branch", r"^### A3\. "),
                    ("B2", r"^### B2\. ", r"^### B3\. "),
                    ("C2", r"^### C2\. Branch", r"^### C3\. ")):
    c.expect("pattern", "C9: next-stage %s cuts into a worktree under %s" % (_nm, _wt),
             "git worktree add" in section(_ns, _s, _e) and _wt in section(_ns, _s, _e))
for _nm, _s, _e in (("A6c", r"^### A6c\. ", r"^### A7\. "),
                    ("B6", r"^### B6\. ", r"^---$"),
                    ("C7", r"^### C7\. ", r"^---$")):
    c.expect("pattern", "C9: next-stage %s (Done) removes the worktree" % _nm,
             "git worktree remove --force" in section(_ns, _s, _e))
src("C9: next-stage's STOP removes every worktree the run created",
    "commands/next-stage.md", "`git worktree remove --force` every\nworktree this run created")
_ig = read("commands/integrate.md")
c.expect("pattern", "C9: integrate merges in a spec/<n> worktree",
         "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/spec/<n> spec/<n>" in _ig)
c.expect("pattern", "C9: integrate removes the worktree on green and on STOP",
         _ig.count("git worktree remove --force") >= 2)
src("C9: integrate's safety invariant: the user's checkout is untouchable",
    "commands/integrate.md", "the user's checkout is **untouchable**")
src("C9: spec-answers folds in a worktree", "commands/spec-answers.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/spec/<n> spec/<n>")
src("C9: spec-answers' STOP removes the worktree", "commands/spec-answers.md",
    "`git worktree remove --force` the `spec/<n>` worktree")
_sa = read("commands/spec-answers.md")
c.expect("pattern", "C9: spec-answers keeps the worktree through step 7's hand-back run",
         "Keep the worktree" in section(_sa, r"^## 6\. ", r"^## 6b\. ")
         and "git worktree remove --force" in section(_sa, r"^## 7\. ", r"^## 8\. "))
for _f in ("commands/integrate.md", "commands/spec-answers.md"):
    c.expect("pattern", "C9: %s's STOP removes only a worktree this run created" % _f,
             re.search(r"[Ii]f this run created", read(_f)) is not None)
src("C9: review-answers commits in a worktree of the CR's branch", "commands/review-answers.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>")
src("C9: patrol's address-review dispatches work in worktrees", "commands/patrol.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>")
c.expect("pattern", "C9: patrol runs no git at all (its scan is forge calls)",
         re.search(r"`git (checkout|switch|reset|stash|merge|fetch) ",
                   read("commands/patrol.md")) is None)
for _f in ("commands/next-stage.md", "commands/integrate.md", "commands/spec-answers.md",
           "commands/review-answers.md", "commands/patrol.md"):
    c.expect("pattern", "C9: %s never instructs a checkout/switch/reset/stash in the user's tree"
             % _f,
             re.search(r"git (checkout|switch|reset|stash|merge --abort)\b|^- Checkout `",
                       read(_f), re.M) is None)
src("C9: hooks/README says which git dir the marker uses", "hooks/README.md",
    "`git rev-parse --git-common-dir`")

# ---------------------------------------------------------------------------
# J1 · the judgment fixtures are frozen at T                (preventive)
# Contamination is that tier's whole game: every forge comment after the
# question's timestamp contains the answer. materialize.py's check runs
# here on every push so a re-materialization (or a hand edit) that lets a
# later comment in goes red before it can score a run. Red-proofed by
# planting one post-T comment (names fixture, issue, comment id). The
# blindness files must exist and be complete before any recorded run.
sys.path.insert(0, os.path.join(R, "evals", "judgment"))
from materialize import check_frozen  # noqa: E402

_frozen_bad = check_frozen(os.path.join(R, "evals", "judgment", "cases"))
c.expect("judgment/materialize.py check_frozen",
         "J1: every judgment fixture's forge state is frozen at its T%s"
         % ("" if not _frozen_bad else " — " + "; ".join(_frozen_bad)), not _frozen_bad)
_crit = json.loads(read("evals/judgment/criteria.json"))
c.expect("judgment/criteria.json", "J1: all seven corpus items have a criterion",
         all(k in _crit for k in ("P1", "P2", "P8", "P12", "N1", "N5", "N10")))
src("J1: the judge prompt carries the criterion slot",
    "evals/judgment/judge-prompt.md", "{criterion}")
src("J1: the judge prompt carries the document slot",
    "evals/judgment/judge-prompt.md", "{document}")

# ---------------------------------------------------------------------------
# L1 · one stage map                                        (preventive)
# The loop diagram is ONE file, images/loop-stage-map.svg, inlined by the
# Pages site (and the learner page when it lands) between SVG markers — a
# second copy of the loop's shape is the B3 defect class. Red-proofed by
# editing one character of the inlined copy.
_svg = read("images/loop-stage-map.svg").strip("\n")
for _page in ("docs/index.html", "docs/onboarding.html"):
    _m = re.search(r"<!-- SVG:images/loop-stage-map\.svg -->\n(.*?)\n<!-- /SVG -->",
                   read(_page), re.S)
    c.expect("images/loop-stage-map.svg is the one loop diagram",
             "L1: %s inlines images/loop-stage-map.svg byte-for-byte" % _page,
             _m is not None and _m.group(1) == _svg)

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
    for lab in labels.split():
        if lab == MUTEX:
            continue
        if lab not in PHASES:
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
# hooks/guard-gate and proven in hooks/tests/test_guard_gate.py ("gate label
# add blocked"), which the same release gate runs. Nothing to check here.
c.passed += 1
c.ok("C4: covered by guard-gate (see hooks/tests/test_guard_gate.py, run by the same gate)")

# ---------------------------------------------------------------------------
# C6 · CR lookup sees merged CRs where it must              (defect: 1.11.0-)
gh_crfind = "\n".join(line for line in read("references/forge-github.md").splitlines()
                      if "CR-FIND" in line)
gl_crfind = "\n".join(line for line in read("references/forge-gitlab.md").splitlines()
                      if "CR-FIND" in line)
c.expect("pattern", "C6: github adapter CR-FIND documents --state all for merged CRs",
         "--state all" in gh_crfind)
c.expect("pattern", "C6: gitlab adapter CR-FIND documents --all for merged MRs",
         "--all" in gl_crfind)
src("C6: the post-integration detection path cites the all-states form",
    "commands/spec-answers.md", "all-states form")
inflight = "\n".join(line for line in read("commands/patrol.md").splitlines()
                     if "no `status:`, `track: spec`" in line)
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

# ---------------------------------------------------------------------------
# L2 · the config keys patrol reads are the ones /roz-gate:config offers and
#      README documents — a key documented in one place and read nowhere is a
#      silent no-op                                           (defect: 1.18.0)
_cfg = read("commands/config.md")
_pat = read("commands/patrol.md")
_rd = read("README.md")
for _k in ("inbox_label", "inbox_assignee", "patrol_model"):
    src("L2: /roz-gate:config offers %s" % _k, "commands/config.md", "`%s`" % _k)
    src("L2: patrol reads %s" % _k, "commands/patrol.md", "`%s`" % _k)
    src("L2: README config block documents %s" % _k, "README.md", "- %s:" % _k)
c.expect("pattern", "L2: a filtered-out issue is counted, never acted on",
         "not in the inbox filter" in _pat
         and re.search(r"never\s+commented on, never locked, never listed", _pat) is not None)
c.expect("pattern", "L2: the filter is inbox-only — track: issues advance regardless",
         "The filter applies to the inbox alone" in _pat)
c.expect("pattern", "L2: config never creates forge labels",
         "never create forge labels" in _cfg)
c.expect("pattern", "L2: config never clears a required key",
         "never clear\na required key" in _cfg or "never clear a required key" in _cfg)
src("L2: GitHub ISSUE-LIST returns assignees (the inbox filter reads them)",
    "references/forge-github.md", "--json number,title,labels,assignees,createdAt")
for _f in ("references/forge-github.md", "references/forge-gitlab.md"):
    src("L2: %s defines LABEL-LIST" % _f, _f, "| LABEL-LIST |")

c.finish()
