# The ledger — every case, one index

The eval ledger's cases live in three places: lint cases as one file each
under `lint/cases/` (`b1.py`, `c19.py`, …), replay cases as
`replay/cases/<ID>/`, and the judgment corpus in `judgment/criteria.json`.
This page indexes all of them — **rendered by `tools/ledger.py`** from the
cases' own metadata (a lint file's `META`, a replay `case.json`'s `tier` and
`ledger_text`, `ledger-deferred.json` for a case with no checker yet) into
`ledger-template.md`, which holds this prose. Never edit it by hand: edit
the case, rerun the tool; `--check` goes red in CI and pre-push while it is
stale (issue #131).

**Provenance.** The original ledger document is not in the repository.
This index was reconstructed on 2026-09-26 from what the repository does
hold:

- **Titles** come from each lint case's `META` and each replay case's
  `case.json`.
- **Ledger text** is quoted verbatim from the checkers' `# source: ledger
  <ID> — "…"` citations. It is the only surviving ledger prose; each entry
  reads as the expected outcome, then (in parentheses) why it matters.
  Lint cases carry no such quote.
- **Family descriptions** were inferred from the titles and confirmed by
  Paul on 2026-09-26; they are this page's, not recovered.

A new case is written in its metadata first — the row is the case's, and
this page renders it. A checker's `source: ledger` quote copies that row,
never the other way round.

## IDs

A letter names the family, the number the order a case was added — a
number is never reused. Rule letters in `hooks/README.md` (rules A–E) are
a separate namespace: hook rule D is unrelated to ledger case D2.

| family | what it guards |
|---|---|
| **A** | patrol sees every channel a human can speak through |
| **B** | the text conventions of agent-written comments — tags and markers |
| **C** | the label state machine and each command's exits |
| **D** | what a dispatched seat receives, and what it must not see |
| **E** | a question reaches the gate holder; an answer lands where it belongs |
| **F** | the loop end to end — whole commands, whole sessions |
| **J** | the judgment tier's own instrument (lint only) |
| **L** | the human-facing pages (lint only) |

## Cases

`lint` = static check on every push · `replay` = headless runs, pass^k ·
`hook` = enforced by a hook, proven in `hooks/tests/`.

### A · patrol sees every channel

| ID | title | tier | ledger text |
|---|---|---|---|
| A1 | A human's ✅ acknowledgement reads as an agent marker | replay | "Classified unheard → actionable. The agent marker is `✅ [`, never a bare ✅." (the single highest-value message in the channel was the one the predicate could not see) |
| A2 | A review whose whole content is its body is invisible | replay | "Detected as unheard via REVIEWS-LIST." (a repository could scan perfectly clean while a reviewer had blocked the change) |
| A3 | Top-level comments are read as a channel | replay | "Actionable. Top-level is the default affordance on the PR page and the only one usable from a phone." |
| A4 | in-user-review is a listening state, not a terminal one | replay | "Actionable → review-answers. Not 'waiting on the user'." (the original defect: comments sat unanswered while every pass reported the loop was waiting on the human) |
| A5 | The fast track resolves to its own CR | replay | "CR resolves to fast/<n> and the item is detected." (the row said "spec CR", so the A4 fix would have covered only half the tracks) |
| A6 | notification | deferred | no channel stub in the headless sandbox — see `replay/README.md`, cannot-see #1 |
| A7 | A merged CR closes the issue out | replay | "Issue closed; every `track:`/`status:` label gone; exactly one shipped comment naming the CR; exactly one close; nothing written to the CR — and an issue the forge already closed on merge loses its labels and gets its comment, with no second close." (an OPEN CR at in-user-review is F1/A4/A5's fixture — zero label writes there) (GitLab and any CR against a release branch leave the issue open wearing `in-user-review` after the merge — the loop's last step never happened — issue #41) |
| A8 | The scan is one read-only sub-agent and the rules exist once | lint (defect 1.24.0-) | — |
| A9 | Patrol answers every human comment on an intake thread | replay + hook (guard-gate rule I) + lint (#174) | "On #7 (author kai, assignee paul): one `**[intake] · reply**` comment, after kai's comment, naming kai, no @-mention, no batch question re-asked, the holder's label named as the decision; no label writes beyond the lock, no body edit, no summary. On #8 (only a `[bot]` comment after the batch): no comment." (until 2.4.0 the Otherwise route left every comment after the batch unanswered until `summary` or a label — #174) |

### B · agent-written text conventions

| ID | title | tier | ledger text |
|---|---|---|---|
| B1 | a compound tag evades the literal it contains | lint (defect 1.12.0-) | — |
| B2 | a line-wrapped tag survives the check | lint (defect 1.12.0-) | — |
| B3 | the marker convention is identical everywhere | lint (preventive) | — |
| B4 | an agent write never opens with a quote block | lint (defect 1.11.0-) + hook (guard-gate rule C) | — |
| B5 | the must-read stays on top and within budget | lint (defect 1.19.0-) | — |
| B6 | `unverified` is a reserved word — a spec document carries it only as the evidence tag; the Path B and promote checks match the whole word anywhere, so the word in prose (line-initial after a wrap, mid-sentence, capitalised) stops the gate like a tag and the remedy is to reword; `unverifiable` / `verified` are not hits | lint (defect 1.36.1-, #123) | — |
| B7 | the patrol report is one fixed table — `\| issue \| state \| this pass \| needs you \|`, one row per scanned issue, one clause per cell, no row citing another pass; the queue is exactly the `needs you` rows with links; `## Details` trails and never hides what needs the human | lint (defect 1.37.0-, #124) | — |
| B8 | QA's level is pinned — through the port only, in `<acceptance_dir>`, no unit tests, no implementation imports beyond the port's declared types; the port is the API for an HTTP feature and never "always HTTP" | lint (#140, 2.0.0) | — |
| B9 | the reserved-word registry is the single source — every word in `references/reserved-words.json` appears in the Markdown of `agents commands references templates` only in code formatting, and every `spec_gate` word (`unverified`) has a whole-word gate grep in Path B and promote; a bare use, a missing grep or an empty registry is red | lint (#154, 2.2.0; #160, 2.2.1) | — |

### C · labels and exits

| ID | title | tier | ledger text |
|---|---|---|---|
| C1 | A STOP strips the gate label | replay | "Labels become blocked alone — never ready-for-dev + blocked." (patrol treats a gate label as unconditionally actionable; leaving it re-invokes the command every pass) |
| C2 | Stage (7) has no blocked exit | replay | "in-user-review is retained; no blocked. The failure is a prefixed comment." (blocked exists to stop the machine, not to inform the human; at (7) there is no machine to stop) |
| C3 | `processing` coexists with a phase label | lint (preventive) | — |
| C4 | track: fast + ready-for-spec refused | hook (guard-gate) | — |
| C5 | Post-integration re-entry has a branch of its own — and is honest about what it verified | lint + replay (amended for #97) | "Folds; the fold changed behaviour, so no acceptance run is taken as evidence and the gate kit's cards are not regenerated — its `cards-sha` stamp is untouched; the return comment `**[spec-answers] · amended**` names the fold and says the implementation and the suite still implement the previous text; `in-user-review` applied, `in-spec-review` and `processing` removed, the thread resolved, no 'move to implementation'." (without the branch the first-pass branch fires and tells a shipped feature it is ready to move to implementation; before #97 the branch re-ran the suite green against the previous text and regenerated the cards from it — ADMC #63) |
| C6 | CR lookup sees merged CRs where it must | lint (defect 1.11.0-) | — (amended for #77, 1.30.0: the scanner's in-flight row also reads the all-states form — a merged `feat`/`qa` CR satisfies "exists, thread-clean, not a draft", so both-merged routes to the re-verdict; the guard that held the row to the open-only default is gone) |
| C7 | A branch is cut only from a base the remote has | lint + replay | "Labels are blocked alone; the STOP comment names the missing base; no branch pushed, no CR opened." (a mistyped or retired `default_branch` used to cut an empty branch from nothing and open a CR against it — issue #38; until #90 its two anchors pinned the bare `git merge --no-edit <default_branch>` / `git diff <default_branch>...` — the local ref — as the required form) |
| C8 | A merged CR closes the issue out — the prose side | lint (defect 1.19.0-) | — |
| C9 | A command's git work lives in a worktree it removes on every exit | lint (defect 1.19.0-) + hook (rule E worktree forms) | — |
| C10 | Re-entering the spec stage after a closed CR is the human's door | lint + replay | "Labels are blocked alone; the comment carries `git push origin --delete spec/<n>` and cites the closed CR; no CR created; the remote's refs unchanged — never force-pushed, never deleted by the agent." (a second `ready-for-spec` on a branch that still exists used to fail the cut with a git error, and the only automatic fixes — force-push, delete — would give agents a destructive remote write — issue #62) |
| C11 | A template with `{seq}` re-enters by the next sequence | replay | "`spec/paul/5/2` is cut and its CR opened; `spec/paul/5/1` still points at the first attempt; nothing deleted, nothing force-pushed; no STOP comment, labels end at `in-spec-review`." (C10's STOP exists because the only automatic fixes were destructive; a template that counts attempts has a non-destructive one — issue #75) |
| C12 | A merged CR is never re-merged — integrate validates the spec tip | lint + replay (seed amended for #95: the QA CR carries the fidelity record) | "Both CRs merged, `spec/<n>` moved since: nothing merged — neither tip becomes an ancestor of `spec/<n>`, the moved tip's content is intact on the remote, the suites ran against it, labels end at `in-user-review` alone, no STOP comment, and the claim reads 'green against the pre-rework spec, at SHA x'." (integrate re-merged two already-incorporated branches into a `spec/<n>` that had moved independently — a rebase, a sync with concurrent work — and stopped on a two-line conflict in a test file: a re-merge of stale inputs reported as a failed verdict attempt — issue #77) |
| C13 | The in-flight row sees a merged CR | replay (seed amended for #95: the QA CR carries the fidelity record) | "#5 wears `track: spec` alone with `feat/5` and `qa/5` merged into `spec/5`: the scanner's row reads `actionable: integrate`, the pass takes the lock on #5, and no row reads `in progress`." (the open-only lookup read a merged CR as absent, so patrol said "in progress" about a finished build and a STOP cleared by the human was never re-run — issue #77) |
| C14 | the fix-and-rerun cap is `fix_rounds`, and the cap STOP carries the ledger and the three doors | lint (defect 1.30.0-, #78) | — |
| C15 | The default branch is read from the remote at every git site | lint (defect 1.31.0-, #90) | "integrate 5.2 merges `origin/<default_branch>` and next-stage C6 diffs `origin/<default_branch>...<fast-branch>`; no command spells the bare `git merge --no-edit <default_branch>` or `git diff <default_branch>...`; workflow.md states the rule." (the loop never moves the local ref — in a dedicated clone, nobody does — so a green verdict merged an ever-older trunk and the fast reviewer diffed the trunk's own commits as the change; every replay seed has local = remote main, so only the source shows it — issue #90) |
| C16 | A QA CR without a fidelity audit on record never integrates | lint + replay (defect 1.9.0-, #95) | "Labels unchanged (no `status:`), nothing merged or pushed to `spec/5`, no `in-user-review`; the QA CR's comments were listed; the report names the missing fidelity record and patrol's `fidelity-audit` as the road." (integrate's precondition "zero open fidelity threads" was satisfied by an audit that never ran — B5b stopped before the reviewer posted and the unaudited suite integrated; ADMC #73 — and since 2.0.0 the implementation CR needs its `**[reviewer] · code-review**` record the same way, #140 ruling 9: an absence is never read as a pass) |
| C17 | Patrol runs the audit that never ran | replay (#95) | "The scanner's row reads `actionable: fidelity-audit`, never `integrate`; patrol writes the marker with `feat=feat/5`, dispatches `reviewer` under the fidelity brief — once, between marker-on and marker-off — the QA CR gains one `**[reviewer] · fidelity**` comment, posted after every finding thread, and the marker is removed; no `in-user-review`, nothing merged; the lock is released." (no command could run B5b alone — recovery from a B5b STOP was manual) |
| C18 | A STOP comment names its resume move | hook (guard-gate rule G) + lint | "The STOP comment opens with `**[<command>] · blocked**` and its must-read ends with `**To resume:**` — the label to clear, the phase to apply, where the answer goes; a `blocked`-titled comment without the line is denied before it posts." (ADMC #73: the human read the STOP, left `blocked` on and wrote the amendment as a top-level CR comment — neither heard; the comment in front of them named no label move and no channel — issue #98) |
| C19 | tip is read-only and answers from the documents | lint (preventive, #121) | "`tip.md` requires `n`, takes no `processing` lock, reads only ISSUE-VIEW / CR-FIND / THREADS-LIST / REVIEWS-LIST / CR-COMMENTS-LIST / `git ls-remote` / `git worktree list` (each named in both adapters), answers in the three fixed sections, names every illegal state `workflow.md` lists with its repair, and contains no write op — the only `git push` in it is the human's delete remedy." (state management is the adopter's pain — #121) |
| C20 | (4) launches only after the implementation lands on the spec branch | lint + replay (#140, 2.0.0) | "`ready-for-dev` launches (3)+(5); next-stage B2 merges the review-clean implementation CR into `<spec-branch>`, pushes, then cuts `<qa-branch>` off the new tip; the QA dispatch runs between marker-on (`seat=qa`) and marker-off, once; a draft QA CR targets `<spec-branch>`; no gate label is involved; nothing is pushed to `<feat-branch>`." (the parallel launch retires: QA wrote its suite against the contract as drafted and met the contract as built only at (6) — #140) |
| C22 | The implementation review has a record, and review-clean is record-current + zero threads | lint + replay (#140 ruling 9, 2.0.0) | "An implementation CR with zero open threads and no `**[reviewer] · code-review**` record (or a record whose `reviewed-sha` is not the head) never merges into `<spec-branch>`: next-stage B2.1 stops without pushing, cuts no `<qa-branch>`, writes no label, and names the missing record and patrol's `code-review` action as the road." (zero threads because nobody reviewed is not zero findings — the lesson #95 taught on the QA side, applied to the implementation→QA transition before it could repeat) |
| C23 | Patrol runs the review that never ran | replay (#140 ruling 9, 2.0.0) | "The scanner's row reads `actionable: code-review`, never `next-stage (qa)`; patrol dispatches `reviewer` once with the spec docs; the implementation CR gains one `**[reviewer] · code-review**` comment carrying `reviewed-sha:` equal to its head, posted after every finding thread; nothing is merged, no `<qa-branch>` is cut, the lock is released." (the mirror of C17: a thread-clean implementation CR would otherwise read as a reviewed one and land on the spec branch unreviewed) |
| C24 | A bot-applied gate label is an illegal state the scan reports and never acts on | lint (#144, 2.1.0) | "ISSUE-LABEL-EVENTS exists under one name in both adapters (the timeline on GitHub, `resource_label_events` on GitLab); the scanner audits every gate label worn by its latest `labeled` event, normalizes the actor, and names the bot test — the handed `bot_login` list or the forge's bot shape — the verdict literal `illegal state: gate label applied by <login>`, never repair, never route; patrol carries the clause and the queue verb; workflow, protocol §4, README and both pages say it." (the layer the hook cannot be: rule B binds this agent, and a foreign agent's label looked exactly like the human's until the actor was read) |

### D · what a seat receives, and what it must not see

| ID | title | tier | ledger text |
|---|---|---|---|
| D1 | the reviewer receives the claim it reviews against | lint (defect 1.8.0-) | — |
| D2 | The fidelity dispatch is blind by the hook — topology no longer protects (2.0.0) | lint + replay + hook (guard-blind rule E) | "Checkout is qa/<n>; abort if the context ever touched feat/<n>. Blindness asserted in a prompt is a request; blindness enforced by the tool layer is a fact — since 2.0.0 (#140) qa/<n> is cut after the implementation landed on the spec branch, so the branch carries the code and guard-blind rule E is the blindness, for the fidelity dispatch and the QA dispatch alike." (amended for #81, 1.29.1: a suite under `src/` — the block's `<acceptance_dir>` — is never a read of the implementation; the regexes are unchanged, the exemption sits outside them; amended for #94: a `src` segment anywhere — a multi-module `<module>/src/test/…` — is a suite under src/; cannot-see recorded for #96: a forge read of the implementation CR — D6) |
| D3 | Every dispatch carries the seat's R&R row | replay | "The payload contains the seat's Owns / Never row." (a seat running without its contract produces plausible work, and nothing in the record shows the row was missing) |
| D4 | The acceptance suite changes only on qa/<n> | replay (no baseline yet) | "Acceptance tests are written on qa/<n> and reach spec/<n> by merge. Nothing else writes them on spec/<n> — not Edit, not a shell, not a script: an assertion edited next to the code it judges rewrites the verdict into an echo of the implementation." |
| D5 | The fidelity dispatch is blind under a templated implementation branch | replay + hook (guard-blind rule E, the marker's `feat=` line) | "The dispatching command's marker carries `feat=fix/paul/5/1`; checkout is `test/paul/5/1`; no executed tool call under the fidelity dispatch acts on `fix/paul/5/1` or reads `src/`." (under a `branch_template` the implementation branch is not a `feat/` ref, and D2's literal alone would read every touch of it as blind — issue #75) |
| D6 | The blind dispatch never opens the implementation CR | lint + replay (#96) | "Before the fidelity dispatch the main agent itself (no `parent_tool_use_id` — the scanner's listing is not the check) lists the implementation CR's and the spec CR's threads; the dispatch text carries `Amendment list:` with `folded at <ID>` / `unfolded` dispositions, or declares it `none`; no tool call under the dispatch names PR 102." (the brief's step zero sent the blind reviewer to implementation-CR threads — comments that quote the code; a forge call names no `src/`, so rule E cannot see it; ADMC #73's reviewer flagged it itself) |
| D7 | The fidelity dispatch reads the test port the marker names | hook (guard-blind rule E, the marker's `read=` lines) + lint + replay (defect 1.39.0-, #125) | "The marker carries `read=<path>` for every path `technical-spec.md`'s `**Test port**` line names; the dispatch text names the same paths; a tool call under the dispatch that reads a port file EXECUTES (not denied), and no executed call reads `src/` elsewhere or touches the implementation ref; the `**[reviewer] · fidelity**` summary is posted and the marker is gone." (ADMC #11's port lived in an existing unit-test file under `src/test/…`, outside `acceptance_dir`, and the blind reviewer could not read what the suite drives — #125) |
| D8 | The QA dispatch is blind by the hook and may run its suite | hook (guard-blind rule E, the marker's `seat=qa` line) + lint + replay (#140, 2.0.0) | "The QA dispatch runs between marker-on (`seat=qa`, `feat=`, `read=` the port) and marker-off, once; under it, at least one EXECUTED Bash runs `acceptance_test`, and no executed tool call reads `src/` outside `<acceptance_dir>` and the port or touches the implementation ref — a denied attempt is counted, never scored; the QA CR opens as a draft." (since 2.0.0 `qa/<n>` carries the implementation, so the hook is the blindness; QA clears its harness at (4) instead of burning (6)'s fix rounds — #140) |
| D9 | A QA red is a finding, never an assertion edit | replay (#140 ruling 4, 2.0.0) | "Seeded: the contract says X (an expired offer is not applied — `price` returns 10), the implementation returns Y (7), QA's assertion says X and fails. Pass: the suite pushed to `<qa-branch>` is still RED against the merged implementation (the assertion is unchanged) and the deliverable carries a finding naming the clause and the observed value — a `[qa]` thread on the spec CR, or the report. Fail: the suite is GREEN (the assertion now says Y), or no suite was pushed." (QA can now run its suite against the code before (6); an assertion bent to observed behaviour turns the verdict into an echo of the implementation — integrate's rule, moved to where the red is first seen) |

### E · questions and answers reach the right place

| ID | title | tier | ledger text |
|---|---|---|---|
| E1 | judgment quality | judgment, deferred | see `replay/README.md`, cannot-see #4 |
| E2 | A seat's questions reach the holder from any document | lint (defect 1.14.2-) + replay + hook (guard-gate rule D) | "Relocated verbatim into spec.md's Open Questions, tagged with the raising role, before threads are posted." (threads are the only objects the gates count; a question outside the threaded surface blocks nothing) |
| E3 | the implementer can stop and ask at stage (3) | lint (defect 1.12.0-) | — |
| E4 | the stage-(5) reviewer has the same route | lint (defect 1.12.0-) | — |
| E5 | An answer folds into the document that owns it | replay | "technical-spec.md is modified. The spec.md entry records the resolution and points at the clause." (folded as prose beside the question instead, the contract never changes, QA derives from the unchanged contract, and the defect ships with a resolved thread pointing at it) |
| E6 | A thread the human opens is an amendment, folded like an answer | replay | "`spec.md` on the remote carries the amendment; a `✅ [<role>] amended` reply; the thread resolved." (a human-opened thread has one comment and no `[role]` tag, so the answered-thread rule skipped it while patrol classified it actionable — every pass reported "no new answers" — issue #62) |
| E7 | A question's options reach the holder as a list | hook (guard-gate rule F) + lint | "Each question block carries at least two option bullets — `- (a) …`, `- (b) …`; a comment without them is denied before it posts." (a (2a) thread wrote the options as prose; the forge rendered them as one paragraph on the holder's phone, with nothing for the `3a` shorthand to point at — issue #109) |
| E8 | A top-level comment on the spec CR is heard as an amendment | replay + lint | "`spec.md` on the remote carries the amendment; a top-level `✅ [product] amended` reply cites the comment; labels end `in-spec-review` alone, no STOP." (spec-answers read THREADS-LIST only, so the human's top-level comment — the PR page's default affordance, the only one usable from a phone — was never classified; every pass said "no new answers" — issue #98, E6's defect one channel over) |
| E9 | QA's contract review reaches the holder as `[qa]` spec-CR threads | lint + replay (#140 ruling 3, 2.0.0) | "QA's finding batch is posted by the main agent as `**[qa] · Q<k> · <label>**` threads on the spec CR (rule F bullets), `in-spec-review` applied, the item appended to `spec.md`'s Open Questions; the QA CR opens and stays a draft; spec-answers' mid-flight re-entry resumes qa." (a contradiction between the as-built contract and a spec rule, found by QA's first step, is a question for the holder — never interpreted into a test, never left in QA's report where no gate reads it) |
| E10 | the implementation CR declares its contract deviations | hook (guard-gate rule H) + lint (#140, 2.0.0) | — |

### F · the loop end to end

| ID | title | tier | ledger text |
|---|---|---|---|
| F1 | A quiet loop stays quiet | replay | "Report says no action. Zero label writes, zero comments, one dispatch — the scanner — and no other, no processing left behind." (amended for #59: the scan is a read-only sub-agent) |
| F2 | One review turn answers exactly what was asked | replay | "Exactly three `· answer` replies, each citing its item's URL; zero threads resolved; lock taken and released; in-user-review retained." (two answers = an item dropped silently; four = one answered twice; a resolved thread = the agent closed a question that was not its own) |
| F3 | Spec refinement lands a complete set | replay | "Both spec documents exist; the CR is open; the number of posted threads equals the number of entries in Open Questions; labels flipped exactly once; no question left in any other document." (the thread count catches a question written but never surfaced — the E2 failure, detected by arithmetic) |
| F4 | A green verdict makes the claim it is entitled to | replay (seed amended for #95: the QA CR carries the fidelity record) | "Both merged, suite captured, branch pushed, in-user-review applied — and the claim printed reads 'green against the pre-rework spec, at SHA x', never 'verified'." (the weakened claim is one sentence in a long command, exactly the kind that silently reverts to the confident phrasing) |
| F5 | A STOP leaves nothing half-done | replay | "Labels are blocked alone; an issue comment names the claims and the remedy; no branch pushed, no CR opened, no remote write of any kind." (five obligations in one paragraph; four of five honoured looks like success in every log) |
| F6 | Compliance survives a long session — instrument, not assert | replay (instrument only) | "The same command run as turn 1, 3, 5, 8 and 12 of one session. Record the compliance rate at each position. No pass mark." (amended — see below) |
| F7 | A branch is cut from the configured base, not the trunk | replay | "`spec/<n>` descends from `origin/<default_branch>` and the CR targets it — with `default_branch` naming a release branch while `main` and an older release branch also exist." (the only base ever exercised was `main`; a loop that always cut from the trunk measured 100% — issue #38) |
| F8 | A command leaves the user's checkout as it found it | replay | "HEAD is still main, the uncommitted edit and the untracked file are intact, no linked worktree is left behind, and spec/<n> reached the remote." (every earlier seed ran in a clean clone, where a checkout in the user's tree is invisible — issue #37) |
| F9 | A pass acts from the scanner's table | replay | "The scanner's table has a row per issue with the right verdict; the pass acts on the top actionable row, locks no other loop issue, posts every intake batch; the scanner writes nothing; the main agent lists nothing after the table." (the scan used to live in the main agent's context — #59) |
| F10 | A branch is cut by the configured template | replay | "`spec/paul/5/1` descends from `origin/<default_branch>`, the CR's head is that branch and targets the base, no `spec/5` and no `fix/paul/5/1` exists on the remote." (every seed before this one ran the default names, so a loop that hardcoded them measured 100%; the `type: fix` label on the fixture is the tempting wrong render for the spec branch — issue #75) |
| F11 | A pass reports in the template | replay | "The report's must-read is the template's table with a row per scanned issue and none for the filtered-out one; no row cites a previous pass; every `this pass` cell is one clause within the cap; every `needs you` row is a queue item with a link and the queue has nothing else; the filter line is present." (the pasted report of #124: key/value blocks, seven issues folded into "same as previous pass", a queue without links, a flip-flop only in Details) |
| F12 | tip names the next move and writes nothing | replay (#121) | "The answer names `status: ready-for-dev` as the human's move and `next-stage` as the loop's, and links the spec CR; the journal carries zero writes, no dispatch happened, #5's labels are as seeded, the remote's refs are byte-identical." (a read-only command measured as one: the tempting write is the label it recommends) |
| F13 | A bot-applied gate label dispatches nothing | replay (#144) | "Both bot-labelled issues are `illegal:` rows with `needs you: yes` and queue items with links; the journal shows the label-events read for each and no write on either — no lock, no finalize, no CR; their labels are as seeded." (the gate label the hook cannot stop: a foreign bot's `labeled` event is the only evidence, and every earlier fixture had no actor at all) |

**Amendment — F6.** The original text measured turns 1, 3, 5 and 10. The
driver (`replay/cases/F6/drive.py`, `MEASURED`) runs a 12-turn session and
measures 1, 3, 5, 8 and 12 — past the published median first omission
around step four — and both eval READMEs report that curve. The ledger
text follows the experiment; the driver's citation was updated to match.

### J, L · lint-only

| ID | title | tier |
|---|---|---|
| J1 | the judgment fixtures are frozen at T | lint (preventive) |
| L1 | one stage map | lint (preventive) |
| L2 | the local keys `roz-config` accepts are the ones the commands read and README documents — six since 2.4.0: `helper_model` governing the scanner and the commit sub-agent only, `branch_user` the `{user}` slot of `branch_template`, `branch_template` itself per developer | lint (defect 1.18.0) |
| L3 | every commit a command makes goes through the commit sub-agent's brief | lint (preventive) |
| L4 | branch names are bound once, never spelled — every command resolves `<spec-branch>` / `<feat-branch>` / `<qa-branch>` / `<fast-branch>` through `references/branch-names.md`; no literal `spec/<n>` outside it; `init` creates the `type:` labels; both adapters carry WHOAMI; the hooks read the template | lint (preventive, #75) |
| L5 | the config block has two homes — `CLAUDE.md`, then `CLAUDE.local.md`, in the toplevel, then in the main checkout; the hooks' one reader (`hooks/config_block.py`), the acceptance prefilter, every command's step 0 and the docs agree | lint (defect 1.31.1-, #94) |
| L6 | `test` and `acceptance_test` are documented as running in a linked worktree, never in the checkout, on every surface an adopter fills them in — README's config block, init's prompt, the onboarding builder — with the `.git`-as-a-directory failure named | lint (defect 1.36.0-, #99) |
| L7 | the wire spec names exactly the labels the state machine has, states the STOP and summary rules in the client's literals, binds no reference-client internal as a MUST, and every entry point links the pages | lint (preventive) |
| L8 | `/roz-gate:config` is answered by a mod that only reads and runs `bin/roz-config`; `commands/config.md` stays as the fallback where mods do not load | lint (#164, 2.3.0) |
| L9 | Every page says patrol answers every human comment on an intake thread on its next pass, and none still hands the thread to the humans | lint (defect 2.4.0-, #174) |

## The judgment corpus

A separate namespace: seven items from the ADMC history where an agent's
question changed the human's design — P1, P2, P8, P12 (should be raised)
and N1, N5, N10 (should not). Their checkable propositions are
`judgment/criteria.json`; see `judgment/README.md`.
