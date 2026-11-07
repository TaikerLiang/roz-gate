#!/usr/bin/env bash
# The QA-frame seeds' shared step (#199). Sourced by a D10–D19 seed.sh
# after seed-common.sh, with ROOT set:
#
#     qa_fixture <name>     # copies evals/replay/fx/<name>/ into the sandbox,
#                           # points config acceptance_test at the shared
#                           # runner (D4's: a verdict on the last stdout line,
#                           # no tests = failure) and commits on main
#
# The fixture tree is hashed into the case's fingerprint (case.json's
# "fixture" key, replaylib.case_fingerprint), so a change here or under fx/
# makes the recorded runs stale, never silently current.
qa_fixture() {
  local fx="$ROOT/evals/replay/fx/$1"
  [ -d "$fx" ] || { echo "qa-fixture: no fixture $1 under evals/replay/fx" >&2; exit 1; }
  cp -R "$fx"/. .
  rm -rf extras   # a fixture's optional parts are copied by the seed that wants them
  [ -f bin/serve ] && chmod +x bin/serve
  cp "$ROOT/evals/replay/fx/common/run_acceptance.py" run_acceptance.py
  sed -i.bak 's|^- acceptance_test: true$|- acceptance_test: python3 run_acceptance.py|' CLAUDE.md
  rm CLAUDE.md.bak
  grep -q '^- acceptance_test: python3 run_acceptance.py$' CLAUDE.md
  printf '__pycache__/\n*.tmp\nkv.json\n' > .gitignore
  git add -A
  git -c user.email=paul@example.com -c user.name=paul commit -qm "fixture: $1; acceptance_test runs the suite"
}
