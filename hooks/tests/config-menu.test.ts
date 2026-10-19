// hooks/config-menu.tsx — the /roz-gate:config mod (#164), run by
// `claude plugin test`. bin/roz-config never runs here: a stub answers
// $.process.run and records every argument list the mod passed it.
import { expect, test } from 'claude-code/testing'
import type { CommandRunInput } from 'claude-code'
import type { TestBody } from 'claude-code/testing'

type On = Parameters<TestBody>[1]

// The person's Enter at the prompt, on a terminal 100 columns wide.
const run = (args: string, command = 'roz-gate:config'): CommandRunInput => ({
  command, args, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 },
})

const JSON_OUT = JSON.stringify({
  default_branch: 'main', inbox_label: ['discuss'], inbox_assignee: [],
  helper_model: '', branch_user: '',
})

type Out = { exitCode: number; stdout: string; stderr: string }

function tool(on: On, calls: string[][], answer = (argv: string[]): Out => ({ exitCode: 0, stdout: 'ok\n', stderr: '' })) {
  on('process.run', ($, e) => {
    calls.push(e.argv.slice(2))
    expect(e.argv[0]).toBe('python3')
    expect(e.argv[1]).toMatch(/\/bin\/roz-config$/)
    const out = e.argv[2] === '--json'
      ? { exitCode: 0, stdout: JSON_OUT + '\n', stderr: '' }
      : answer(e.argv.slice(2))
    return { value: { ...out, isStdoutTruncated: false, isStderrTruncated: false } }
  })
}

const PANE = {
  plugin: 'roz-gate',
  component: 'Pane',
  requestId: 'roz-gate-config',
  viewport: { columns: 100, rows: 30 },
  props: {
    title: 'roz-gate config', isFocused: true, bodyColumns: 80, placement: 'inline',
    scroll: { offset: 0, bodyRows: 12 }, view: {},
  },
} as const

test('with arguments: the key, then the rest as one argument, to bin/roz-config', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls, () => ({ exitCode: 0, stdout: 'inbox_label set → discuss, good first issue\n', stderr: '' }))
  const r = await $.command.run(run('inbox_label discuss, good first issue'))
  expect(calls).toEqual([['inbox_label', 'discuss, good first issue']])
  expect(r.text).toBe('inbox_label set → discuss, good first issue')
})

test('a key alone is passed alone — the tool removes the override', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls)
  await $.command.run(run('  helper_model  '))
  expect(calls).toEqual([['helper_model']])
})

test("the tool's refusal is shown with its exit code", async ($, on) => {
  const calls: string[][] = []
  tool(on, calls, () => ({ exitCode: 2, stdout: '', stderr: "roz-config: unknown key 'model'\n" }))
  const r = await $.command.run(run('model x'))
  expect(r.text).toBe("roz-config: unknown key 'model'")
  expect(r.exitCode).toBe(2)
})

