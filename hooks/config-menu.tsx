// /roz-gate:config without a model turn (#164). This mod answers the
// markdown command `commands/config.md` itself; where the mod does not load
// (Claude Code < 2.1.287, --safe-mode, disableAllHooks) that prompt runs as
// the fallback. It is a menu and nothing else: `bin/roz-config` reads and
// writes the keys — this module never writes a file, never asks the forge
// or a model, and runs nothing but that tool.
import type { EngineInterface, Register } from 'claude-code'

const COMMAND = 'roz-gate:config'
const PANE = 'roz-gate-config'
const KEYS = ['default_branch', 'inbox_label', 'inbox_assignee', 'helper_model', 'branch_user']
const HINT: Record<string, string> = {
  default_branch: "one branch; empty = the remote's HEAD",
  inbox_label: 'labels, comma-separated; empty = no filter',
  inbox_assignee: 'logins, comma-separated; empty = no filter',
  helper_model: "one model id; empty = the runtime's",
  branch_user: 'one forge login; empty = yours',
}

type Values = Record<string, string | string[]>
type Answer = { text: string; exitCode: number }

let values: Values = {}
let selected = 'default_branch'
let last = ''

const shown = (v: string | string[] | undefined) =>
  (Array.isArray(v) ? v.join(', ') : v) || '-'

// Runs bin/roz-config with an argument list — no shell, so a label with
// spaces stays one argument; the tool splits list keys on commas.
async function tool($: EngineInterface, args: string[]): Promise<Answer> {
  const path = $.plugin.root + '/bin/roz-config'
  try {
    const r = await $.process.run(['python3', path, ...args])
    const out = (r.exitCode === 0 ? r.stdout : r.stderr || r.stdout).trim()
    return { text: out, exitCode: r.exitCode }
  } catch (err) {
    const why = err instanceof Error ? err.message : String(err)
    return {
      text: `roz-gate: could not run bin/roz-config (${why}) — run \`python3 ${path} ${args.join(' ')}\` yourself`,
      exitCode: 1,
    }
  }
}

async function load($: EngineInterface) {
  const r = await tool($, ['--json'])
  if (r.exitCode === 0) values = JSON.parse(r.text)
  else last = r.text
}

export const register: Register = on => {
  on('command.run', { command: COMMAND }, async ($, e) => {
    const typed = e.args.trim()
    if (typed) {
      // The first word is the key; the rest goes as one argument.
      const gap = typed.search(/\s/)
      const key = gap < 0 ? typed : typed.slice(0, gap)
      const rest = gap < 0 ? '' : typed.slice(gap).trim()
      return tool($, rest ? [key, rest] : [key])
    }
    last = ''
    await load($)
    const opened = await $.ui.open({ id: PANE, title: 'roz-gate config', focus: true, closeOnEscape: true })
    if (opened.isPlaced) return {}
    // Nothing draws here (claude -p, a cloud session): print the values.
    await $.ui.close({ id: PANE })
    return tool($, [])
  }).catch(() => ({ text: 'roz-gate: the config menu failed — run bin/roz-config yourself', exitCode: 1 }))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const table = $.ui.resolve(e)
    const { Box, Text } = table
    if (e.surface === 'mobile' || !('Select' in table)) {
      // A surface with no fields (mobile): the values, and how to set one.
      return (
        <Box flexDirection="column">
          {KEYS.map(k => <Text>{`${k}  ${shown(values[k])}`}</Text>)}
          <Text dimColor>{"Set one with /roz-gate:config <key> <value>."}</Text>
        </Box>
      )
    }
    const { Select, Input } = table
    const set = async (typed: string) => {
      const r = await tool($, typed.trim() ? [selected, typed] : [selected])
      last = r.text
      await load($)
      $.ui.invalidate('ui.render')
    }

    return (
      <Box flexDirection="column">
        <Select
          key="key"
          label="Key"
          options={KEYS.map(k => ({ value: k, label: `${k}  ${shown(values[k])}` }))}
          value={selected}
          autoFocus
          onSelect={(k: string) => {
            selected = k
            last = ''
            $.ui.invalidate('ui.render')
          }}
        />
        <Input
          key="value"
          label="Value"
          placeholder={HINT[selected]}
          value={shown(values[selected]) === '-' ? '' : shown(values[selected])}
          submitLabel="set"
          onSubmit={set}
        />
        {last !== '' && <Text>{last}</Text>}
        <Text dimColor>The write is bin/roz-config's; Esc closes.</Text>
      </Box>
    )
  }).catch(() => undefined)
}
