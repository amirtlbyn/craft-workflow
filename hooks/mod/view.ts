// Pure helpers for the craft mod: formatting, status glyphs, and cost arithmetic.
// Nothing here touches $, so craft.tsx stays the only file that calls the mods API.

import type { AgentCost, CostBook, Snapshot } from '../../types'

export type PriceRow = {
  family: string
  match: string[]
  input: number
  output: number
  cache_write: number
  cache_read: number
}

export const DEFAULT_PRICES: PriceRow[] = [
  { family: 'opus', match: ['opus'], input: 5, output: 25, cache_write: 6.25, cache_read: 0.5 },
  { family: 'sonnet', match: ['sonnet'], input: 3, output: 15, cache_write: 3.75, cache_read: 0.3 },
  { family: 'haiku', match: ['haiku'], input: 1, output: 5, cache_write: 1.25, cache_read: 0.1 },
  { family: 'other', match: [''], input: 3, output: 15, cache_write: 3.75, cache_read: 0.3 },
]

const FALLBACK_PRICE: PriceRow = { family: 'other', match: [''], input: 3, output: 15, cache_write: 3.75, cache_read: 0.3 }

export const ROUTE_EMOJI: Record<string, string> = { quick: '⚡', task: '📦', project: '🗺' }

export const GATE_EMOJI: Record<string, string> = {
  trace: '🔗',
  tests: '🧪',
  lint: '🧹',
  imports: '📥',
  format: '🎨',
  types: '🔎',
  vet: '🧾',
  race: '🏁',
}

const SEVERITY_RANK: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }

export function severityRank(severity: string | undefined): number {
  return SEVERITY_RANK[String(severity).toLowerCase()] ?? 4
}

export function severityColor(severity: string | undefined): string {
  return ['error', 'error', 'warning', 'subtle'][severityRank(severity)] ?? 'subtle'
}

export function family(model: string, prices: PriceRow[]): PriceRow {
  const lowered = (model || '').toLowerCase()
  for (const row of prices) {
    if (row.match.some(part => lowered.includes(part))) return row
  }
  return prices[prices.length - 1] ?? FALLBACK_PRICE
}

export function shortModel(model: string, prices: PriceRow[]): string {
  const name = family(model, prices).family
  return name === 'other' ? (model || '?').split('/').pop()!.slice(0, 10) : name
}

/** USD for one usage record, priced with the table. */
export function priced(
  usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number },
  model: string,
  prices: PriceRow[],
): number {
  const row = family(model, prices)
  return (
    (usage.input_tokens * row.input +
      usage.output_tokens * row.output +
      usage.cache_read_input_tokens * row.cache_read +
      usage.cache_creation_input_tokens * row.cache_write) /
    1_000_000
  )
}

export function agentName(subagentType: string | undefined): string {
  if (!subagentType) return 'subagent'
  const bare = subagentType.includes(':') ? subagentType.split(':').pop()! : subagentType
  return bare || 'subagent'
}

export function addToBook(
  book: CostBook,
  agent: string,
  model: string,
  usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number },
  prices: PriceRow[],
): CostBook {
  const previous: AgentCost = book.agents[agent] ?? {
    model,
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    steps: 0,
    weight: 0,
  }
  const next: AgentCost = {
    model: model || previous.model,
    input: previous.input + (usage.input_tokens || 0),
    output: previous.output + (usage.output_tokens || 0),
    cacheRead: previous.cacheRead + (usage.cache_read_input_tokens || 0),
    cacheWrite: previous.cacheWrite + (usage.cache_creation_input_tokens || 0),
    steps: previous.steps + 1,
    weight: previous.weight + priced(usage, model, prices),
  }
  return { ...book, agents: { ...book.agents, [agent]: next } }
}

export function bookTotal(book: CostBook | null): number {
  if (!book) return 0
  return Object.values(book.agents).reduce((sum, agent) => sum + agent.weight, 0)
}

export function cacheRate(agent: AgentCost): number {
  const all = agent.input + agent.cacheRead + agent.cacheWrite
  return all > 0 ? agent.cacheRead / all : 0
}

export function usd(value: number): string {
  if (!Number.isFinite(value)) return '$—'
  if (value > 0 && value < 0.01) return '<$0.01'
  return '$' + value.toFixed(2)
}

export function tokens(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M'
  if (value >= 1_000) return Math.round(value / 1_000) + 'k'
  return String(value)
}

export function bar(fraction: number, width: number): string {
  const clamped = Math.max(0, Math.min(1, fraction || 0))
  const full = Math.round(clamped * width)
  return '█'.repeat(full) + '░'.repeat(Math.max(0, width - full))
}

export function pct(value: number | undefined): string {
  return value === undefined || value === null ? '—' : Math.round(value) + '%'
}

export function levelColor(percent: number | undefined): string {
  if (percent === undefined) return 'subtle'
  if (percent >= 80) return 'error'
  if (percent >= 50) return 'warning'
  return 'success'
}

export function mark(ok: boolean | null | undefined): string {
  if (ok === true) return '✓'
  if (ok === false) return '✗'
  return '○'
}

export function markColor(ok: boolean | null | undefined): string {
  if (ok === true) return 'success'
  if (ok === false) return 'error'
  return 'subtle'
}