test('a tool that cannot start names the fallback', async ($, on) => {
  on('process.run', () => ({ deny: 'python3: not found' }))
  const r = await $.command.run(run("inbox_label good first issue, Paul's"))
  expect(r.text).toMatch(/could not run bin\/roz-config .*run `python3 '[^`]*\/bin\/roz-config' 'inbox_label' 'good first issue, Paul'\\''s'` yourself/)
  expect(r.exitCode).toBe(1)
})

test('another command passes through untouched', async ($, on) => {
  on('command.run', () => ({ text: 'the prompt ran' }))
  const r = await $.command.run(run('', 'roz-gate:patrol'))
  expect(r.text).toBe('the prompt ran')
})

test('no arguments where nothing draws: the pane closes and the values print', async ($, on) => {
  const calls: string[][] = []
  const closed: string[] = []
  tool(on, calls, () => ({ exitCode: 0, stdout: 'default_branch   main\n', stderr: '' }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no-surface' } }))
  on('ui.close', ($, e) => {
    closed.push(e.id)
    return { value: undefined }
  })
  const r = await $.command.run(run(''))
  expect(calls).toEqual([['--json'], []])
  expect(closed).toEqual(['roz-gate-config'])
  expect(r.text).toBe('default_branch   main')
})

test('no arguments where a pane draws: pick the key, submit the value', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls, argv => ({ exitCode: 0, stdout: `${argv[0]} set\n`, stderr: '' }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  const r = await $.command.run(run(''))
  expect(r).toEqual({})
  for (const surface of ['terminal', 'desktop'] as const) {
    calls.length = 0
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ key: 'key' })).toBeDefined()
    await ui.select({ key: 'key', value: 'inbox_label' })
    await ui.input({ key: 'value', text: 'discuss, good first issue' })
    expect(calls).toEqual([['inbox_label', 'discuss, good first issue'], ['--json']])
    expect(await ui.find({ type: 'Text', text: 'inbox_label set' })).toBeDefined()
    await ui.unmount()
  }
})

test('an empty submit passes the key alone', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls)
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.command.run(run(''))
  calls.length = 0
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.select({ key: 'key', value: 'branch_user' })
  await ui.input({ key: 'value', text: '  ' })
  expect(calls[0]).toEqual(['branch_user'])
})

test('a surface with no fields lists the values and the argument form', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls)
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.command.run(run(''))
  const ui = await $.ui.mount({ ...PANE, surface: 'mobile' })
  expect(await ui.find({ type: 'Text', text: 'inbox_label  discuss' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /\/roz-gate:config <key> <value>/ })).toBeDefined()
})

test('a submitted value is trimmed before the tool sees it', async ($, on) => {
  const calls: string[][] = []
  tool(on, calls)
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.command.run(run(''))
  calls.length = 0
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.select({ key: 'key', value: 'default_branch' })
  await ui.input({ key: 'value', text: '  release/20261020 ' })
  expect(calls[0]).toEqual(['default_branch', 'release/20261020'])
})

test("a failed load shows the tool's diagnostic, not stale values — on mobile too", async ($, on) => {
  on('process.run', () => ({
    value: { exitCode: 1, stdout: '', stderr: 'roz-config: not inside a git repository\n',
             isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.command.run(run(''))
  for (const surface of ['terminal', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: 'roz-config: not inside a git repository' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /discuss/ })).toBeUndefined()
    await ui.unmount()
  }
})

test("a successful run's stderr notice is shown, before the tool's line", async ($, on) => {
  const calls: string[][] = []
  tool(on, calls, () => ({ exitCode: 0, stdout: 'inbox_label set → discuss\n', stderr: 'roz-config: seeded from the CLAUDE.md block once\n' }))
  const r = await $.command.run(run('inbox_label discuss'))
  expect(r.text).toBe('roz-config: seeded from the CLAUDE.md block once\ninbox_label set → discuss')
})

test("the load's stderr notice is shown in the pane", async ($, on) => {
  on('process.run', () => ({
    value: { exitCode: 0, stdout: JSON_OUT + '\n', stderr: 'roz-config: seeded from the CLAUDE.md block once\n',
             isStdoutTruncated: false, isStderrTruncated: false },
  }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.command.run(run(''))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'roz-config: seeded from the CLAUDE.md block once' })).toBeDefined()
})

test("where nothing draws, the load's notice leads the listing, once", async ($, on) => {
  let first = true
  on('process.run', ($, e) => {
    const notice = first ? 'roz-config: seeded from the CLAUDE.md block once\n' : ''
    first = false
    const stdout = e.argv[2] === '--json' ? JSON_OUT + '\n' : 'inbox_label      discuss\n'
    return { value: { exitCode: 0, stdout, stderr: notice, isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no-surface' } }))
  on('ui.close', () => ({ value: undefined }))
  const r = await $.command.run(run(''))
  expect(r.text).toBe('roz-config: seeded from the CLAUDE.md block once\ninbox_label      discuss')
})
