# Forge adapter — GitHub (`gh`)

Concrete CLI for every forge operation the roz-gate commands name. All `gh`
calls infer the repository from the current directory's git remote — never pass
`--repo`. Vocabulary: a **change request (CR)** is a GitHub **Pull Request**.

Prerequisite: `gh auth status` succeeds for the remote's host.

## Identity

Two modes, set by `agent_identity` in the Roz Gate config (key absent →
`user`):

- **`user`** (default): every op runs as the human's `gh auth login`
  session — the pre-1.7.0 behavior, unchanged.
- **`bot`**: every CAPITALIZED-OP runs as the project's GitHub App
  (`bot_login` = the app slug; one-time setup in
  `references/identity-github-app.md`):
  - Mint a short-lived installation token
    (`${CLAUDE_PLUGIN_ROOT}/scripts/gh-app-token.sh`) and pass it
    **per invocation**: `GH_TOKEN=<token> gh …`. **Never export it into
    the session environment** — a bare `gh` outside a CAPITALIZED-OP must
    keep the human's identity.
  - ISSUE-CREATE always adds `--assignee <operator>` (the config's
    `operator`) — a bot-authored issue must never be born holder-less; a
    bot is never a gate holder.
  - Git: push over HTTPS —
    `git push https://x-access-token:<token>@github.com/<owner>/<repo>.git <branch>`
    — and commit with per-command author flags,
    `git -c user.name="<slug>[bot]" -c user.email="<app-id>+<slug>[bot]@users.noreply.github.com" commit …`,
    never writing identity into the repo's git config (the human's own
    commits in the same clone stay theirs).
  - Author shapes differ by API path (`app/<slug>`, `<slug>[bot]`, bare
    `<slug>`) — when comparing, strip the `app/` prefix and `[bot]`
    suffix first.

## Issues & labels

| Op | Command |
|---|---|
| ISSUE-LIST | `gh issue list --state open --json number,title,labels,createdAt` (add `--label "<label>"` to filter) |
| ISSUE-VIEW | `gh issue view <n> --json title,body,labels,comments` |
| LABEL-ADD | `gh issue edit <n> --add-label "<label>"` |
| LABEL-REMOVE | `gh issue edit <n> --remove-label "<label>"` |
| ISSUE-COMMENT | `gh issue comment <n> --body "..."` |
| COMMENT-EDIT | `gh api -X PATCH repos/<owner>/<repo>/issues/comments/<comment-id> -f body="..."` (top-level issue/CR comments; id from the comment's URL or listing) |
| ISSUE-CREATE | `gh issue create --title "..." --body "..." [--label "<label>"]` |
| ISSUE-EDIT-BODY | `gh issue edit <n> --body "..."` (async intake only, after the user's `approve`) |

Label names use the **space form**: `track: spec`, `track: fast`,
`status: ready-for-spec`, `status: ready-for-dev`, `status: in-spec-review`,
`status: in-user-review`, `status: processing`, `status: blocked`.

## Change requests

| Op | Command |
|---|---|
| CR-OPEN | `gh pr create --base <target> --head <branch> --title "..." --body "..."` |
| CR-OPEN-DRAFT | same + `--draft` |
| CR-READY | `gh pr ready <pr>` |
| CR-FIND | `gh pr list --head <branch> --state open --json number,title,isDraft,baseRefName` (`--state all` when a command must also see merged CRs) |
| CR-VIEW | `gh pr view <pr> --json number,title,isDraft,state,headRefName` |
| CR-MERGE | `gh pr merge <pr>` (the human's act at (7) — commands never run this) |

## Review threads

Inline threads ride the REST comments API; thread state rides GraphQL.

**THREADS-LIST** — all threads with resolution state and comments:

```
gh api graphql -f query='
query($owner:String!,$repo:String!,$pr:Int!){
  repository(owner:$owner,name:$repo){ pullRequest(number:$pr){
    reviewThreads(first:100){ nodes{
      id isResolved
      comments(first:50){ nodes{ databaseId body author{login} createdAt } }
    } }
  } }
}' -F owner=<owner> -F repo=<repo> -F pr=<pr>
```

(Resolve `<owner>`/`<repo>` once per run: `gh repo view --json owner,name`.)

**THREAD-POST-INLINE** — open a thread anchored to a file line (one call per
question/finding; `SHA` = head commit of the CR's branch):

```
gh api -X POST "repos/<owner>/<repo>/pulls/<pr>/comments" \
  -f body="..." -f commit_id="$SHA" -f path="<file>" -F line=<line> -f side=RIGHT
```

**THREAD-REPLY** — reply within an existing thread (use the `databaseId` of the
thread's first comment):

```
gh api -X POST "repos/<owner>/<repo>/pulls/<pr>/comments/<databaseId>/replies" \
  -f body="..."
```

**THREAD-RESOLVE** — mark resolved (use the thread's GraphQL node `id`):

```
gh api graphql -f query='mutation($t:ID!){
  resolveReviewThread(input:{threadId:$t}){ thread{ isResolved } } }' -F t=<thread-id>
```

## The other two comment channels

A human reviews in three places, and inline threads are only one of them.
**Read every channel you write into** — an unread channel is one intact copy
of "the user's comments went unheard".

**REVIEWS-LIST** — review summary bodies. A `CHANGES_REQUESTED` review whose
whole content is its body carries no inline comment and appears in neither
THREADS-LIST nor the comments endpoint:

```
gh api repos/<owner>/<repo>/pulls/<pr>/reviews \
  --jq '.[] | {id, state, body, author: .user.login, submitted_at}'
```

States: `COMMENTED` / `CHANGES_REQUESTED` / `APPROVED` (a non-empty body counts
on all three; `PENDING` is invisible to the API by design — an unsubmitted
draft is not yet addressed to anyone).

**CR-COMMENTS-LIST** — top-level CR comments. They live on the *issues*
endpoint, not the pulls one, and they are the default affordance on the PR page
— the reply a human types on a phone lands here:

```
gh api repos/<owner>/<repo>/issues/<pr>/comments \
  --jq '.[] | {id, body, author: .user.login, created_at, html_url}'
```

## Bootstrap (used by /roz-gate:init)

| Op | Command |
|---|---|
| LABEL-CREATE | `gh label create "<label>" --color <hex> --description "..."` (idempotent-ish: add `--force` to update) |
| LABEL-DELETE | `gh label delete "<label>" --yes` (erases it from closed issues too — `/roz-gate:uninit` only, on explicit request) |
| ISSUE-TEMPLATE-PATH | `.github/ISSUE_TEMPLATE/idea.md` |

Suggested colors: `track: *` `#1d76db`; gates `#0e8a16`; transient `#fbca04`;
`status: blocked` `#d93f0b`; `status: processing` `#c5def5`.
