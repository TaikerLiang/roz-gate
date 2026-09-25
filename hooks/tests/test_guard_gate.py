"""guard-gate (Bash): rules A-D. See hooks/README.md for each rule's predicate.

A case table is (name, command) for allowed cases and (name, command,
stderr substring) for denied ones.
"""

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

    def test_gitlab(self):
        with self.case("glab summary after 'summary' allowed"):
            self.assertAllowed(self.bash('''glab issue note 7 --message "**[intake] · summary**

**Story** ..."'''))
