"""guard-gate (Bash): rules A-D, F-H. See hooks/README.md for each rule's predicate.

A case table is (name, command) for allowed cases and (name, command,
stderr substring) for denied ones.
"""

import subprocess

from hooktest import HookTest, config_block

SUMMARY_CMD = '''gh issue comment 54 --body "**[intake] · summary**

**Story** — As a user, I want ..."'''


class FastPath(HookTest):
    """Unrelated commands never reach Python, and never touch the forge."""

    guard = "guard-gate"

    ALLOWED = [
        ("unrelated command passes prefilter", "ls -la && git status"),
        ("plain issue comment passes", 'gh issue comment 54 --body "thanks, will do"'),
    ]

    def test_allowed(self):
        for name, cmd in self.ALLOWED:
            with self.case(name):
                self.assertAllowed(self.bash(cmd))

    def test_questions_batch_needs_no_api(self):
        with self.case("questions batch allowed (no API call)"):
            result = self.bash(r'''gh issue comment 54 --body "**[intake]**

3 questions — when it settles the assignee comments \`summary\`.

**Q1 · Scope** ..."''')
            self.assertAllowed(result)
        with self.case("questions batch made no API call"):
            self.assertEqual(self.api_calls(), [])


class RuleB_GateLabelsAreHumanOnly(HookTest):
    guard = "guard-gate"

    DENIED = [
        ("gate label add blocked (gh)",
         'gh issue edit 5 --add-label "status: ready-for-spec"', "gate labels"),
        ("gate label add blocked (gh, =form)",
         'gh issue edit 5 --add-label="status: ready-for-dev"', "gate labels"),
        ("gate label add blocked (glab)",
         'glab issue update 5 --label "status::ready-for-dev"', "gate labels"),
        ("untokenizable: adding a gate label is still denied",
         'gh issue edit 73 --add-label "status: ready-for-dev" && '
         "gh issue comment 73 --body-file - <<'EOF'\nDon't wait.\nEOF", "gate labels"),
        ("untokenizable: the =form is still denied",
         'gh issue edit 73 --add-label="ready-for-spec" && '
         "gh issue comment 73 --body-file - <<'EOF'\nDon't wait.\nEOF", "gate labels"),
        ("untokenizable: a \\-newline continuation before the value is still denied "
         "(codex, PR #100)",
         'gh issue edit 73 --add-label \\\n   "status: ready-for-dev" && '
         "gh issue comment 73 --body-file - <<'EOF'\nDon't wait.\nEOF", "gate labels"),
        ("untokenizable: a tab before the value is still denied",
         'gh issue edit 73 --add-label\t"status: ready-for-dev" && '
         "gh issue comment 73 --body-file - <<'EOF'\nDon't wait.\nEOF", "gate labels"),
        ("untokenizable: glab update --label is still denied",
         'glab issue update 73 --label "status::ready-for-dev" && '
         'glab issue note 73 --message "x" <<\'EOF\'\nDon\'t wait.\nEOF', "gate labels"),
    ]
    ALLOWED = [
        ("gate label remove allowed",
         'gh issue edit 5 --remove-label "status: ready-for-spec" --add-label "track: spec"'),
        ("glab list filter allowed",
         'glab issue list --label "status::ready-for-spec" --output json'),
        ("gh list filter allowed",
         'gh issue list --label "status: ready-for-spec" --json number'),
        ("label create allowed (init)",
         'gh label create "status: ready-for-spec" --color 0e8a16 --description "gate"'),
        # #94: an untokenizable command (an apostrophe in a heredoc body) used
        # to be judged on "both halves anywhere" — the STOP protocol's own swap
        # beside its comment was denied. The fallback judges the add value.
        ("untokenizable: the STOP swap + a heredoc body with an apostrophe allowed",
         'gh issue edit 73 --remove-label "status: ready-for-dev" --add-label "status: blocked" && '
         "gh issue comment 73 --body-file - <<'EOF'\n**[next-stage] · blocked**\n"
         "B5b didn't finish; the reviewer stopped.\nEOF"),
        ("untokenizable: a remedy text naming the gate label is not an add",
         'gh issue edit 73 --add-label "status: blocked" && '
         "gh issue comment 73 --body-file - <<'EOF'\n**[next-stage] · blocked**\n"
         "Don't re-apply ready-for-dev; swap blocked→in-spec-review.\nEOF"),
    ]

    def test_denied(self):
        for name, cmd, says in self.DENIED:
            with self.case(name):
                self.assertDenied(self.bash(cmd), says)

    def test_allowed(self):
        for name, cmd in self.ALLOWED:
            with self.case(name):
                self.assertAllowed(self.bash(cmd))


