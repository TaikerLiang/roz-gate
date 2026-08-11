# Agent identity — one-time setup

How to give the agent its own forge identity for `agent_identity: bot`
mode. **Creating credentials is always the human's task** — commands link
here; they never automate any step on this page. All facts below were
verified against live forges on 2026-08-10.

## GitHub — a GitHub App

1. **Register the App** (browser): Settings → Developer settings →
   GitHub Apps → New GitHub App (under your user or org).
   - Name: anything; the app **slug** derived from it is your
     `bot_login` (comments will render as `<slug>[bot]`).
   - Webhook: **uncheck Active** — roz-gate polls; no webhook needed.
   - Repository permissions (least privilege):
     **Issues: Read & write · Pull requests: Read & write ·
     Contents: Read & write · Metadata: Read-only** (automatic).
     Everything else: No access.
2. **Install it** on the repo(s) the loop runs in (Install App → choose
   "Only select repositories").
3. **Collect credentials**: note the **App ID** (About page) and generate
   a **private key** (.pem). Store the .pem **outside every repo** (e.g.
   `~/.config/roz-gate/<slug>.pem`, mode 600).
4. **Config block** (project CLAUDE.md, `### Roz Gate config`):
   - `agent_identity: bot`
   - `bot_login: <slug>`
   - `operator: <your GitHub login>`
5. **Tokens at run time**: installation tokens are short-lived (~1 hour).
   Mint per run with the bundled helper:
   `${CLAUDE_PLUGIN_ROOT}/scripts/gh-app-token.sh <app-id> <key.pem> <owner>/<repo>`
   → prints a token for `GH_TOKEN=<token> gh …` (per invocation — never
   exported; see the forge adapter's Identity section).

Author shapes to expect for the same App: `app/<slug>` (gh `--json`
issue/PR author), bare `<slug>` (gh `--json comments`, GraphQL),
`<slug>[bot]` (REST). Compare with the prefix/suffix stripped.

## GitLab — a project access token

Works on gitlab.com free-tier personal projects and self-managed
instances; the sanctioned pattern where company policy forbids extra user
accounts.

1. **Create the token**: project → Settings → Access tokens (or via API
   with your personal session):
   - Role: **Maintainer** (verified level; lower may work for parts but
     is unmeasured), scopes: **`api`, `write_repository`**, expiry:
     required, max 1 year — rotation is your job; calendar it.
   - API variant (note: JSON body required — form encoding of `scopes`
     fails):
     `glab api -X POST -H 'Content-Type: application/json' projects/<id>/access_tokens --input -`
     with `{"name":"roz-bot","scopes":["api","write_repository"],"access_level":40,"expires_at":"<date>"}`.
2. **Find the bot username**: creating the token creates a project bot
   member, `project_<id>_bot_<hash>` —
   `GITLAB_TOKEN=<token> glab api user` shows it. That full username is
   your `bot_login`.
3. **Config block**: `agent_identity: bot`, `bot_login: project_<id>_bot_<hash>`,
   `operator: <your GitLab username>`.
4. **Run time**: the token is a static value — pass it per invocation as
   `GITLAB_TOKEN=<token> glab …` (CLI subcommands and `glab api` both
   honor it). Git pushes: `https://<any-name>:<token>@gitlab.com/<path>.git`.

## Security rules (both forges)

- The bot credential is passed **per invocation only** — never `export`ed
  into the session, never written into git config or any repo file.
- Revocation: GitHub — uninstall the App or delete the key; GitLab —
  revoke the token (Settings → Access tokens).
- The human's own CLI auth (`gh auth login` / `glab auth login`) stays
  untouched — it is what everything outside CAPITALIZED-OPs runs as.
