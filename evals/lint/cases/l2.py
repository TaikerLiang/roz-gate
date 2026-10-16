"""L2 · the local keys roz-config accepts are the ones the commands read and
README documents — a key settable but read nowhere is a silent no-op,
a key read from the block is a team value pretending to be yours
(defect: 1.18.0-, #55)
1.28.0 (#66): helper_model is the fourth key — the scanner's and the
commit sub-agent's model; patrol_model (the block, patrol's seats) is
retired and must survive nowhere in the prose. 1.29.0 (#75):
branch_user is the fifth — the {user} slot of branch_template (L4).
"""

import re

from lib.lintkit import c, dirs_text, read, section, src

META = {
    "id": 'L2',
    "title":
        'the local keys `roz-config` accepts are the ones the commands read and README '
        'documents — five since 1.29.0: `helper_model` governing the scanner and the commit '
        'sub-agent only, `branch_user` the `{user}` slot of `branch_template`',
    "tier": 'lint (defect 1.18.0)',
    "ledger": None,
}

_tool = read("bin/roz-config")
_m = re.search(r'^KEYS = \((.*?)\)$', _tool, re.M)
_tool_keys = tuple(re.findall(r'"([a-z_]+)"', _m.group(1))) if _m else ()
c.expect("pattern", "L2: bin/roz-config accepts exactly the five local keys",
         _tool_keys == ("default_branch", "inbox_label", "inbox_assignee", "helper_model",
                        "branch_user"))
_readers = ("commands/patrol.md", "commands/next-stage.md", "commands/integrate.md",
            "commands/spec-answers.md", "commands/review-answers.md")
for _f in _readers:
    src("L2: %s reads the local keys through roz-config --json" % _f, _f, "bin/roz-config --json")
    _blk = re.search(r"config` block in the project's CLAUDE\.md \(([^)]*)\)", read(_f))
    c.expect("pattern", "L2: %s does not read default_branch from the block" % _f,
             _blk is None or "default_branch" not in _blk.group(1))
for _k in _tool_keys:
    src("L2: README documents %s under /roz-gate:config" % _k, "README.md",
        "/roz-gate:config %s" % _k)
    src("L2: /roz-gate:config's menu names %s" % _k, "commands/config.md", "`%s`" % _k)
_pat = read("references/patrol-scan.md")
c.expect("pattern", "L2: the inbox keys are lists — any of, both must hold, empty = no filter",
         "**any** of its labels" in _pat and "**any** of its logins" in _pat
         and "an empty list is no\n  filter" in _pat)
c.expect("pattern", "L2: a filtered-out issue is counted, never acted on",
         "not in the inbox filter" in _pat
         and re.search(r"never\s+commented on, never locked, never listed", _pat) is not None)
c.expect("pattern", "L2: the filter is inbox-only — track: issues advance regardless",
         "The filter applies to the inbox alone" in _pat)
_cfg = read("commands/config.md")
c.expect("pattern", "L2: /roz-gate:config is only the menu — bin/roz-config does the write",
         _cfg.count('bin/roz-config"') >= 3 and "never edit `.claude/roz-gate.local.json`" in _cfg)
c.expect("pattern", "L2: /roz-gate:config never touches the block or the forge",
         "or `CLAUDE.local.md`\nyourself" in _cfg and "never create forge labels" in _cfg
         and "LABEL-LIST" not in _cfg)
c.expect("pattern", "L2: /roz-gate:config splits inbox values on commas and quotes each",
         "comma-separated" in _cfg and "never split on spaces" in _cfg
         and '"<v1>" "<v2>"' in _cfg)
c.expect("pattern", "L2: /roz-gate:config injects the tool's current values into the prompt",
         '!`python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config"`' in _cfg)
src("L2: roz-config migrates a pre-1.23 block once (upgrade path, codex review)",
    "bin/roz-config", "def migrate(root, path, stored):")
src("L2: the template still carries the block (specs_dir)", "templates/claude-workflow.md",
    "- specs_dir:")
c.expect("pattern", "L2: the template has no default_branch line",
         "default_branch" not in read("templates/claude-workflow.md"))
src("L2: GitHub ISSUE-LIST returns assignees (the inbox filter reads them)",
    "references/forge-github.md", "--json number,title,labels,assignees,author,createdAt")
_pm = read("commands/patrol.md")
_model = section(_pm, r"^\*\*Model\*\*", r"^$")
c.expect("pattern", "L2: patrol's Model paragraph: helper_model is the scanner's and the "
         "commit sub-agent's, from roz-config, never the seats'",
         "`helper_model`" in _model and "scanner" in _model and "commit" in _model
         and "roz-config" in _model
         and re.search(r"seats?\b.*runtime", _model, re.S | re.I) is not None)
c.expect("pattern", "L2: patrol dispatches the scanner on helper_model",
         "helper_model" in section(_pm, r"^## 1\. Dispatch the scanner", r"^## 2\. "))
c.expect("pattern", "L2: README's block has no patrol_model line; the per-clone section has five",
         "- patrol_model" not in read("README.md") and "Five keys are **yours" in read("README.md"))
c.expect("pattern", "L2: patrol_model survives nowhere in the prose or the docs",
         "patrol_model" not in dirs_text("commands", "references", "templates", "docs")
         and "patrol_model" not in read("README.md"))
c.expect("pattern", "L2: the onboarding builder offers helper_model as a per-clone key",
         "helper_model" in read("docs/onboarding.html"))
src("L2: roz-config seeds helper_model from an old patrol_model line", "bin/roz-config",
    '"patrol_model"')