class RuleC_MarkerCommentNeverOpensWithAQuote(HookTest):
    """Static rule, no API. The B4 runaway: patrol reads a quote-opening agent
    comment as a human answer and the loop replies to itself."""

    guard = "guard-gate"

    DENIED = [
        ("quote-opening readback denied",
         '''gh pr comment 12 --body "> 你說的是要在讀取時就擋掉過期的 offer

**[review] · answer**

對,規則 R4 就是這個意思。"''', "marker on line one"),
        ("whitespace-led quote still denied", '''gh issue comment 54 --body "

   > the quoted claim
**[reviewer] · question** is this measured?"''', "open with its marker"),
        ("thread-reply via gh api denied (✅ marker)",
         '''gh api -X POST "repos/o/r/pulls/12/comments/9/replies" -f body="> the finding as stated

✅ [reviewer] resolved — fixed in abc123."''', "open with its marker"),
        ("glab message form denied", '''glab issue note 7 --message "> 原本的問題

**[qa] · addressed** covered by the new fixture."''', "open with its marker"),
        ("body-file heredoc parsed and denied", '''gh pr comment 12 --body-file - <<EOF
> the quoted claim

**[review] · answer**
EOF''', "open with its marker"),
        ("unjudgeable marker-carrying body-file fails closed",
         'printf "**[qa] · x**" | gh pr comment 12 --body-file -', "cannot judge"),
        ("ANSI-C quoted body denied",
         r"gh pr comment 12 --body $'> quoted\n\n**[review] · answer**'", "open with its marker"),
        ("glued --field=body= form denied",
         '''gh api -X POST "repos/o/r/pulls/12/comments/9/replies" --field=body="> the finding

✅ [reviewer] resolved — fixed."''', "open with its marker"),
    ]
    ALLOWED = [
        ("marker first, quote below — the remedy — allowed",
         '''gh pr comment 12 --body "**[review] · answer**

> 你說的是要在讀取時就擋掉過期的 offer

對,規則 R4 就是這個意思。"'''),
        ("quote-opening body with no marker allowed (scoping)",
         '''gh pr comment 12 --body "> just quoting a teammate

agreed, merging."'''),
        ("CR body may open with a quote (comments only)",
         '''gh pr create --title t --body "> quoting the spec intro
see **[R4]** below"'''),
    ]
    # Segment splitting (1.14.1): a compound line's api -F must never be read as
    # the comment segment's --body-file (the dogfooded false positive). Glued,
    # unspaced operators: codex review on PR #2 -- token equality alone missed
    # `x=y&&gh`, reproducing the very false positive the PR fixed.
    SEGMENTS_DENIED = [
        ("semicolon-joined quote-opening comment still denied",
         '''gh pr view 12; gh pr comment 12 --body "> quoted claim

**[qa] · addressed** done."''', "open with its marker"),
        ("glued semicolon quote-opening comment still denied",
         '''gh pr view 12;gh pr comment 12 --body "> quoted claim

**[qa] · addressed** done."''', "open with its marker"),
    ]
    SEGMENTS_ALLOWED = [
        ("compound api -F + marker comment allowed",
         'gh api graphql -f query="q" -F owner=acme -F repo=demo -F pr=101 && '
         'gh issue comment 5 --body "**[intake] · note** all three channels are clean."'),
        ("pipe segment does not leak flags across the boundary",
         'gh api "repos/o/r/pulls/12/comments" -F per_page=50 | head -5 && '
         'gh issue comment 5 --body "**[review] · answer** see thread."'),
        ("glued && operator: api -F + marker comment allowed",
         'gh api graphql -f query="q" -F owner=acme&&'
         'gh issue comment 5 --body "**[intake] · note** all clean."'),
        ("glued pipe does not leak flags across the boundary",
         'gh pr list --limit 50|head -3 && '
         'gh issue comment 5 --body "**[review] · answer** done."'),
    ]

    def test_denied(self):
        for name, cmd, says in self.DENIED + self.SEGMENTS_DENIED:
            with self.case(name):
                self.assertDenied(self.bash(cmd), says)

    def test_allowed(self):
        for name, cmd in self.ALLOWED + self.SEGMENTS_ALLOWED:
            with self.case(name):
                self.assertAllowed(self.bash(cmd))

    def test_only_forge_writes_and_no_api(self):
        with self.case("non-forge command with marker+quote allowed (gh/glab only)"):
            self.assertAllowed(
                self.bash('git commit -m "> odd subject **[not a protocol write]**"'))
        with self.case("rule C made no API call"):
            self.assertEqual(self.api_calls(), [])

    def test_body_file_read_back(self):
        quoted = self.tmp / "body-quoted.md"
        quoted.write_text("> quoted claim\n\n**[review] · answer**\n")
        marker_first = self.tmp / "body-ok.md"
        marker_first.write_text("**[review] · answer**\n\n> quoted claim\n")
        with self.case("body-file read back and denied"):
            self.assertDenied(self.bash("gh pr comment 12 --body-file %s" % quoted),
                              "open with its marker")
        with self.case("body-file with marker-first body allowed"):
            self.assertAllowed(self.bash("gh pr comment 12 --body-file %s" % marker_first))


