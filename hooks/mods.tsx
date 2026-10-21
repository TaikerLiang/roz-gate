// The plugin's one hooks module (#172): Claude Code names one module per
// plugin in hooks.json `modules`, so this entry registers each mod in turn —
// the /roz-gate:config menu (#164) and the seat pane (#172).
import type { Register } from 'claude-code'

import { register as config } from './config-menu'
import { register as seats } from './seat-pane'

export const register: Register = (on, options) => {
  config(on, options)
  seats(on, options)
}
