#!/usr/bin/env bash
# C11 sandbox: C10's shape under a branch_template with {seq} (the local file's, 2.4.0). spec/paul/5/1
# still exists from a first attempt whose spec CR was closed unmerged
# (state.json: PR 101 CLOSED), and spec/paul/5/3 from a later abandoned one
# (PR 103 CLOSED) — the human removed /2 by hand, so the sequences have a
# gap (#135). The issue wears ready-for-spec again. The cut must NOT stop,
# and the next attempt is 1 + max({seq}) = spec/paul/5/4 — not 1 + count
# (= 3, an existing ref). Both earlier attempts stay exactly as they were.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
mkdir -p .claude && printf '{"branch_user": "paul", "branch_template": "{type}/{user}/{n}/{seq}"}\n' > .claude/roz-gate.local.json
grep -q '"branch_user": "paul"' .claude/roz-gate.local.json
grep -q '"branch_template": "{type}/{user}/{n}/{seq}"' .claude/roz-gate.local.json
printf '.claude/roz-gate.local.json\n' >> .git/info/exclude
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -q --allow-empty -m "seed (branch_template)"
git checkout -qb spec/paul/5/1
mkdir -p docs/specs/5
printf '# Spec #5 — first attempt\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5 (first attempt)"
git checkout -q main
git checkout -qb spec/paul/5/3
mkdir -p docs/specs/5
printf '# Spec #5 — third attempt (abandoned)\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5 (third attempt)"
git checkout -q main