class RuleF_QuestionOptionsAreBullets(HookTest):
    """Static rule, no API. Issue #109: a (2a) thread wrote its options as
    prose; the forge renders consecutive lines as one paragraph, so the
    holder's phone showed one run-together sentence with nothing for `3a`
    to point at."""

    guard = "guard-gate"

    # The #109 thread body, verbatim.
    PROSE = """[em] · Q3 · Sort parameter semantics

The standard sort query param is accepted without error but has zero effect — WorkspaceActionLogRepoImpl hardcodes ORDER BY createdAt DESC, id DESC regardless of pageable.getSort() (same as the UserActionLogController/Repo sibling) — acceptable for this story, or does AC-6 require sort to actually work?

(a) Accept the no-op sort as consistent with existing convention; document as a known limitation, no code change this story. ← ✅ recommended (b) Extend WorkspaceActionLogRepoImpl to honor pageable.getSort(), expanding scope beyond "expose an endpoint over an existing service.\""""  # noqa: E501 — verbatim
    GOOD = """**[em] · Q3 · Sort parameter semantics**

Does AC-6 require `sort` to work, or is the no-op acceptable for this story?

- (a) Accept the no-op sort; document it as a known limitation. ← ✅ recommended
- (b) Honor `pageable.getSort()` — scope beyond "expose an endpoint".

*The sibling endpoint has the same no-op; (b) is a new feature.*"""

    DENIED = [
        ("#109's thread body verbatim — options as prose — denied",
         'gh api -X POST "repos/o/r/pulls/12/comments" -f body=\'%s\' -f commit_id=abc '
         '-f path=docs/specs/5/spec.md -F line=40 -f side=RIGHT' % PROSE.replace("'", "'\\''"),
         "Q3 has none"),
        ("options on consecutive bare lines (the forge joins them) denied",
         '''gh pr comment 12 --body "**[em] · Q3 · Sort parameter semantics**

Does AC-6 require sort to work?

(a) Accept the no-op sort. ← ✅ recommended
(b) Honor the sort parameter.

*why*"''', "Q3 has none"),
        ("a single option bullet is not a list — denied",
         '''gh pr comment 12 --body "**[em] · Q1 · lock strategy**

Row or table lock?

- (a) row lock ← ✅ recommended, (b) table lock

*Bounds contention.*"''', "Q1 has none"),
        ("intake batch: the second question without bullets — names it",
         r'''gh issue comment 5 --body "**[intake]** 2 questions — discuss below (\`1a 2b\` shorthand welcome).

**Q1 · Scope**

- (a) the endpoint only ← ✅ recommended
- (b) the endpoint and the export

*The export is its own story.*

**Q2 · Driver**

(a) cron ← ✅ recommended (b) webhook

*Cron exists already.*"''', "Q2 has none"),  # noqa: E501
        ("a story-level title is a question — denied",
         '''gh pr comment 12 --body "**[product] · Q2 · Export scope (story-level)**

Is the export part of this story?

(a) no ← ✅ recommended (b) yes

*why*"''', "Q2 has none"),
        ("a list-item title with prose options denied",
         '''gh pr comment 12 --body "- **[em] · Q1 · lock strategy**
  Row or table lock? (a) row ← ✅ recommended (b) table. *why*"''', "Q1 has none"),
        ("glab discussions form denied",
         '''glab api -X POST "projects/:id/merge_requests/7/discussions" -f body="**[em] · Q1 · lock strategy**

Row or table lock?

(a) row lock ← ✅ recommended (b) table lock

*why*" -f "position[position_type]=text"''', "Q1 has none"),  # noqa: E501
        ("body-file heredoc parsed and denied", '''gh pr comment 12 --body-file - <<EOF
**[em] · Q1 · lock strategy**

Row or table lock?

(a) row lock ← ✅ recommended (b) table lock
EOF''', "Q1 has none"),
        ("ANSI-C quoted body denied",
         r"gh pr comment 12 --body $'**[em] · Q1 · lock strategy**\n\nRow or table?\n\n"
         r"(a) row ← ✅ recommended (b) table'", "Q1 has none"),
        # The label is free text (codex review, PR #112): punctuation in it
        # does not turn a question into a non-question.
        ("a label with a colon is still a question — denied",
         '''gh pr comment 12 --body "**[em] · Q1 · Scope: exports**

Is the export in?

(a) no ← ✅ recommended (b) yes"''', "Q1 has none"),
        ("a label with a parenthetical is still a question — denied",
         '''gh pr comment 12 --body "**[em] · Q1 · Sort (pagination)**

Does sort apply?

(a) no ← ✅ recommended (b) yes"''', "Q1 has none"),
        ("an unbolded label with a colon is still a question — denied",
         '''gh pr comment 12 --body "[em] · Q1 · Scope: exports

Is the export in?

(a) no ← ✅ recommended (b) yes"''', "Q1 has none"),
    ]
    ALLOWED = [
        ("the prescribed shape allowed", 'gh pr comment 12 --body "%s"' % GOOD),
        ("asterisk and numbered list markers allowed",
         '''gh pr comment 12 --body "**[em] · Q1 · lock strategy**

Row or table lock?

* (a) row lock ← ✅ recommended
* (b) table lock

**Q2 · Driver**

1. (a) cron ← ✅ recommended
2. (b) webhook"'''),
        ("option bullets with detail sub-bullets allowed",
         '''gh pr comment 12 --body "**[em] · Q1 · lock strategy**

- (a) row lock ← ✅ recommended
  - bounds contention
- (b) table lock"'''),
        ("a batch where every question has bullets allowed",
         '''gh issue comment 5 --body "**[intake]** 2 questions.

**Q1 · Scope**

- (a) the endpoint only ← ✅ recommended
- (b) both

**Q2 · Driver**

- (a) cron ← ✅ recommended
- (b) webhook"'''),
        ("a resolved item — the title shares its line — allowed",
         '''gh pr comment 12 --body "**[spec-answers] · folded**

**[em] · Q1 · lock strategy** — resolved.
**Resolved:** (a) row lock — paul. Folded into R4."'''),
        ("a bolded ruling line allowed",
         '''gh issue comment 5 --body "**[intake] · note**

**Q1 · Scope → (a)**
**Q2 · Driver → (b)**"'''),
        ("an unbolded resolved item allowed",
         '''gh pr comment 12 --body "[em] · Q1 · lock strategy — resolved.
**Resolved:** (a) row lock — paul."'''),
        ("text after the closing bold is not a title — allowed",
         '''gh pr comment 12 --body "**Q1 · Scope** — the holder's call, see the thread."'''),
        ("a rulings list — each title shares its line — allowed",
         '''gh issue comment 5 --body "**[intake] · note** rulings so far:

**Q1 · Scope** → (a)
**Q2 · Driver** → (b)"'''),
        ("an answer that mentions options allowed",
         '''gh api -X POST "repos/o/r/pulls/12/comments/9/replies" -f body="**[review] · answer**

(a) it is — see R4; (b) was never on the table."'''),
        ("a question-shaped CR body allowed (comments only)",
         '''gh pr create --title t --body "**[em] · Q1 · lock strategy**

(a) row (b) table"'''),
    ]

    def test_denied(self):
        for name, cmd, says in self.DENIED:
            with self.case(name):
                self.assertDenied(self.bash(cmd), says)

    def test_allowed(self):
        for name, cmd in self.ALLOWED:
            with self.case(name):
                self.assertAllowed(self.bash(cmd))

    def test_only_forge_writes_and_no_api(self):
        with self.case("non-forge command carrying a prose question allowed (gh/glab only)"):
            self.assertAllowed(self.bash(
                'git commit -m "**[em] · Q3 · label** (a) row (b) table"'))
        with self.case("rule F made no API call"):
            self.assertEqual(self.api_calls(), [])

    def test_body_file_read_back(self):
        prose = self.tmp / "q-prose.md"
        prose.write_text(self.PROSE + "\n")
        good = self.tmp / "q-good.md"
        good.write_text(self.GOOD + "\n")
        with self.case("body-file read back and denied"):
            self.assertDenied(self.bash("gh pr comment 12 --body-file %s" % prose),
                              "Q3 has none")
        with self.case("body-file with the prescribed shape allowed"):
            self.assertAllowed(self.bash("gh pr comment 12 --body-file %s" % good))