export function summaryText(detail: unknown): string {
  if (!detail || typeof detail !== 'object') return String(detail ?? '')
  const summary = detail as Record<string, unknown>
  const parts: string[] = []
  for (const key of ['passed', 'failed', 'errors', 'skipped', 'issues', 'races']) {
    const value = summary[key]
    if (typeof value === 'number' && (value > 0 || key === 'passed' || key === 'failed')) parts.push(`${value} ${key}`)
  }
  return parts.join(' · ')
}

/** A decider's vote as `field value · field value`, not raw JSON. */
export function voteText(answer: unknown): string {
  if (!answer || typeof answer !== 'object') return String(answer ?? '')
  return Object.entries(answer as Record<string, unknown>)
    .map(([field, value]) => `${field} ${Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    .join(' · ')
}

export function specState(state: string | undefined): { glyph: string; text: string; color: string } {
  switch (state) {
    case 'approved':
      return { glyph: '✓', text: 'approved', color: 'success' }
    case 'not approved':
      return { glyph: '◐', text: 'waiting for you', color: 'warning' }
    case 'stale':
      return { glyph: '◐', text: 'changed since approval', color: 'warning' }
    default:
      return { glyph: '○', text: 'no spec', color: 'subtle' }
  }
}

export function gateBText(state: string | undefined): { glyph: string; color: string } {
  switch (state) {
    case 'green':
      return { glyph: '✓', color: 'success' }
    case 'changes requested':
      return { glyph: '✗', color: 'error' }
    case 'in review':
      return { glyph: '◐', color: 'warning' }
    default:
      return { glyph: '○', color: 'subtle' }
  }
}

export function isGated(snapshot: Snapshot | null): boolean {
  const route = snapshot?.session?.route
  return Boolean(snapshot?.session?.active && (route === 'task' || route === 'project') && snapshot?.spec?.name)
}

export function inCraftArea(path: string, repo: string): boolean {
  if (!path) return true
  const absolute = path.startsWith('/') ? path : `${repo}/${path}`
  if (!absolute.startsWith(repo + '/')) return true
  return absolute.slice(repo.length + 1).startsWith('.claude/')
}

export function oneLineStatus(snapshot: Snapshot | null, total: number): string {
  if (!snapshot || snapshot.error) return '🛠️ craft · state unavailable'
  const stack = snapshot.stack
  const session = snapshot.session
  const spec = snapshot.spec
  const route = session?.route || ''
  const parts = ['🛠️ craft']
  if (route) parts.push(`${ROUTE_EMOJI[route] ?? ''} ${route}${spec?.key ? ' ' + spec.key : ''}`.trim())
  if (stack) parts.push(`${stack.emoji} ${stack.primary}`)
  if (spec?.name) {
    const gateA = snapshot.gate_a
    parts.push(`📋 ${specState(spec.state).glyph}`)
    if (gateA) parts.push(`🅰️ ${gateA.passed}/${gateA.total}`)
    parts.push(`🅱️ ${gateBText(snapshot.gate_b?.state).glyph}`)
  }
  if (total > 0) parts.push(`💰 ${usd(total)}`)
  return parts.join(' · ')
}

// ---------------------------------------------------------------------------
// The document viewer: markdown made readable in a terminal pane
// ---------------------------------------------------------------------------

const COMMENT = /<!--[\s\S]*?-->/g
const TABLE_ROW = /^\s*\|.*\|\s*$/
const TABLE_RULE = /^\s*\|(\s*:?-{3,}:?\s*\|)+\s*$/
/** A cell this long or shorter stays on the row's heading line. */
const SHORT_CELL = 24

function tableCells(line: string): string[] {
  const inner = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return inner.split(/(?<!\\)\|/).map(cell => cell.trim())
}

/** The terminal columns a table needs: the widest cell of each column, plus borders. */
function tableWidth(rows: string[][]): number {
  const widths: number[] = []
  for (const row of rows) row.forEach((cell, index) => (widths[index] = Math.max(widths[index] ?? 0, cell.length)))
  return widths.reduce((sum, width) => sum + width + 3, 1)
}

/** One block per row: the first cell bold with the short cells after it, each long cell its own paragraph. */
function tableBlocks(header: string[], rows: string[][]): string[] {
  const out: string[] = []
  for (const row of rows) {
    const [first = '', ...rest] = row
    const short: string[] = []
    const long: string[] = []
    rest.forEach((cell, index) => {
      if (!cell) return
      if (cell.length <= SHORT_CELL) short.push(cell)
      else long.push(`*${header[index + 1] || 'More'}:* ${cell}`)
    })
    out.push([first ? `**${first}**` : '', ...short].filter(Boolean).join(' · '), '')
    for (const paragraph of long) out.push(paragraph, '')
    out.push('---', '')
  }
  if (out.length) out.splice(-2, 2)
  return out
}

/**
 * A spec document as the viewer draws it: every <!-- --> comment removed, and
 * each table wider than `columns` redrawn as one block per row (CSL-9, CSL-12).
 */
export function docText(markdown: string, columns: number): string {
  const lines = markdown.replace(COMMENT, '').split('\n')
  const out: string[] = []
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index] ?? ''
    if (!TABLE_ROW.test(line) || !TABLE_RULE.test(lines[index + 1] ?? '')) {
      out.push(line)
      continue
    }
    let end = index + 2
    while (end < lines.length && TABLE_ROW.test(lines[end] ?? '')) end++
    const table = lines.slice(index, end)
    const header = tableCells(table[0] ?? '')
    const rows = table.slice(2).map(tableCells)
    if (tableWidth([header, ...rows]) <= columns) out.push(...table)
    else out.push(...tableBlocks(header, rows))
    index = end - 1
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}
