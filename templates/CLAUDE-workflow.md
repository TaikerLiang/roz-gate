## Development Workflow (Gated Loop)
<!-- gated-loop workflow v{{PLUGIN_VERSION}} -->

This repo runs the **Gated Loop** (Claude Code plugin `gated-loop`): an idea
becomes a shipped feature through a labelled, role-driven loop — spec debate,
blind black-box QA, independent review, an integration verdict — and the human
guards every gate.

The workflow doc is **not copied here** — it ships with the plugin, at
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`, so a plugin upgrade takes
effect everywhere at once. Read it before acting on any gated-loop issue.
Angle-bracket values in it (`<specs_dir>`, `<acceptance_dir>`) resolve from
the config below.

### Gated Loop config

- forge: {{FORGE}}
- default_branch: {{DEFAULT_BRANCH}}
- test: {{TEST}}
- acceptance_dir: {{ACCEPTANCE_DIR}}
- acceptance_test: {{ACCEPTANCE_TEST}}
- env_sync: {{ENV_SYNC}}
- lockfile: {{LOCKFILE}}
- lockfile_regen: {{LOCKFILE_REGEN}}
- specs_dir: {{SPECS_DIR}}