class RuleG_StopCommentNamesItsResume(HookTest):
    """Static rule, no API. Issue #98 (ADMC #73): the STOP comment named no
    label move and no channel; the human left `blocked` on and answered as
    a top-level CR comment — neither heard."""

    guard = "guard-gate"

    STOP = """**[next-stage] · blocked**

Step A4 died: the push of `spec/5` was rejected (non-fast-forward).
Remote: `spec/5` exists at `abc1234`, no CR. Recommended: fetch, rebase the
worktree commit onto `origin/spec/5`, push again.

<details><summary>Evidence</summary>

    ! [rejected] spec/5 -> spec/5 (fetch first)

</details>"""
    RESUME = ("**To resume:** clear `status: blocked`, apply `status: ready-for-spec` — "
              "yourself, or tell the main agent; nothing to answer — run the remedy first.")
    GOOD = STOP.replace("<details>", RESUME + "\n\n<details>", 1)

    DENIED = [
        ("a STOP comment without the resume line — denied",
         'gh issue comment 5 --body "%s"' % STOP, "resume line"),
        ("glab form denied",
         'glab issue note 5 --message "%s"' % STOP, "resume line"),
        ("api form denied",
         "gh api -X POST repos/o/r/issues/5/comments -f body='%s'" % STOP, "resume line"),
        ("heredoc body-file denied",
         "gh issue comment 5 --body-file - <<'EOF'\n%s\nEOF" % STOP, "resume line"),
        ("ANSI-C quoted body denied",
         r"gh issue comment 5 --body $'**[integrate] · blocked**\n\nconflict in a.txt; "
         r"see below.'", "resume line"),
        ("the resume line in another segment is not in the body — denied",
         'gh issue comment 5 --body "%s" && echo "%s"' % (STOP, RESUME), "resume line"),
        ("the line without its bold opening is not the line — denied",
         'gh issue comment 5 --body "%s"' % STOP.replace(
             "<details>", "To resume: clear blocked, apply ready-for-spec.\n\n<details>", 1),
         "resume line"),
        # Codex review, PR #114: the line must CLOSE the must-read.
        ("the resume line only inside the folded evidence — denied",
         'gh issue comment 5 --body "%s"' % STOP.replace(
             "</details>", RESUME + "\n</details>", 1), "resume line"),
        ("the resume line followed by more must-read prose — denied",
         'gh issue comment 5 --body "%s"' % STOP.replace(
             "<details>", RESUME + "\n\nAlso: the worktree is gone.\n\n<details>", 1),
         "resume line"),
    ]
    ALLOWED = [
        ("the prescribed shape allowed", 'gh issue comment 5 --body "%s"' % GOOD),
        ("glab prescribed shape allowed", 'glab issue note 5 --message "%s"' % GOOD),
        ("integrate's phase-less resume line allowed",
         '''gh issue comment 5 --body "**[integrate] · blocked**

Round 3 of 3 red: 3 harness issues in a row, all in AcceptanceSupport.

**To resume:** clear `status: blocked` — nothing else; patrol re-runs integrate."'''),
        ("`blocked` in prose with no STOP title allowed",
         '''gh pr comment 12 --body "**[review] · question** — the merge is blocked on a conflict in a.txt; which side wins?"'''),  # noqa: E501
        ("a title sharing its line is not the STOP title — allowed",
         '''gh issue comment 5 --body "**[next-stage] · blocked** — see the thread; nothing to resume."'''),  # noqa: E501
        ("no evidence block at all — the line last — allowed",
         'gh issue comment 5 --body "%s"' % (STOP.split("<details>", 1)[0] + RESUME)),
        ("the title quoted inside a sentence allowed",
         '''gh issue comment 5 --body "✅ [next-stage] resumed — the **[next-stage] · blocked** comment above is handled."'''),  # noqa: E501
    ]

    def test_denied(self):
        for name, cmd, says in self.DENIED:
            with self.case(name):
                self.assertDenied(self.bash(cmd), says)

    def test_allowed(self):
        for name, cmd in self.ALLOWED:
            with self.case(name):
                self.assertAllowed(self.bash(cmd))

    def test_only_forge_writes_and_no_api(self):
        with self.case("non-forge command carrying the STOP title allowed (gh/glab only)"):
            self.assertAllowed(self.bash('git commit -m "**[next-stage] · blocked**"'))
        with self.case("rule G made no API call"):
            self.assertEqual(self.api_calls(), [])

    def test_body_file_read_back(self):
        stop = self.tmp / "stop.md"
        stop.write_text(self.STOP + "\n")
        good = self.tmp / "stop-good.md"
        good.write_text(self.GOOD + "\n")
        with self.case("body-file read back and denied"):
            self.assertDenied(self.bash("gh issue comment 5 --body-file %s" % stop),
                              "resume line")
        with self.case("body-file with the resume line allowed"):
            self.assertAllowed(self.bash("gh issue comment 5 --body-file %s" % good))


