#!/usr/bin/env python3
"""D28's red-proof: check.py scores staged runs correctly. No model, no
sandbox — D28 reads the transcript's init event, its dispatch payloads and
its Bash calls; each shape stages them and check.py runs.

    python3 evals/replay/cases/D28/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/private/var/folders/xy/T/roz-replay-abc/plugin"
OTHER = "/Users/op/.claude/plugins/cache/roz-gate/roz-gate/2.7.1"
ROW = ("You are the product seat for issue #9. Your R&R row: Owns: actors, scenarios, "
       "consistency, user-facing gaps. Never: architecture, code, impl tests. ")
WITH_ROOT = ROW + ("Plugin root: %s — plugin paths resolve here; never search for plugin "
                   "files.\nRead the intake brief: %s/references/intake-brief.md" % (ROOT, ROOT))
# The 2026-11-16 sweep's shape (#358): the variable passed on unexpanded.
LITERAL = ROW + "Read the intake brief: ${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md"
BARE = ROW + "Read references/intake-brief.md and follow it."
WRONG_ROOT = ROW + "Plugin root: %s\nRead %s/references/intake-brief.md" % (OTHER, OTHER)
FIND = 'find / -name workflow.md -path "*roz-gate*" 2>/dev/null | head -1'
ECHO = 'echo "$CLAUDE_PLUGIN_ROOT"; ls "$CLAUDE_PLUGIN_ROOT/references"'
SPECS = "find . -name '*.md' -path '*specs*'"

# (name, expected exit: 0 pass / 1 fail / 3 invalid, init root or None,
#  product dispatch prompt or None, Bash commands)
SHAPES = [
    ("the payload names the loaded root, no search", 0, ROOT, WITH_ROOT, []),
    ("a project-only find (specs) is not a plugin search", 0, ROOT, WITH_ROOT, [SPECS]),
    ("the payload passes ${CLAUDE_PLUGIN_ROOT} on literally (#358)", 1, ROOT, LITERAL, []),
    ("the payload says only references/… (#358)", 1, ROOT, BARE, []),
    ("the payload names another roz-gate copy (cached 2.7.1)", 1, ROOT, WRONG_ROOT, []),
    ("root carried, but a seat still runs find / -name workflow.md", 1, ROOT, WITH_ROOT,
     [FIND]),
    ("the sweep's run: literal payload, then echo + find", 1, ROOT, LITERAL, [ECHO, FIND]),
    ("no product dispatch at all", 3, ROOT, None, []),
    ("no roz-gate path in the init event", 3, None, WITH_ROOT, []),
]


def transcript(root, prompt, cmds):
    plugins = [{"name": "cc-plugin-x", "source": "x@builtin"}]
    if root:
        plugins.append({"name": "roz-gate", "path": root})
    ev = [{"type": "system", "subtype": "init", "plugins": plugins, "mcp_servers": []},
          {"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "s0", "name": "Task",
               "input": {"subagent_type": "general-purpose",
                         "prompt": "Read %s/references/patrol-scan.md …" % ROOT}}]}}]
    if prompt is not None:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "p1", "name": "Task",
             "input": {"subagent_type": "roz-gate:product", "prompt": prompt}}]}})
    for i, cmd in enumerate(cmds):
        ev.append({"type": "assistant", "parent_tool_use_id": "p1", "message": {"content": [
            {"type": "tool_use", "id": "b%d" % i, "name": "Bash", "input": {"command": cmd}}]}})
    ev.append({"type": "result", "result": "patrol: #9 intake batch posted."})
    return ev


def check(tmp, root, prompt, cmds):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    shutil.copy(os.path.join(CASE, "state.json"), os.path.join(run, "forge", "state.json"))
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(root, prompt, cmds):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE="")
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp = tempfile.mkdtemp()
    try:
        for name, want, root, prompt, cmds in SHAPES:
            p = check(tmp, root, prompt, cmds)
            ok = p.returncode == want
            verdict = {0: "pass", 1: "fail", 3: "invalid"}[want]
            print("%s D28 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
