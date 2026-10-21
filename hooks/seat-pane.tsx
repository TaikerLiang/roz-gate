// The seat pane (#172): the seats running now, each an animated 8-bit Roz.
// It only watches — an `agent.spawn` hook notes a seat as it starts, a timer
// reads `$.agent.list()` for its status; it never writes a file, runs a
// process, reaches the network or a model, or refuses a spawn. Where mods do
// not load (Claude Code < 2.1.287) there is simply no pane.
import type { AgentStatus, EngineInterface, Register } from 'claude-code'

import { BIG, SEATS, lines } from './seat-sprites'
import type { Cell } from './seat-sprites'

const PANE = 'roz-gate-seats'
const TICK = 500
// A seat by its default agent type only (ruling 6): a seat linked to your
// own agent (`implementer: backend`) and every other agent are not shown.
const SEAT_OF: Record<string, string> = {
  'roz-gate:product': 'product',
  'roz-gate:em': 'em',
  implementer: 'implementer',
  'roz-gate:qa': 'qa',
  'roz-gate:reviewer': 'reviewer',
}
const LIVE: AgentStatus[] = ['pending', 'running', 'waiting']

type Seat = { seat: string; description: string; since: number; status: AgentStatus }

let seats = new Map<string, Seat>()
let opened = false
let closed = false
// Nowhere to draw (`claude -p`, no surface attached): nothing to animate.
let headless = false
let tick = 0
let now = 0
let timer: { cancel: () => void } | undefined

function reset() {
  timer?.cancel()
  timer = undefined
  seats = new Map()
  opened = closed = headless = false
  tick = now = 0
}

function elapsed(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h ${m % 60}m`
}

function cut(text: string, room: number) {
  return text.length <= room ? text : text.slice(0, Math.max(0, room - 1)) + '…'
}

// One frame: the seats move every tick; standby Roz blinks one tick in eight.
async function step($: EngineInterface) {
  tick++
  if (seats.size > 0) {
    const listed = await $.agent.list()
    for (const [id, s] of seats) {
      const status = listed.find(a => a.id === id)?.status
      if (status && LIVE.includes(status)) s.status = status
      else seats.delete(id)
    }
  }
  now = await $.clock.now()
  $.ui.invalidate('ui.render')
}

// The timer runs while the pane is open; the person's close stops it.
function run($: EngineInterface) {
  if (timer || !opened || closed || headless) return
  timer = $.clock.every(TICK, () => void step($))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    reset()
    return next(e)
  }).catch(($, e, next) => next(e))

  on('agent.spawn', async ($, e, next) => {
    const r = await next(e)
    const seat = SEAT_OF[e.subagentType]
    // A spawn another hook refused carries no agent id: nothing started.
    if (!seat || !('agentId' in r) || !r.agentId) return r
    // The spawn has started: the pane's bookkeeping never fails it
    // (codex review, PR #187).
    try {
      now = await $.clock.now()
      seats.set(r.agentId, { seat, description: e.description, since: now, status: 'running' })
      if (!opened && !closed) {
        opened = true
        const placed = await $.ui.open({ id: PANE, title: 'Roz Gate' })
        // A narrow terminal places it later; no surface never does
        // (codex review, PR #187).
        headless = !placed.isPlaced && placed.reason.startsWith('no-surface')
      }
      run($)
      $.ui.invalidate('ui.render')
    } catch {
      // A pane that cannot draw leaves the spawn as it was.
    }
    return r
  }).catch(($, e, next) => next(e))

  on('ui.close', async ($, e, next) => {
    const r = await next(e)
    if (e.id === PANE && e.origin.kind === 'person') {
      // Closed by hand: not reopened in this session (ruling 7).
      closed = true
      timer?.cancel()
      timer = undefined
    }
    return r
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const rows = [...seats.values()]
    const text = (s: Seat) => [s.seat, s.description, `${s.status} · ${elapsed(now - s.since)}`]
    if (e.surface !== 'terminal') {
      // Sprites are the terminal's (ruling 8): elsewhere a text list.
      return (
        <Box flexDirection="column">
          {rows.length === 0 && <Text dimColor>standby — no seat running</Text>}
          {rows.map(s => <Text>{text(s).join(' · ')}</Text>)}
        </Box>
      )
    }
    const art = (grid: string[]) => (
      <Box flexDirection="column">
        {lines(grid).map(line => (
          <Text>
            {line.map((c: Cell) => <Text color={c.color} backgroundColor={c.backgroundColor}>{c.char}</Text>)}
          </Text>
        ))}
      </Box>
    )
    if (rows.length === 0) {
      return (
        <Box flexDirection="column">
          {art(BIG[tick % 8 === 7 ? 1 : 0])}
          <Text dimColor>standby</Text>
        </Box>
      )
    }
    const room = Math.max(8, (e.props.bodyColumns ?? 40) - 11)
    return (
      <Box flexDirection="column" gap={1}>
        {rows.map(s => {
          const [name, description, status] = text(s)
          return (
            <Box flexDirection="row" gap={2}>
              {art(SEATS[s.seat][tick % 2])}
              <Box flexDirection="column">
                <Text bold>{name}</Text>
                <Text>{cut(description, room)}</Text>
                <Text dimColor>{status}</Text>
              </Box>
            </Box>
          )
        })}
      </Box>
    )
  }).catch(() => undefined)
}
