# Forge adapter — GitHub (`gh`)

Concrete CLI for every forge operation the gated-loop commands name. All `gh`
calls infer the repository from the current directory's git remote — never pass
`--repo`. Vocabulary: a **change request (CR)** is a GitHub **Pull Request**.

Prerequisite: `gh auth status` succeeds for the remote's host.

## Issues & labels

| Op | Command |
|---|---|
| ISSUE-LIST | `gh issue list --state open --json number,title,labels,createdAt` (add `--label "<label>"` to filter) |
| ISSUE-VIEW | `gh issue view <n> --json title,body,labels,comments` |
| LABEL-ADD | `gh issue edit <n> --add-label "<label>"` |
| LABEL-REMOVE | `gh issue edit <n> --remove-label "<label>"` |
| ISSUE-COMMENT | `gh issue comment <n> --body "..."` |
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
| CR-FIND | `gh pr list --head <branch> --state open --json number,title,isDraft,baseRefName` |
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

## Bootstrap (used by /gated-loop:init)

| Op | Command |
|---|---|
| LABEL-CREATE | `gh label create "<label>" --color <hex> --description "..."` (idempotent-ish: add `--force` to update) |
| ISSUE-TEMPLATE-PATH | `.github/ISSUE_TEMPLATE/idea.md` |

Suggested colors: `track: *` `#1d76db`; gates `#0e8a16`; transient `#fbca04`;
`status: blocked` `#d93f0b`; `status: processing` `#c5def5`.
