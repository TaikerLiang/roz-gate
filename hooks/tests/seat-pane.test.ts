// hooks/seat-pane.tsx — the seat pane (#172), run by `claude plugin test`.
// Hooks beneath stand for the engine: they start the agents, list them,
// place the pane; `mock.clock` moves the 500 ms timer only when a test does.
import { expect, mock, test } from 'claude-code/testing'
import type { AgentInfo, AgentSpawnInput, AgentStatus } from 'claude-code'
import type { TestBody } from 'claude-code/testing'

import { register } from '../seat-pane'
import { BASE, BIG, PALETTE, SEATS } from '../seat-sprites'

type On = Parameters<TestBody>[1]
type Engine = Parameters<TestBody>[0]

const PANE = 'roz-gate-seats'

// One Agent call: its tool_use_id carries the agent id the engine answers.
const spawn = (subagentType: string, id = 'a1', description = 'QA validation #172'): AgentSpawnInput => ({
  tool_use_id: 'tu-' + id, prompt: 'run the stage', description, subagentType,
  provider: { plugin: 'engine', tier: 'core' }, parentModel: 'claude-opus-5-5', background: true, fork: false,
})

// The engine beneath: spawns, lists `agents`, places the pane, counts both.
function engine(on: On, agents: AgentInfo[]) {
  const seen = { opens: 0, lists: 0 }
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('agent.spawn', (_, e) => ({ model: 'claude-opus-5-5', agentId: e.tool_use_id.slice(3) }))
  on('agent.list', () => {
    seen.lists++
    return { value: agents }
  })
  on('ui.open', () => {
    seen.opens++
    return { value: { isPlaced: true } }
  })
  on('ui.close', () => ({ value: undefined }))
  return seen
}

const agent = (id: string, type: string, status: AgentStatus = 'running'): AgentInfo =>
  ({ id, type, status, description: 'QA validation #172' })

// A person's close cannot be raised through the kit (its `$` has no
// `ui.close`), so the close tests drive seat-pane's own hooks with a fake `$`:
// the timer it starts, the opens and the list polls are counted.
function direct() {
  const hooks: Record<string, (...a: unknown[]) => Promise<unknown>> = {}
  const on = (event: string, a: unknown, b?: unknown) => {
    hooks[event] = (typeof a === 'function' ? a : b) as (...a: unknown[]) => Promise<unknown>
    return { catch: () => undefined }
  }
  register(on as never, {} as never)
  const calls = { opens: 0, lists: 0, timers: 0, cancels: 0 }
  const $ = {
    clock: {
      now: async () => 0,
      every: () => {
        calls.timers++
        return { cancel: () => void calls.cancels++ }
      },
    },
    agent: {
      list: async () => {
        calls.lists++
        return [agent('a1', 'roz-gate:qa')]
      },
    },
    ui: {
      open: async () => {
        calls.opens++
        return { isPlaced: true }
      },
      invalidate: () => undefined,
    },
  }
  const fire = (event: string, e: unknown, answer: unknown) => hooks[event]($, e, async () => answer)
  return { fire, calls }
}

async function start($: Engine) {
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
}

function mount($: Engine, surface: 'terminal' | 'desktop' | 'vscode' | 'mobile') {
  return $.ui.mount({
    plugin: 'roz-gate', component: 'Pane', requestId: PANE, surface,
    props: {
      title: 'Roz Gate', isFocused: false, bodyColumns: 40, placement: 'dock',
      scroll: { offset: 0, bodyRows: 30 }, view: {},
    },
  })
}

test('a seat by its default agent type only', async ($, on) => {
  mock.clock(on)
  const agents: AgentInfo[] = []
  engine(on, agents)
  await start($)
  const types: [string, string | undefined][] = [
    ['roz-gate:product', 'product'], ['roz-gate:em', 'em'], ['implementer', 'implementer'],
    ['roz-gate:qa', 'qa'], ['roz-gate:reviewer', 'reviewer'],
    ['general-purpose', undefined], ['backend', undefined],
  ]
  for (const [i, [type]] of types.entries()) {
    agents.push(agent('a' + i, type))
    await $.agent.spawn(spawn(type, 'a' + i))
  }
  const ui = await mount($, 'desktop')
  for (const [, seat] of types.filter(([, s]) => s)) {
    expect(await ui.find({ type: 'Text', text: new RegExp('^' + seat + ' · ') })).toBeDefined()
  }
  expect(await ui.find({ type: 'Text', text: /^(general-purpose|backend) · / })).toBeUndefined()
  await ui.unmount()
})

test('the first seat opens the pane, once', async ($, on) => {
  mock.clock(on)
  const agents = [agent('a1', 'roz-gate:qa'), agent('a2', 'roz-gate:reviewer')]
  const seen = engine(on, agents)
  await start($)
  await $.agent.spawn(spawn('general-purpose', 'g1'))
  expect(seen.opens).toBe(0)
  await $.agent.spawn(spawn('roz-gate:qa', 'a1'))
  await $.agent.spawn(spawn('roz-gate:reviewer', 'a2'))
  expect(seen.opens).toBe(1)
})

test('closed by hand: never reopened, and the timer stops (A2)', async () => {
  const { fire, calls } = direct()
  await fire('session.start', { cwd: '/' }, { cwd: '/' })
  await fire('agent.spawn', spawn('roz-gate:qa', 'a1'), { model: 'm', agentId: 'a1' })
  expect([calls.opens, calls.timers]).toEqual([1, 1])
  // Another pane's close, and a plugin's close of this one, change nothing.
  await fire('ui.close', { id: 'roz-gate-config', origin: { kind: 'person' } }, undefined)
  await fire('ui.close', { id: PANE, origin: { kind: 'plugin' } }, undefined)
  expect(calls.cancels).toBe(0)
  await fire('ui.close', { id: PANE, origin: { kind: 'person' } }, undefined)
  expect(calls.cancels).toBe(1)
  await fire('agent.spawn', spawn('roz-gate:em', 'a2'), { model: 'm', agentId: 'a2' })
  expect([calls.opens, calls.timers]).toEqual([1, 1])
})

