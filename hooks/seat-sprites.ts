// The seat pane's sprites (#172): Roz, the owl of images/roz-gate-logo.svg,
// as 8-bit pixel grids in the logo's palette. Data only — no `$`, no hooks;
// hooks/seat-pane.tsx draws them. One letter is one pixel, `.` transparent;
// two pixel rows make one terminal line (`▀`: the top pixel is its colour,
// the bottom one its background).

export const PALETTE: Record<string, string> = {
  D: '#2A2018', B: '#7A5C42', W: '#5C4433', L: '#A98762', Z: '#8A6A4F', G: '#C4453A', E: '#DCE8E2',
  P: '#2A2018', K: '#E5A13C', C: '#F5C86B', R: '#F2EBD3', A: '#8FD3E8', Y: '#F2D21B', U: '#B8913E',
  Q: '#3B7FC4',
}

export type Frames = [string[], string[]]

// 16×16, the pane's standby: eyes open, then a blink.
export const BIG: Frames = [
  [
    '.DD..........DD.', '.DBD........DBD.', '.DBBDDDDDDDDBBD.', 'DBBBBBBBBBBBBBBD',
    'DGBGGGBBBBGGGBGD', 'DBGBBBGGGGBBBGBD', 'DBGDDDGBBGDDDGBD', 'DCGEPEGBBGEPEGCD',
    'DCBGGGBKKBGGGBCD', 'DWCBLLLLLLLLBCWD', 'DWWLZLLZZLLZLWWD', 'DWWLLZZLLZZLLWWD',
    '.DWWLLLLLLLLWWD.', '..DWWLLLLLLWWD..', '...DDDDDDDDDD...', '....KK....KK....',
  ],
  [
    '.DD..........DD.', '.DBD........DBD.', '.DBBDDDDDDDDBBD.', 'DBBBBBBBBBBBBBBD',
    'DGBGGGBBBBGGGBGD', 'DBGBBBGGGGBBBGBD', 'DBGBBBGBBGBBBGBD', 'DCGDDDGBBGDDDGCD',
    'DCBGGGBKKBGGGBCD', 'DWCBLLLLLLLLBCWD', 'DWWLZLLZZLLZLWWD', 'DWWLLZZLLZZLLWWD',
    '.DWWLLLLLLLLWWD.', '..DWWLLLLLLWWD..', '...DDDDDDDDDD...', '....KK....KK....',
  ],
]

// 8×8, the base Roz every seat is drawn from.
export const BASE = ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLLLWD', 'DWZLLZWD', '.DKDDKD.']

// The five seats, two frames each — the rulings' table (#172).
export const SEATS: Record<string, Frames> = {
  // swimming: a wing and its splash, left then right
  product: [
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'WEAQAQAQ', 'QAQQQAQQ', 'QQQQQQQQ'],
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'QAQAQAEW', 'QQAQQQAQ', 'QQQQQQQQ'],
  ],
  // full-black shades on, then off
  em: [
    ['D......D', 'DBBBBBBD', 'DDDDDDDD', 'BDDBBDDB', 'BBBKKBBB', 'DWLLLLWD', 'DWZLLZWD', '.DKDDKD.'],
    BASE,
  ],
  // surfing: the board level, then nose up with spray off the tail
  implementer: [
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLLLWD', '.DKDDKD.', 'RRRGRRRR'],
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLLLWD', '.DKDDKDR', 'ARRGRRR.'],
  ],
  // the lifeguard squats, down one row
  qa: [
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLYLWD', 'DWGGGGWD', '.DKDDKD.'],
    ['........', 'D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWGGYGWD', '.DKDDKD.'],
  ],
  // walking the beach: one foot planted, then the other
  reviewer: [
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLLLWD', '.DKDDD..', 'UCKCUCUC'],
    ['D......D', 'DBBBBBBD', 'BGGBBGGB', 'GEPGGPEG', 'BGGKKGGB', 'DWLLLLWD', '..DDDKD.', 'UCUCUKUC'],
  ],
}

export type Cell = { char: string; color?: string; backgroundColor?: string }

// A grid as the lines a terminal draws: each pair of pixel rows is one line
// of half blocks; a transparent pixel takes no colour.
export function lines(grid: string[]): Cell[][] {
  const out: Cell[][] = []
  for (let y = 0; y < grid.length; y += 2) {
    const top = grid[y]
    const bottom = grid[y + 1] ?? '.'.repeat(top.length)
    const line: Cell[] = []
    for (let x = 0; x < top.length; x++) {
      const t = top[x], b = bottom[x]
      if (t === '.' && b === '.') line.push({ char: ' ' })
      else if (t === '.') line.push({ char: '▄', color: PALETTE[b] })
      else if (b === '.') line.push({ char: '▀', color: PALETTE[t] })
      else line.push({ char: '▀', color: PALETTE[t], backgroundColor: PALETTE[b] })
    }
    out.push(line)
  }
  return out
}