# The E2 fixture's exact technical-spec.md (the scripted double's output).
TS_WITH_SECTION = """# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.

## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
"""
TS_MOVED = """# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
  (open question on the clock source: spec.md Q9)
"""
TS_POINTER_ONLY = """# Technical spec #5

## §9 Open questions
- moved → spec.md Q9
"""
SPEC_MD = "# Spec #5\n\n## Open Questions\n- **[implementer] · Q9 · Clock source**\n"


class RuleD_OpenQuestionsHaveOneHome(HookTest):
    """A commit never carries an open-questions section in a technical-spec.md
    under specs_dir (1.15.0; E2 measured 0/5 on prose). The steps share one
    repo and run in order."""

    guard = "guard-gate"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", specs_dir="docs/specs")})
        (self.repo / "sub").mkdir()
        self.ts = self.repo / "docs/specs/5/technical-spec.md"

    def stage(self, technical_spec):
        """Write technical-spec.md and spec.md, then stage everything."""
        self.write(self.ts, technical_spec)
        self.write(self.repo / "docs/specs/5/spec.md", SPEC_MD)
        self.git(self.repo, "add", "-A")

    def test_rule_d(self):
        repo = self.repo
        self.stage(TS_WITH_SECTION)
        with self.case("rule D: §9 section left in technical-spec.md denied"):
            self.assertDenied(self.bash('git commit -m "spec: #5 refinement"', repo),
                              "open-questions section")
        with self.case("rule D: message carries the remedy (move + delete, A6)"):
            self.assertDenied(self.bash('git commit -m "spec: #5 refinement"', repo),
                              "delete it here")
        with self.case("rule D: judged from a subdirectory"):
            self.assertDenied(self.bash("git commit -am x", repo / "sub"), "open-questions section")
        # The block's two homes (#94): specs_dir read from CLAUDE.local.md too.
        local = self.new_repo({"CLAUDE.md": "# Project\n",
                               "CLAUDE.local.md": config_block(forge="github",
                                                               specs_dir="docs/specs")})
        self.write(local / "docs/specs/5/technical-spec.md", TS_WITH_SECTION)
        self.write(local / "docs/specs/5/spec.md", SPEC_MD)
        self.git(local, "add", "-A")
        with self.case("rule D: block only in CLAUDE.local.md — §9 section still denied"):
            self.assertDenied(self.bash('git commit -m "spec: #5 refinement"', local),
                              "open-questions section")
        with self.case("rule D: compound line (cd && git commit) denied"):
            self.assertDenied(self.bash("git add -A && git -c user.name=t commit -m x", repo),
                              "open-questions section")
        with self.case("rule D: a comment body mentioning git commit is not a commit"):
            self.assertAllowed(self.bash(
                'gh pr comment 12 --body "**[review] · answer** run git commit after the fix"',
                repo))

        self.stage(TS_MOVED)
        with self.case("rule D: moved — pointer line under another heading — allowed"):
            self.assertAllowed(self.bash('git commit -m "spec: #5 refinement"', repo))

        self.stage(TS_POINTER_ONLY)
        with self.case("rule D: heading kept as pointer-only section still denied"):
            self.assertDenied(self.bash("git commit -m x", repo), "open-questions section")

        self.stage(TS_WITH_SECTION)
        self.write(self.ts, TS_MOVED)  # fixed in the working tree, not re-staged
        with self.case("rule D: fixed in the working tree but stale in the index denied"):
            self.assertDenied(self.bash("git commit -m x", repo), "git add")

        self.git(repo, "add", "-A")
        with self.case("rule D: spec.md's own Open Questions is the destination, not a hit"):
            self.assertAllowed(self.bash("git commit -m x", repo))

        self.write(self.ts, TS_WITH_SECTION)  # unstaged
        with self.case("rule D: unstaged working-tree section denied (commit -a would take it)"):
            self.assertDenied(self.bash("git commit -am x", repo), "working tree")

        self.git(repo, "checkout", "-q", "--", "docs/specs/5/technical-spec.md")
        self.write(repo / "notes/9/technical-spec.md", TS_WITH_SECTION)
        with self.case("rule D: a technical-spec.md outside specs_dir is not in scope"):
            self.assertAllowed(self.bash("git add -A && git commit -m x", repo))

    def test_no_config_block(self):
        repo = self.new_repo(commit=True, branch="spec/1")
        self.write(repo / "docs/specs/1/technical-spec.md", TS_WITH_SECTION)
        self.git(repo, "add", "-A")
        with self.case("rule D: repo without a Roz Gate config block untouched"):
            self.assertAllowed(self.bash("git commit -m x", repo))