test('standby shows the 16×16 Roz; a running seat shows its 8×8 frame and three lines', async ($, on) => {
  mock.clock(on)
  const agents = [agent('a1', 'roz-gate:qa')]
  engine(on, agents)
  await start($)
  let ui = await mount($, 'terminal')
  expect(await ui.find({ type: 'Text', text: 'standby' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^[▀▄ ]{16}$/ })).toBeDefined()
  await ui.unmount()
  await $.agent.spawn(spawn('roz-gate:qa', 'a1'))
  ui = await mount($, 'terminal')
  expect(await ui.find({ type: 'Text', text: /^[▀▄ ]{8}$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^[▀▄ ]{16}$/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: 'qa' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'QA validation #172' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'running · 0s' })).toBeDefined()
  await ui.unmount()
})

test('the elapsed time counts from the spawn', async ($, on) => {
  const clock = mock.clock(on, { now: 1_000_000 })
  engine(on, [agent('a1', 'implementer')])
  await start($)
  await $.agent.spawn(spawn('implementer', 'a1', 'Implement #172'))
  await clock.advance(4 * 60_000)
  const ui = await mount($, 'terminal')
  expect(await ui.find({ type: 'Text', text: 'running · 4m' })).toBeDefined()
  await ui.unmount()
})

test('desktop, VS Code and mobile get a text list, no sprite', async ($, on) => {
  mock.clock(on)
  engine(on, [agent('a1', 'roz-gate:product')])
  await start($)
  for (const surface of ['desktop', 'vscode', 'mobile'] as const) {
    let ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: /standby/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /[▀▄]/ })).toBeUndefined()
    await ui.unmount()
  }
  await $.agent.spawn(spawn('roz-gate:product', 'a1', 'Intake #175'))
  for (const surface of ['desktop', 'vscode', 'mobile'] as const) {
    const ui = await mount($, surface)
    expect(await ui.find({ type: 'Text', text: 'product · Intake #175 · running · 0s' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /[▀▄]/ })).toBeUndefined()
    await ui.unmount()
  }
})

test("with no seat running the list is not polled; the person's close stops the timer (A3)", async ($, on) => {
  const clock = mock.clock(on)
  const agents = [agent('a1', 'roz-gate:reviewer')]
  const seen = engine(on, agents)
  await start($)
  await $.agent.spawn(spawn('roz-gate:reviewer', 'a1'))
  await clock.advance(500)
  expect(seen.lists).toBe(1)
  agents[0] = agent('a1', 'roz-gate:reviewer', 'completed')
  await clock.advance(500)
  expect(seen.lists).toBe(2)
  await clock.advance(5000)
  expect(seen.lists).toBe(2)
  // Standby still blinks: the timer runs while the pane is open.
  const ui = await mount($, 'terminal')
  expect(await ui.find({ type: 'Text', text: 'standby' })).toBeDefined()
  await ui.unmount()
  // The person's close stops it (driven directly, as in the A2 test).
  const { fire, calls } = direct()
  await fire('session.start', { cwd: '/' }, { cwd: '/' })
  await fire('agent.spawn', spawn('roz-gate:reviewer', 'a1'), { model: 'm', agentId: 'a1' })
  await fire('ui.close', { id: PANE, origin: { kind: 'person' } }, undefined)
  expect([calls.timers, calls.cancels]).toEqual([1, 1])
})

// Codex review, PR #187: no surface never places the pane — no timer; a
// narrow terminal places it later — the timer runs.
for (const [where, reason, lists] of [
  ['where nothing draws, no timer runs', 'no-surface: a -p run', 0],
  ['a terminal too narrow for now keeps the timer', '144 columns unasked, 100 now', 2],
] as const) {
  test(where, async ($, on) => {
    const clock = mock.clock(on)
    const seen = { lists: 0 }
    on('session.start', (_, e) => ({ cwd: e.cwd }))
    on('agent.spawn', (_, e) => ({ model: 'claude-opus-5-5', agentId: e.tool_use_id.slice(3) }))
    on('agent.list', () => {
      seen.lists++
      return { value: [agent('a1', 'roz-gate:qa')] }
    })
    on('ui.open', () => ({ value: { isPlaced: false, reason } }))
    await start($)
    await $.agent.spawn(spawn('roz-gate:qa', 'a1'))
    await clock.advance(1000)
    expect(seen.lists).toBe(lists)
  })
}

test('every grid is rectangular and drawn in the palette', async () => {
  const grids: [string, string[], number][] = [
    ['big', BIG[0], 16], ['big blink', BIG[1], 16], ['base', BASE, 8],
    ...Object.entries(SEATS).flatMap(([seat, [a, b]]) =>
      [[seat + ' 1', a, 8], [seat + ' 2', b, 8]] as [string, string[], number][]),
  ]
  expect(Object.keys(SEATS)).toEqual(['product', 'em', 'implementer', 'qa', 'reviewer'])
  for (const [, grid, size] of grids) {
    expect(grid.length).toBe(size)
    for (const row of grid) {
      expect(row.length).toBe(size)
      for (const ch of row) expect(ch === '.' || ch in PALETTE).toBe(true)
    }
  }
})
