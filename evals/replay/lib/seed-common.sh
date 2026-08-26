#!/usr/bin/env bash
# Seeds the sandbox repo every case starts from: the workflow section a
# /roz-gate:init would have written (current template stamp), plugin-default
# personas, and the instantiated implementer agent. $1 = plugin root.
set -eu
ROOT="$1"
STAMP=$(grep -o '<!-- roz-gate workflow-template v[0-9]* -->' "$ROOT/templates/CLAUDE-workflow.md")

cat > CLAUDE.md <<EOF
## Development Workflow (Roz Gate)
$STAMP

This repo runs the **Roz Gate** (Claude Code plugin \`roz-gate\`). The
workflow doc ships with the plugin at
\${CLAUDE_PLUGIN_ROOT}/references/workflow.md. Read it before acting on any
roz-gate issue.

### Roz Gate config

- forge: github
- default_branch: main
- test: true
- acceptance_dir: tests/acceptance
- acceptance_test: true
- env_sync: none
- lockfile: none
- lockfile_regen: none
- specs_dir: docs/specs

### Roz Gate personas

- product: roz-gate:product
- em: roz-gate:em
- implementer: implementer
- qa: roz-gate:qa
- reviewer: roz-gate:reviewer
EOF

mkdir -p .claude/agents
cp "$ROOT/templates/implementer.md" .claude/agents/implementer.md
mkdir -p src tests/acceptance docs/specs
echo "demo" > src/app.txt

git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm seed