class RuleA_IntakeSummaryTrigger(HookTest):
    """An intake summary is posted only when the gate holder asked for it (or a
    gate label authorizes the finalize). Each case swaps the fake gh's issue
    JSON (tests/fx/)."""

    guard = "guard-gate"

    # (name, fixture, stderr substring or None for allowed)
    GITHUB = [
        ("summary without trigger blocked (#54 case)", "gh_no_trigger.json",
         "human decision point"),
        ("summary after gate holder's 'summary' allowed", "gh_summary.json", None),
        ("summary with gate label allowed (finalize)", "gh_gate_label.json", None),
        ("duplicate summary blocked", "gh_already.json", "already"),
        ("'summary' from non-gate-holder blocked", "gh_wrong_person.json", "gate holder"),
        # The summary-request line rule: corrections + summary in one comment.
        ("corrections + last-line summary allowed", "gh_corrections_lastline.json", None),
        ("first-line summary allowed", "gh_firstline.json", None),
        ("mid-text summary mention blocked", "gh_midline.json", "human decision point"),
        ("finalize regen after bystander chatter allowed", "gh_gate_label_bystander.json", None),
    ]

    def check(self, result, says):
        if says is None:
            self.assertAllowed(result)
        else:
            self.assertDenied(result, says)

    def test_github(self):
        for name, fx, says in self.GITHUB:
            with self.case(name), self.fixture(gh=fx):
                self.check(self.bash(SUMMARY_CMD), says)
        with self.case("unparseable issue ref blocked"):
            self.assertDenied(self.bash(
                'gh issue comment https://github.com/x/y/issues/54 '
                '--body "**[intake] · summary** ..."'), "adapter form")

    def test_api_failure_fails_closed(self):
        with self.case("API failure fails closed with retry wording"), self.fixture(fail=True):
            self.assertDenied(self.bash(SUMMARY_CMD), "NOT a protocol block")

    def test_bot_mode(self):
        """Bot mode (1.7.0): identity comes from the project's config block."""
        config = config_block(forge="github", agent_identity="bot", bot_login="roz-bot")
        repo = self.new_repo({"CLAUDE.md": "## Development Workflow (Roz Gate)\n\n" + config})
        (repo / "sub").mkdir()
        cases = [
            ("bot mode: bot-posted summary counts as already-posted",
             "gh_bot_already.json", repo, "already"),
            ("bot mode: human quoting the marker doesn't count",
             "gh_bot_human_quote.json", repo, None),
            ("bot mode: bot-authored unassigned issue denied",
             "gh_bot_orphan.json", repo, "no human gate holder"),
            ("bot mode: config found from a subdirectory",
             "gh_bot_human_quote.json", repo / "sub", None),
        ]
        for name, fx, cwd, says in cases:
            with self.case(name), self.fixture(gh=fx):
                self.check(self.bash(SUMMARY_CMD, cwd), says)
        # The block's two homes (#94): ADMC runs in bot mode with its block in
        # CLAUDE.local.md — rule A silently ran in user mode there.
        local = self.new_repo({"CLAUDE.md": "# Project\n", "CLAUDE.local.md": config})
        with self.case("bot mode: block only in CLAUDE.local.md — bot-authored unassigned issue "
                       "denied"), self.fixture(gh="gh_bot_orphan.json"):
            self.check(self.bash(SUMMARY_CMD, local), "no human gate holder")

    def test_gitlab(self):
        with self.case("glab summary after 'summary' allowed"):
            self.assertAllowed(self.bash('''glab issue note 7 --message "**[intake] · summary**

**Story** ..."'''))


TS_V1 = ("# Technical spec #5\n\n## Contract\n- **C1 (R4)** — `price(cart, now)` excludes "
         "offers with `expires_at < now`.\n")
TS_V2 = TS_V1 + "- **C2 (R4)** — `now` is the DB clock, not the caller's (as built).\n"
DEVIATIONS = ("## Contract deviations\n\n- **C2** — `now` was the caller's clock; the DB clock "
              "is the only one the sweep can see. Declared, not decided: R4 is untouched.\n")


class RuleH_CrOpenDeclaresDeviations(HookTest):
    """2.0.0 (#140): the implementer corrects technical-spec.md on its branch
    as it builds, and QA tests the contract as built. A CR-OPEN whose diff
    touches `<specs_dir>/*/technical-spec.md` carries `## Contract
    deviations` in its body; the diff is one git call, and a diff the guard
    cannot compute fails closed. The repo: spec/5 at the seed, feat/5 edits
    the contract and the code, feat/6 edits the code only."""

    guard = "guard-gate"
    CR = 'gh pr create --base spec/5 --head feat/5 --title "feat: implement #5" --body "%s"'

    def setUp(self):
        super().setUp()
        repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", specs_dir="docs/specs"),
             "docs/specs/5/technical-spec.md": TS_V1,
             "docs/specs/5/spec.md": "# Spec #5\n", "src/app.py": "x = 1\n"}, commit=True)
        self.git(repo, "branch", "-q", "spec/5")
        self.git(repo, "checkout", "-q", "-b", "feat/5")
        self.write(repo / "docs/specs/5/technical-spec.md", TS_V2)
        self.write(repo / "src/app.py", "x = 2\n")
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "impl #5")
        self.git(repo, "checkout", "-q", "-b", "feat/6", "spec/5")
        self.write(repo / "src/app.py", "x = 3\n")
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "impl #6")
        self.git(repo, "checkout", "-q", "feat/5")
        (repo / "sub").mkdir()
        self.repo = repo

    def test_denied(self):
        repo = self.repo
        for name, cmd, says in [
            ("rule H: the diff touches technical-spec.md and the body has no section — denied",
             self.CR % "Closes #5", "Contract deviations"),
            ("rule H: the message names the file and the remedy",
             self.CR % "Closes #5", "docs/specs/5/technical-spec.md"),
            ("rule H: a body that merely mentions deviations is not the section — denied",
             self.CR % "Closes #5. Contract deviations: none.", "Contract deviations"),
            ("rule H: --fill (no body at all) — denied",
             'gh pr create --base spec/5 --head feat/5 --fill', "Contract deviations"),
            ("rule H: heredoc body-file without the section — denied",
             "gh pr create --base spec/5 --head feat/5 --title t --body-file - <<'EOF'\n"
             "Closes #5\nEOF", "Contract deviations"),
            ("rule H: the head defaults to HEAD (feat/5 checked out) — denied",
             'gh pr create --base spec/5 --title t --body "Closes #5"', "Contract deviations"),
            ("rule H: glab mr create without the section — denied",
             'glab mr create --source-branch feat/5 --target-branch spec/5 --title t '
             '--description "Closes #5"', "Contract deviations"),
            ("rule H: an unknown base — the diff cannot be computed — fails closed",
             'gh pr create --base nope/5 --head feat/5 --title t --body "%s"' % DEVIATIONS,
             "could not be computed"),
            ("rule H: the fail-closed message says it is not a protocol block",
             'gh pr create --base nope/5 --head feat/5 --title t --body "%s"' % DEVIATIONS,
             "NOT a protocol block"),
            ("rule H: compound line — the create segment is still judged",
             'git push -q origin feat/5 && ' + self.CR % "Closes #5", "Contract deviations"),
        ]:
            with self.case(name):
                self.assertDenied(self.bash(cmd, repo), says)
        with self.case("rule H: judged from a subdirectory"):
            self.assertDenied(self.bash(self.CR % "Closes #5", repo / "sub"), "Contract deviations")
        # gh's default base (codex review, PR #143): branch.<head>.gh-merge-base
        # before the repository default branch.
        self.git(repo, "config", "branch.feat/5.gh-merge-base", "spec/5")
        with self.case("rule H: no --base — the head's gh-merge-base is the base — denied"):
            self.assertDenied(self.bash(
                'gh pr create --title t --body "Closes #5"', repo), "Contract deviations")
        with self.case("rule H: no --base, --head given — that branch's gh-merge-base — denied"):
            self.assertDenied(self.bash(
                'gh pr create --head feat/5 --title t --body "Closes #5"', repo / "sub"),
                "Contract deviations")
        with self.case("rule H: no --base, no gh-merge-base, no origin/HEAD — fails closed"):
            self.git(repo, "config", "--unset", "branch.feat/5.gh-merge-base")
            self.assertDenied(self.bash(
                'gh pr create --title t --body "Closes #5"', repo), "could not be computed")
        nosec = self.tmp / "body-nosec.md"
        nosec.write_text("Closes #5\n")
        with self.case("rule H: --body-file read back without the section — denied"):
            self.assertDenied(self.bash(
                "gh pr create --base spec/5 --head feat/5 --title t --body-file %s" % nosec, repo),
                "Contract deviations")
        with self.case("rule H: an unreadable --body-file fails closed"):
            self.assertDenied(self.bash(
                "gh pr create --base spec/5 --head feat/5 --title t --body-file /nonexistent/b.md",
                repo), "cannot judge")

    def test_allowed(self):
        repo = self.repo
        for name, cmd in [
            ("rule H: the section present — allowed", self.CR % ("Closes #5\n\n" + DEVIATIONS)),
            ("rule H: the section with `none` — allowed",
             self.CR % "Closes #5\n\n## Contract deviations\n\nnone"),
            ("rule H: a deeper heading with a trailing note — allowed",
             self.CR % "Closes #5\n\n### Contract deviations — none"),
            ("rule H: heredoc body-file with the section — allowed",
             "gh pr create --base spec/5 --head feat/5 --title t --body-file - <<'EOF'\n"
             "Closes #5\n\n" + DEVIATIONS + "EOF"),
            ("rule H: --body= glued form with the section — allowed",
             "gh pr create --base spec/5 --head feat/5 --title t --body='Closes #5\n\n%s'"
             % DEVIATIONS),
            ("rule H: glab mr create with the section — allowed",
             'glab mr create --source-branch feat/5 --target-branch spec/5 --title t '
             '--description "Closes #5\n\n%s"' % DEVIATIONS),
            ("rule H: a diff that does not touch technical-spec.md needs no section — allowed",
             'gh pr create --base spec/5 --head feat/6 --title t --body "Closes #6"'),
            ("rule H: a draft CR (the QA CR) off the spec tip — no contract change — allowed",
             'gh pr create --draft --base spec/5 --head feat/6 --title t --body "QA"'),
            ("rule H: a comment that mentions `pr create` is not a CR-OPEN — allowed",
             'gh pr comment 12 --body "run gh pr create after the fix"'),
            ("rule H: the fast CR off the base, code only — allowed",
             'gh pr create --base spec/5 --head feat/6 --title "fast: #6 x" --body "Closes #6"'),
        ]:
            with self.case(name):
                self.assertAllowed(self.bash(cmd, repo))
        good = self.tmp / "body-good.md"
        good.write_text("Closes #5\n\n" + DEVIATIONS)
        with self.case("rule H: --body-file read back with the section — allowed"):
            self.assertAllowed(self.bash(
                "gh pr create --base spec/5 --head feat/5 --title t --body-file %s" % good, repo))
        with self.case("rule H: -F file with the section — allowed"):
            self.assertAllowed(self.bash(
                "gh pr create --base spec/5 --head feat/5 --title t -F %s" % good, repo))
        self.git(repo, "config", "branch.feat/5.gh-merge-base", "spec/5")
        with self.case("rule H: no --base, the head's gh-merge-base, with the section — allowed"):
            self.assertAllowed(self.bash(
                'gh pr create --title t --body "Closes #5\n\n%s"' % DEVIATIONS, repo))
        with self.case("rule H: --base wins over gh-merge-base (feat/6: no contract change)"):
            self.git(repo, "config", "branch.feat/6.gh-merge-base", "feat/5")
            self.assertAllowed(self.bash(
                'gh pr create --base spec/5 --head feat/6 --title t --body "Closes #6"', repo))
        self.git(repo, "config", "--unset", "branch.feat/5.gh-merge-base")
        self.git(repo, "config", "--unset", "branch.feat/6.gh-merge-base")
        # A worktree cut from origin/<spec-branch> may have no local spec/5:
        # the base resolves through its origin/ form (resolve_ref).
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "spec/5"],
                             capture_output=True, text=True).stdout.strip()
        self.git(repo, "update-ref", "refs/remotes/origin/spec/5", sha)
        self.git(repo, "branch", "-q", "-D", "spec/5")
        with self.case("rule H: a base that exists only as origin/<base> resolves — judged"):
            self.assertDenied(self.bash(self.CR % "Closes #5", repo), "Contract deviations")
        with self.case("rule H: … and passes with the section"):
            self.assertAllowed(self.bash(self.CR % ("Closes #5\n\n" + DEVIATIONS), repo))
        with self.case("rule H: rule H made no API call"):
            self.assertEqual(self.api_calls(), [])

    def test_no_config_block(self):
        repo = self.new_repo({"docs/specs/5/technical-spec.md": TS_V1}, commit=True)
        self.git(repo, "branch", "-q", "spec/5")
        self.git(repo, "checkout", "-q", "-b", "feat/5")
        self.write(repo / "docs/specs/5/technical-spec.md", TS_V2)
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
        with self.case("rule H: repo without a Roz Gate config block untouched"):
            self.assertAllowed(self.bash(self.CR % "Closes #5", repo))
        with self.case("rule H: outside any git repo — allowed (nothing to diff, not a project)"):
            self.assertAllowed(self.bash(self.CR % "Closes #5", self.new_dir()))
