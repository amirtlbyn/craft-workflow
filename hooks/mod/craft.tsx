// craft-workflow's mod: the status at the top, the 🗂 board, cost per agent,
// zero-token commands, and the spec gate as a question instead of a refusal.
//
// Everything it shows comes from bin/craft-ui-state, which reads the same
// .claude/specs and .claude/craft files the Python hooks enforce. The mod never
// decides a gate: it draws them, and it asks the developer. The Python hooks in
// hooks/hooks.json stay the enforcement, so a session without mods (VS Code's
// panel, claude -p, ZCode, Codex) keeps every rule.

import { atom, read, update } from 'claude-code'
import type { ElementTable, EngineInterface, Register } from 'claude-code'

import type { CostBook, DocName, GateItem, Snapshot, Tab } from '../../types'
import {
  DEFAULT_PRICES,
  GATE_EMOJI,
  addToBook,
  agentName,
  bar,
  bookTotal,
  cacheRate,
  docText,
  gateBText,
  inCraftArea,
  isGated,
  levelColor,
  mark,
  markColor,
  oneLineStatus,
  pct,
  severityColor,
  severityRank,
  shortModel,
  specState,
  summaryText,
  tokens,
  usd,
  voteText,
} from './view'
import type { PriceRow } from './view'

const PANE = 'craft-board'
const TABS: { id: Tab; label: string; hotkey: string }[] = [
  { id: 'spec', label: 'Spec', hotkey: '1' },
  { id: 'tasks', label: 'Tasks', hotkey: '2' },
  { id: 'gates', label: 'Gates', hotkey: '3' },
  { id: 'review', label: 'Review', hotkey: '4' },
  { id: 'cost', label: 'Cost', hotkey: '5' },
  { id: 'deciders', label: 'Deciders', hotkey: '6' },
]
// The document viewer: the active spec's files, one hotkey each.
const VIEWER = 'craft-doc'
const DOCS: { id: DocName; file: string; hotkey: string }[] = [
  { id: 'spec', file: 'spec.md', hotkey: 's' },
  { id: 'design', file: 'design.md', hotkey: 'd' },
  { id: 'tasks', file: 'tasks.md', hotkey: 't' },
  { id: 'log', file: 'log.md', hotkey: 'l' },
]
const REFRESH_EVERY_MS = 20_000
const NOTICE_MS = 8_000
const WRITE_TOOLS = /^(Write|Edit|MultiEdit|NotebookEdit)$/
const TEST_COMMAND = /^(\s*)(pytest|python -m pytest|go test|gotestsum|\.\/mvnw|mvn|\.\/gradlew|gradle|npm test|pnpm test|yarn test|bun test|npx vitest|npx jest|cargo test)\b/
const WAITING = new Set(['proposed', 'plausible'])

const snapshot = atom({ plugin: 'craft-workflow', key: 'snapshot' } as const, null)
const tab = atom({ plugin: 'craft-workflow', key: 'tab' } as const, 'spec')
const costs = atom({ plugin: 'craft-workflow', key: 'costs' } as const, null)
const notice = atom({ plugin: 'craft-workflow', key: 'notice' } as const, '')
const doc = atom({ plugin: 'craft-workflow', key: 'doc' } as const, 'spec')
const placed = atom({ plugin: 'craft-workflow', key: 'placed' } as const, false)
const confirmApprove = atom({ plugin: 'craft-workflow', key: 'confirmApprove' } as const, false)
const stale = atom({ plugin: 'craft-workflow', key: 'stale' } as const, '')

// Module state: lost on a reload, rebuilt on the next event.
let prices: PriceRow[] = DEFAULT_PRICES
const agentTypes = new Map<string, string>()
let pendingRefresh: { cancel: () => void } | null = null
let noticeTimer: { cancel: () => void } | null = null
let lastGateA = false
let lastGateB = false
let refusedEdit = ''
let placement = 'top'
let autoCheck = false
let gateQuestion = true

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

async function runCraft($: EngineInterface, command: string, args: string[]) {
  const cwd = await $.session.cwd()
  try {
    const result = await $.process.run(['python3', $.plugin.root + '/bin/' + command, ...args], {
      cwd,
      timeoutMs: 60_000,
    })
    return { code: result.exitCode, out: (result.stdout || '') + (result.stderr || '') }
  } catch (error) {
    return { code: 127, out: String(error) }
  }
}

async function refresh($: EngineInterface) {
  const cwd = await $.session.cwd()
  let next: Snapshot
  try {
    const result = await $.process.run(['python3', $.plugin.root + '/bin/craft-ui-state', '--cwd', cwd], {
      cwd,
      timeoutMs: 10_000,
    })
    next = JSON.parse(result.stdout || '{}') as Snapshot
  } catch (error) {
    next = { version: 1, error: 'craft-ui-state failed: ' + String(error).slice(0, 120) }
  }
  // One failed read keeps the last good state on screen, marked stale.
  const previous = await read($, snapshot)
  if (next.error && previous && !previous.error) {
    await update($, stale, () => next.error ?? 'craft-ui-state failed')
    return previous
  }
  await update($, stale, () => '')
  if (next.spec?.state === 'approved') refusedEdit = ''
  await update($, snapshot, () => next)
  await rollBook($, next)
  announce($, next)
  return next
}

function scheduleRefresh($: EngineInterface) {
  if (pendingRefresh) pendingRefresh.cancel()
  pendingRefresh = $.clock.after(400, () => refresh($))
}

async function setNotice($: EngineInterface, text: string) {
  await update($, notice, () => text)
  if (noticeTimer) noticeTimer.cancel()
  noticeTimer = $.clock.after(NOTICE_MS, () => update($, notice, () => ''))
}

function announce($: EngineInterface, next: Snapshot) {
  const gateA = Boolean(next.gate_a?.green)
  const gateB = next.gate_b?.state === 'green'
  if (gateA && gateB && !(lastGateA && lastGateB)) $.ui.toast('🎉 Both gates green: /finish')
  else if (gateA && !lastGateA) $.ui.toast('Gate A is green ✓')
  else if (gateB && !lastGateB) $.ui.toast('Gate B is green ✓')
  lastGateA = gateA
  lastGateB = gateB
}

function bookKey(next: Snapshot | null): string {
  return 'costs:' + (next?.repo ?? '?') + ':' + (next?.spec?.name || 'no-spec')
}

async function rollBook($: EngineInterface, next: Snapshot) {
  const key = bookKey(next)
  const current = await read($, costs)
  if (current && current.key === key) return
  if (current && bookTotal(current) > 0) {
    await $.store.set(current.key, current)
    const historyKey = 'history:' + (next.repo ?? '?')
    const history = ((await $.store.get(historyKey)) as { spec: string; usd: number; route: string; at: number }[]) ?? []
    const spec = current.key.split(':').pop() ?? ''
    const kept = history.filter(item => item.spec !== spec)
    kept.push({ spec, usd: bookTotal(current), route: next.session?.route ?? '', at: await $.clock.now() })
    await $.store.set(historyKey, kept.slice(-30))
  }
  const saved = (await $.store.get(key)) as CostBook | undefined
  const usage = await $.session.usage()
  const book: CostBook = saved ?? { key, startedAt: await $.clock.now(), agents: {}, ledgerAtStart: usage.cost?.usd ?? 0 }
  await update($, costs, () => book)
}

async function addUsage($: EngineInterface, agentId: string | undefined, usage: {
  model: string
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  cache_creation_input_tokens: number
}) {
  let name = 'main'
  if (agentId) {
    name = agentTypes.get(agentId) ?? ''
    if (!name) {
      const agents = await $.agent.list()
      const found = agents.find(agent => agent.id === agentId)
      name = agentName(found?.type)
      agentTypes.set(agentId, name)
    }
  }
  const book = await read($, costs)
  if (!book) return
  const next = addToBook(book, name, usage.model, usage, prices)
  await update($, costs, () => next)
  await $.store.set(next.key, next)
}

async function openBoard($: EngineInterface, which: Tab | null) {
  if (which) await update($, tab, () => which)
  const result = await $.ui.open({ id: PANE, title: '🗂 Craft', focus: true, closeOnEscape: true })
  await update($, placed, () => Boolean(result.isPlaced))
  await refresh($)
}

async function openViewer($: EngineInterface, which: DocName) {
  await update($, doc, () => which)
  const file = DOCS.find(item => item.id === which)?.file ?? which
  await $.ui.open({ id: VIEWER, title: '📄 ' + file, focus: true, closeOnEscape: true, columns: 120, rows: 40 })
}

async function approveSpec($: EngineInterface, how: string) {
  const result = await runCraft($, 'craft-approve', ['--note', 'Approved by the developer in ' + how])
  await setNotice($, result.code === 0 ? '✓ Spec approved. The gate is open.' : '✗ ' + result.out.slice(0, 160))
  await refresh($)
  return result.code === 0
}

// Approving from the band or the board first shows what is being approved.
async function askApproval($: EngineInterface) {
  await update($, confirmApprove, () => true)
  await openBoard($, 'spec')
}

/** `where` names the view the developer confirmed in, for the approval note and the resume prompt. */
async function confirmApproval($: EngineInterface, where: string) {
  await update($, confirmApprove, () => false)
  const path = refusedEdit // the refresh after an approval clears it
  if (!(await approveSpec($, where)) || !path) return
  // The gate refused this edit and Claude stopped: hand the turn back.
  $.prompt.submit({ text: `The developer approved the spec in ${where}. Retry the edit to ${path} and continue.` })
    .catch(error => $.ui.log('craft: could not resume Claude: ' + String(error).slice(0, 120)))
}

async function setFinding($: EngineInterface, id: string, state: string) {
  const result = await runCraft($, 'craft-session', ['finding', id, '--state', state, '--note', 'set on the craft board'])
  await setNotice($, result.code === 0 ? `${id} → ${state}` : '✗ ' + result.out.slice(0, 160))
  await refresh($)
}

async function retrace($: EngineInterface) {
  const result = await runCraft($, 'craft-spec', ['trace'])
  const last = result.out.trim().split('\n').filter(line => line.startsWith('result:')).pop() ?? result.out.trim().split('\n').pop()
  await setNotice($, 'trace ' + (last ?? 'ran'))
  await refresh($)
  return result
}

async function toggleMode($: EngineInterface) {
  const current = await read($, snapshot)
  const mode = current?.deciders?.mode === 'council' ? 'first' : 'council'
  const result = await runCraft($, 'craft-decide', ['mode', mode])
  await setNotice($, result.code === 0 ? `decider mode: ${mode}` : '✗ ' + result.out.slice(0, 160))
  await refresh($)
}

async function pingDeciders($: EngineInterface) {
  await setNotice($, 'asking every decider in the chain…')
  const result = await runCraft($, 'craft-decide', ['test'])
  await setNotice($, result.out.trim().split('\n').slice(0, 6).join('\n') || 'no answer')
}

async function loadPrices($: EngineInterface) {
  try {
    const text = await $.fs.read($.plugin.root + '/config/prices.json')
    const data = JSON.parse(String(text)) as { families?: PriceRow[] }
    if (Array.isArray(data.families) && data.families.length) prices = data.families
  } catch {
    prices = DEFAULT_PRICES
  }
}

function statusText(current: Snapshot | null, total: number): string {
  if (!current || current.error) return current?.error ?? 'craft state unavailable'
  const lines = [oneLineStatus(current, total)]
  const spec = current.spec
  if (spec?.name) {
    lines.push(`📋 ${spec.title || spec.name} · ${specState(spec.state).text} · risk ${spec.risk || '?'}`)
    const items = current.gate_a?.items ?? []
    lines.push('🅰️ ' + items.map(item => `${GATE_EMOJI[item.name] ?? '•'} ${item.name} ${mark(item.ok)}`).join('  '))
    lines.push(`🅱️ review ${current.gate_b?.state ?? 'not run'}${current.gate_b?.blocking ? ` · ${current.gate_b.blocking} blocking` : ''}`)
    if (spec.next_task) lines.push('➡️  next: ' + spec.next_task)
  } else {
    lines.push('No active spec. /craft <request> starts one.')
  }
  const concurrency = current.stack?.concurrency
  if (concurrency?.verdict) lines.push(`🧵 concurrency: ${concurrency.model} · ${concurrency.verdict}`)
  return lines.join('\n')
}

function gatesText(current: Snapshot | null): string {
  if (!current?.gate_a) return 'No gate state yet.'
  const lines = [`🅰️ Gate A — spec verified: ${current.gate_a.passed}/${current.gate_a.total}${current.gate_a.green ? ' ✓' : ''}`]
  for (const item of current.gate_a.items) {
    lines.push(`  ${GATE_EMOJI[item.name] ?? '•'} ${item.name.padEnd(8)} ${mark(item.ok)} ${summaryText(item.detail)}`)
  }
  lines.push(`🅱️ Gate B — review green: ${current.gate_b?.state ?? 'not run'}`)
  return lines.join('\n')
}

/** The confirm before craft-approve runs, on the board and in the viewer (CMOD-3, CSL-11). */
function approvalBox(
  $: EngineInterface,
  { Box, Text, Button }: Pick<ElementTable, 'Box' | 'Text' | 'Button'>,
  spec: NonNullable<Snapshot['spec']>,
  where: string,
) {
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="warning" paddingX={1}>
      <Text bold>{`Approve "${spec.title || spec.name}"?`}</Text>
      <Text dimColor>{`sha ${spec.sha} · ${spec.criteria.length} criteria · risk ${spec.risk || '?'}`}</Text>
      <Text dimColor>The spec gate opens, and Claude may write source and tests.</Text>
      <Box flexDirection="row" columnGap={2}>
        <Button key="spec-confirm" label="confirm" hotkey="y" variant="primary" onPress={() => confirmApproval($, where)} />
        <Button key="spec-cancel" label="cancel" hotkey="n" plain dimColor onPress={() => update($, confirmApprove, () => false)} />
      </Box>
    </Box>
  )
}

/** `trace ✓ tests ✗ lint ○`: each Gate A check by name, its glyph in colour. */
function gateStrip(Text: ElementTable['Text'], items: readonly GateItem[]) {
  return items.map(item => (
    <Text key={'strip-' + item.name}>
      {' ' + item.name + ' '}
      <Text color={markColor(item.ok)}>{mark(item.ok)}</Text>
    </Text>
  ))
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export const register: Register = (on, options) => {
  placement = String((options as Record<string, unknown>)?.status ?? 'top')
  autoCheck = Boolean((options as Record<string, unknown>)?.auto_check ?? false)
  gateQuestion = (options as Record<string, unknown>)?.gate_question !== false

  on('session.start', async ($, e, next) => {
    await loadPrices($)
    const first = await refresh($)
    $.clock.every(REFRESH_EVERY_MS, () => refresh($))
    if ((placement === 'top' || placement === 'both') && first.spec?.name) {
      const result = await $.ui.open({ id: PANE, title: '🗂 Craft', closeOnEscape: true })
      await update($, placed, () => Boolean(result.isPlaced))
    }
    try {
      await $.command.register({ name: 'craft-board', description: '🗂 Open the craft board: spec, tasks, gates, review, cost, deciders', immediate: true })
      await $.command.register({ name: 'craft-status', description: '🛠️ Where the active spec stands, in a few lines. No Claude turn', immediate: true })
      await $.command.register({ name: 'craft-cost', description: '💰 What each agent cost on this spec', immediate: true })
      await $.command.register({ name: 'craft-gates', description: '🚦 Gate A and Gate B, check by check. No Claude turn', immediate: true })
      await $.command.register({ name: 'craft-trace', description: '🔗 Map each criterion to its test now. No Claude turn', immediate: true })
    } catch (error) {
      $.ui.log('craft: a command name is taken: ' + String(error).slice(0, 120))
    }
    return next(e)
  })

  on('classic.SessionStart', { source: ['clear', 'resume', 'fork'] }, async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  // Commands that answer at once, with no Claude turn and no tokens.
  on('command.run', { command: 'craft-board' }, async $ => {
    await openBoard($, null)
    return {}
  })

  on('command.run', { command: 'craft-cost' }, async $ => {
    await openBoard($, 'cost')
    return {}
  })

  on('command.run', { command: 'craft-status' }, async $ => {
    const current = await refresh($)
    return { text: statusText(current, bookTotal(await read($, costs))) }
  })

  on('command.run', { command: 'craft-gates' }, async $ => {
    const current = await refresh($)
    return { text: gatesText(current) }
  })

  on('command.run', { command: 'craft-trace' }, async $ => {
    const result = await retrace($)
    return { text: result.out.trim().split('\n').slice(-14).join('\n') }
  })

  // Who each subagent is, so its tokens land under its own name.
  on('agent.spawn', async ($, e, next) => {
    const result = await next(e)
    if (result.agentId) agentTypes.set(result.agentId, agentName(e.subagentType))
    return result
  })

  // 💰 Every model request, main loop and subagents alike.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    if (result.usage) await addUsage($, e.agentId, result.usage)
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (!e.agentId) scheduleRefresh($)
    return result
  })

  // The spec gate as a question. The Python gate still runs after this hook
  // and still refuses when the spec is not approved: this only lets the
  // developer approve in place, by pressing a key Claude cannot press.
  on('tool.call', { tool: WRITE_TOOLS }, async ($, e, next) => {
    if (!gateQuestion) return next(e)
    const current = await read($, snapshot)
    const path = String((e as { file_path?: string; notebook_path?: string }).file_path ??
      (e as { notebook_path?: string }).notebook_path ?? '')
    const repo = current?.repo ?? ''
    if (!isGated(current) || !repo || inCraftArea(path, repo)) {
      const ran = await next(e)
      scheduleRefresh($)
      return ran
    }
    const fresh = await refresh($)
    if (!isGated(fresh) || fresh.spec?.state === 'approved') {
      const ran = await next(e)
      scheduleRefresh($)
      return ran
    }
    const spec = fresh.spec!
    const relative = path.startsWith(repo + '/') ? path.slice(repo.length + 1) : path
    const open = '👀 Open the spec'
    const approve = '✅ Approve the spec'
    const keep = '🚫 Keep it blocked'
    let answer = keep
    try {
      answer = await $.ui.ask(
        `📋 "${spec.title || spec.name}" (sha ${spec.sha}, ${spec.criteria.length} criteria) is ${specState(spec.state).text}. ` +
          `Claude wants to edit ${relative}, and no source or test file is written before you approve the spec. What now?`,
        { header: 'Spec gate', options: [open, approve, keep] },
      )
    } catch {
      return next(e) // nobody to ask: the Python gate decides
    }
    if (answer === approve && (await approveSpec($, 'the gate question'))) {
      refusedEdit = ''
      return next(e)
    }
    if (answer === open) {
      refusedEdit = relative
      await openViewer($, 'spec')
      return { deny: 'The developer is reading the spec in the craft viewer. Wait for their approval, then retry this edit.' }
    }
    return { deny: 'The developer kept the spec gate shut. Do not write source or tests. Ask what to change in the spec.' }
  }).catch(($, e, next) => next(e))

  // Checks through craft-check, so Gate A records them without Claude
  // remembering to. Off unless the developer turns on auto_check.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const command = String(e.command ?? '')
    const current = await read($, snapshot)
    let rewritten = e
    if (autoCheck && current?.session?.active && TEST_COMMAND.test(command) && !command.includes('craft-check')) {
      rewritten = { ...e, command: `"${$.plugin.root}/bin/craft-check" --junit auto -- ${command}` }
    }
    const ran = await next(rewritten)
    if (command.includes('craft-') || TEST_COMMAND.test(command)) scheduleRefresh($)
    return ran
  }).catch(($, e, next) => next(e))

  // The spinner says what the work is on.
  on('ui.render', { component: 'Spinner' }, async ($, e, next) => {
    const current = await read($, snapshot)
    const spec = current?.spec
    if (!spec?.name) return next(e)
    const total = spec.tasks.length
    const done = spec.tasks.filter(task => task.done).length
    const suffix = ` · ${spec.key || 'craft'}${total ? ` · task ${Math.min(done + 1, total)}/${total}` : ''}`
    return next({ ...e, props: { ...e.props, suffix: (e.props.suffix ?? '') + suffix } })
  })

  // A short status at the end of the hint line under the prompt.
  on('ui.render', { component: 'PromptHint' }, async ($, e, next) => {
    const current = await read($, snapshot)
    const route = current?.session?.route
    if (!current?.session?.active || !route) return next(e)
    const gateA = current.gate_a
    const tail = ` · craft ${route}${gateA ? ` · A ${gateA.passed}/${gateA.total}` : ''} · /craft-board`
    return next({ ...e, props: { ...e.props, tail: (e.props.tail ?? '') + tail } })
  })

  // The band above the prompt, one row: the status where there is no room for
  // the board beside the transcript, or everywhere when status is "prompt" or "both".
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const current = await read($, snapshot)
    const isPlaced = await read($, placed)
    const wanted = placement === 'prompt' || placement === 'both' || !isPlaced
    if (!wanted || !current || (!current.session?.active && !current.spec?.name)) return next(e)
    const book = await read($, costs)
    const usage = await $.session.usage()
    const { Box, Text, Button } = $.ui.resolve(e)
    const spec = current.spec
    const state = specState(spec?.state)
    const gateB = gateBText(current.gate_b?.state)
    const fiveHour = usage.rateLimits.find(limit => limit.kind === 'five_hour')
    const waiting = spec?.state === 'not approved' || spec?.state === 'stale'
    return (
      <Box flexDirection="row" columnGap={2}>
        <Text wrap="truncate-end">
          <Text color="claude" bold>🛠️ craft</Text>
          <Text dimColor>{'  ' + (current.session?.route ?? '')}</Text>
          {spec?.name ? `  ${spec.key} ${spec.title.slice(0, 40)}` : '  no active spec'}
          {spec?.risk === 'high' && <Text color="error">{'  risk high'}</Text>}
          <Text dimColor>{'  │  spec '}</Text>
          <Text color={state.color}>{state.glyph}</Text>
          <Text dimColor>{'  A'}</Text>
          {gateStrip(Text, current.gate_a?.items ?? [])}
          <Text dimColor>{'  B '}</Text>
          <Text color={gateB.color}>{gateB.glyph}</Text>
          <Text dimColor>{'  │  '}</Text>
          {usd(bookTotal(book)) + '  5h '}
          <Text color={levelColor(fiveHour?.percentUsed)}>{pct(fiveHour?.percentUsed)}</Text>
          {'  ctx ' + pct(usage.context.percent)}
        </Text>
        <Button key="band-board" label="board" hotkey="1" plain dimColor onPress={() => openBoard($, null)} />
        <Button key="band-cost" label="cost" hotkey="2" plain dimColor onPress={() => openBoard($, 'cost')} />
        <Button key="band-gates" label="gates" hotkey="3" plain dimColor onPress={() => openBoard($, 'gates')} />
        {waiting && <Button key="band-approve" label="approve spec…" hotkey="4" plain onPress={() => askApproval($)} />}
      </Box>
    )
  })

  // 🗂 The board. In a wide fullscreen terminal it docks beside the
  // transcript, so its header is the status at the top of the screen.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const current = await read($, snapshot)
    const active = await read($, tab)
    const book = await read($, costs)
    const message = await read($, notice)
    const asking = await read($, confirmApprove)
    const staleReason = await read($, stale)
    const usage = await $.session.usage()
    const width = Math.max(30, e.props.bodyColumns ?? 60)
    const spec = current?.spec
    const state = specState(spec?.state)
    const gateB = gateBText(current?.gate_b?.state)
    const route = current?.session?.route ?? ''
    const fiveHour = usage.rateLimits.find(limit => limit.kind === 'five_hour')
    const sevenDay = usage.rateLimits.find(limit => limit.kind === 'seven_day')
    const barWidth = Math.max(10, Math.min(30, width - 34))

    const header = (
      <Box flexDirection="column" borderStyle="round" borderColor="claude" paddingX={1}>
        <Box flexDirection="row" justifyContent="space-between" columnGap={2}>
          <Text wrap="truncate-end">
            <Text color="claude" bold>🛠️ craft</Text>
            <Text dimColor>{'  ' + (route || 'idle')}</Text>
            {spec?.name && <Text bold>{`  ${spec.key} ${spec.title}`}</Text>}
            {spec?.risk === 'high' && <Text color="error">{'  risk high'}</Text>}
          </Text>
          <Text>
            <Text bold>{usd(bookTotal(book))}</Text>
            <Text dimColor>{'  5h '}</Text>
            <Text color={levelColor(fiveHour?.percentUsed)}>{pct(fiveHour?.percentUsed)}</Text>
            <Text dimColor>{'  ctx '}</Text>
            <Text color={levelColor(usage.context.percent)}>{pct(usage.context.percent)}</Text>
          </Text>
        </Box>
        <Text wrap="truncate-end">
          <Text dimColor>{'spec '}</Text>
          <Text color={state.color}>{`${state.glyph} ${state.text}`}</Text>
          <Text dimColor>{'   A'}</Text>
          {gateStrip(Text, current?.gate_a?.items ?? [])}
          <Text dimColor>{'   B '}</Text>
          <Text color={gateB.color}>{`${gateB.glyph} ${current?.gate_b?.state ?? 'not run'}`}</Text>
        </Text>
      </Box>
    )

    const tabs = (
      <Box flexDirection="row" columnGap={1} flexWrap="wrap">
        {TABS.map(item => (
          <Button key={'tab-' + item.id} label={item.label} hotkey={item.hotkey} plain onPress={() => update($, tab, () => item.id)}>
            {active === item.id ? <Text inverse bold>{` ${item.label} `}</Text> : <Text dimColor>{` ${item.label} `}</Text>}
          </Button>
        ))}
      </Box>
    )

    let body = <Text dimColor>Loading…</Text>
    if (!current || current.error) {
      body = <Text color="error">{(current?.error ?? 'No state yet.') + ' Press r to retry.'}</Text>
    } else if (active === 'spec') {
      if (!spec?.name) {
        body = <Text dimColor>No active spec. /craft {'<request>'} starts one on the task or project route.</Text>
      } else {
        const confirm = asking && spec.state !== 'approved' && approvalBox($, { Box, Text, Button }, spec, 'the craft board')
        const approveButton = spec.state !== 'approved' && !asking && (
          <Button key="spec-approve" label="approve…" hotkey="a" plain onPress={() => update($, confirmApprove, () => true)} />
        )
        body = (
          <Box flexDirection="column">
            {confirm}
            <Text bold>{`📋 ${spec.key} · ${spec.title}`}</Text>
            <Text dimColor>
              {`${state.text}${spec.approved_at ? ' ' + spec.approved_at.slice(0, 16).replace('T', ' ') : ''} · sha ${spec.sha} · `}
              {spec.traced !== undefined ? `traced ${spec.traced}/${spec.criteria.length}` : 'not traced yet'}
            </Text>
            <Text>{' '}</Text>
            {spec.criteria.map(row => {
              const traced = Array.isArray(row.tests)
              const ok = traced ? row.tests!.length > 0 : null
              return (
                <Text key={'crit-' + row.id} wrap="truncate-end">
                  <Text color={markColor(ok)}>{mark(ok) + ' '}</Text>
                  <Text bold>{row.id.padEnd(8)}</Text>
                  {row.text.replace(/\s+/g, ' ').slice(0, Math.max(20, width - 14))}
                  {row.developer && <Text color="suggestion">{' [you]'}</Text>}
                </Text>
              )
            })}
            <Text>{' '}</Text>
            <Box flexDirection="row" columnGap={2} flexWrap="wrap">
              {approveButton}
              <Button key="spec-trace" label="re-trace" hotkey="t" plain dimColor onPress={() => retrace($)} />
              <Button key="spec-read" label="read spec.md" hotkey="o" plain dimColor onPress={() => openViewer($, 'spec')} />
            </Box>
          </Box>
        )
      }
    } else if (active === 'tasks') {
      const items = spec?.tasks ?? []
      const done = items.filter(task => task.done).length
      const nextIndex = items.findIndex(task => !task.done)
      body = items.length === 0 ? (
        <Text dimColor>No tasks yet. On a task, the checklist goes in tasks.md after approval; on a project, /plan writes it.</Text>
      ) : (
        <Box flexDirection="column">
          <Text>
            <Text bold>✅ Tasks</Text>
            <Text dimColor>{`  ${done} of ${items.length} done${spec?.tasks_state ? ' · ' + spec.tasks_state : ''}`}</Text>
          </Text>
          <Text color="success">{bar(done / items.length, barWidth)}</Text>
          <Text>{' '}</Text>
          {items.map((task, index) => (
            <Text key={'task-' + index} wrap="truncate-end">
              {task.done ? (
                <Text color="success">{'✓ '}</Text>
              ) : index === nextIndex ? (
                <Text color="claude" bold>{'▸ '}</Text>
              ) : (
                <Text dimColor>{'○ '}</Text>
              )}
              {index === nextIndex ? <Text bold>{task.text}</Text> : <Text dimColor={task.done}>{task.text}</Text>}
            </Text>
          ))}
          {current.session?.checkpoint && <Text dimColor>{'\ncheckpoint: ' + current.session.checkpoint}</Text>}
          <Button key="tasks-read" label="read tasks.md" hotkey="o" plain dimColor onPress={() => openViewer($, 'tasks')} />
        </Box>
      )
    } else if (active === 'gates') {
      const gateA = current.gate_a
      const items = gateA?.items ?? []
      const concurrency = current.stack?.concurrency
      body = (
        <Box flexDirection="column">
          <Text>
            <Text bold>🚦 Gate A — spec verified</Text>
            <Text color={gateA?.green ? 'success' : 'subtle'}>{gateA ? `  ${gateA.passed}/${gateA.total}` : ''}</Text>
          </Text>
          {items.length === 0 ? (
            <Text dimColor>{`  No check recorded yet. bin/craft-check -- ${current.session?.checkpoint || '<checkpoint>'} records one.`}</Text>
          ) : (
            items.map(item => (
              <Text key={'gate-' + item.name} wrap="truncate-end">
                {'  ' + item.name.padEnd(9)}
                <Text color={markColor(item.ok)}>{mark(item.ok)}</Text>
                <Text dimColor>{'  ' + summaryText(item.detail)}</Text>
              </Text>
            ))
          )}
          <Text>{' '}</Text>
          <Text>
            <Text bold>Gate B — review green</Text>
            <Text color={gateB.color}>{`  ${gateB.glyph} ${current.gate_b?.state ?? 'not run'}`}</Text>
          </Text>
          <Text dimColor>{`  ${current.gate_b?.rounds ?? 0} round(s) · ${current.gate_b?.blocking ?? 0} blocking · ${current.gate_b?.proposed ?? 0} to adjudicate`}</Text>
          <Text>{' '}</Text>
          <Text dimColor wrap="truncate-end">
            {`stack ${current.stack?.primary ?? '?'}${concurrency?.verdict ? ` · concurrency ${concurrency.model} ${concurrency.verdict}` : ''}`}
          </Text>
          <Text dimColor>The Stop hook refuses "done" until both gates are green.</Text>
        </Box>
      )
    } else if (active === 'review') {
      const isWaiting = (finding: { id?: string; state?: string }) => Boolean(finding.id && WAITING.has(finding.state ?? ''))
      const findings = [...(current.findings ?? [])].sort(
        (a, b) => Number(isWaiting(b)) - Number(isWaiting(a)) || severityRank(a.severity) - severityRank(b.severity),
      )
      const waiting = findings.filter(isWaiting)
      const first = waiting[0]?.id
      body = findings.length === 0 ? (
        <Text dimColor>No findings yet. /review runs the reviewer, and adjudication records them here.</Text>
      ) : (
        <Box flexDirection="column">
          <Text>
            <Text bold>🔍 Review</Text>
            <Text dimColor>{`  ${findings.length} finding(s) · ${waiting.length} waiting for you`}</Text>
          </Text>
          {findings.slice(0, 12).map((finding, index) => (
            <Box key={'finding-' + (finding.id ?? index)} flexDirection="column" marginTop={1}>
              <Text wrap="truncate-end">
                <Text color={severityColor(finding.severity)} bold>{String(finding.severity ?? '?').toUpperCase().padEnd(9)}</Text>
                <Text bold>{finding.id ?? ''}</Text>
                <Text dimColor>{` ${finding.lens ?? ''} · ${finding.where ?? ''}  `}</Text>
                <Text color={finding.state === 'confirmed' ? 'error' : finding.state === 'fixed' ? 'success' : 'warning'}>{finding.state ?? ''}</Text>
              </Text>
              <Text wrap="truncate-end">{'         ' + (finding.title ?? '')}</Text>
              {isWaiting(finding) && (
                <Box flexDirection="row" columnGap={2} marginLeft={9}>
                  <Button key={'confirm-' + finding.id} label="confirm" hotkey={finding.id === first ? 'c' : undefined} plain onPress={() => setFinding($, finding.id!, 'confirmed')} />
                  <Button key={'reject-' + finding.id} label="reject" hotkey={finding.id === first ? 'x' : undefined} plain dimColor onPress={() => setFinding($, finding.id!, 'rejected')} />
                </Box>
              )}
            </Box>
          ))}
        </Box>
      )
    } else if (active === 'cost') {
      const agents = Object.entries(book?.agents ?? {}).sort((a, b) => b[1].weight - a[1].weight)
      const total = bookTotal(book)
      const top = agents[0]?.[1].weight ?? 0
      const history = ((await $.store.get('history:' + (current.repo ?? '?'))) as { spec: string; usd: number }[]) ?? []
      body = (
        <Box flexDirection="column">
          <Text>
            <Text bold>{`💰 Cost${spec?.key ? ' · ' + spec.key : ''}  `}</Text>
            <Text bold color="claude">{usd(total)}</Text>
            <Text dimColor>{`  priced from tokens · engine ledger this session ${usd(usage.cost?.usd ?? 0)}`}</Text>
          </Text>
          <Text>{' '}</Text>
          <Text dimColor>{'agent'.padEnd(16) + 'model'.padEnd(8) + 'in'.padStart(7) + 'out'.padStart(7) + 'cache'.padStart(7) + 'cost'.padStart(8)}</Text>
          {agents.length === 0 && <Text dimColor>No model request on this spec yet.</Text>}
          {agents.map(([name, agent]) => (
            <Text key={'agent-' + name} wrap="truncate-end">
              <Text color={name === 'main' ? 'claude' : undefined}>{name.slice(0, 15).padEnd(16)}</Text>
              <Text dimColor>{shortModel(agent.model, prices).padEnd(8)}</Text>
              {tokens(agent.input + agent.cacheRead + agent.cacheWrite).padStart(7) + tokens(agent.output).padStart(7) + pct(cacheRate(agent) * 100).padStart(7)}
              <Text bold>{usd(agent.weight).padStart(8)}</Text>
              {' '}
              <Text color={name === 'main' ? 'claude' : 'suggestion'}>{bar(top ? agent.weight / top : 0, barWidth)}</Text>
            </Text>
          ))}
          <Text>{' '}</Text>
          <Text>
            {'5-hour   '}
            <Text color={levelColor(fiveHour?.percentUsed)}>{bar((fiveHour?.percentUsed ?? 0) / 100, barWidth) + ' ' + pct(fiveHour?.percentUsed)}</Text>
            <Text dimColor>{fiveHour?.resetsAt ? '  resets ' + fiveHour.resetsAt.slice(11, 16) : ''}</Text>
          </Text>
          <Text>
            {'7-day    '}
            <Text color={levelColor(sevenDay?.percentUsed)}>{bar((sevenDay?.percentUsed ?? 0) / 100, barWidth) + ' ' + pct(sevenDay?.percentUsed)}</Text>
          </Text>
          <Text>
            {'context  '}
            <Text color={levelColor(usage.context.percent)}>{bar((usage.context.percent ?? 0) / 100, barWidth) + ' ' + pct(usage.context.percent)}</Text>
          </Text>
          <Text>{' '}</Text>
          <Text dimColor wrap="truncate-end">
            {history.length
              ? 'earlier: ' + history.slice(-4).map(item => `${item.spec.replace(/^\d{4}-\d{2}-\d{2}-/, '')} ${usd(item.usd)}`).join(' · ')
              : 'earlier: no spec yet'}
          </Text>
          {Boolean(current.deciders?.decisions) && (
            <Text dimColor>{`deciders: ${current.deciders!.decisions} decision(s) · ${usd(current.deciders!.cost_total ?? 0)}`}</Text>
          )}
          <Text dimColor>Priced with config/prices.json. Subscription plans pay in limits, not dollars.</Text>
        </Box>
      )
    } else if (active === 'deciders') {
      const deciders = current.deciders
      const last = (deciders?.last ?? {}) as Record<string, unknown>
      const items = (last.items ?? {}) as Record<string, unknown>
      const votes = (last.votes ?? {}) as Record<string, unknown>
      body = (
        <Box flexDirection="column">
          <Text>
            <Text bold>🧠 Deciders</Text>
            <Text color={deciders?.enabled ? 'success' : 'subtle'}>{deciders?.enabled ? '  on' : '  off'}</Text>
            <Text dimColor>{` · mode ${deciders?.mode ?? 'first'}`}</Text>
          </Text>
          <Text dimColor wrap="truncate-end">
            {deciders?.mode === 'council' ? 'council: ' + (deciders?.council ?? []).join(', ') : 'order: ' + (deciders?.order ?? []).join(' → ')}
          </Text>
          <Text dimColor wrap="truncate-end">{'ready: ' + ((deciders?.ready ?? []).join(', ') || 'none. bin/craft-decide status says why')}</Text>
          <Text>{' '}</Text>
          {last.stage ? (
            <Box flexDirection="column">
              <Text wrap="truncate-end">
                <Text bold>{'last: ' + String(last.stage)}</Text>
                <Text dimColor>{' · ' + String(last.source ?? '')}</Text>
              </Text>
              {Object.entries(items).map(([name, value]) => (
                <Text key={'item-' + name} wrap="truncate-end">{`  ${name.padEnd(18)} ${Array.isArray(value) ? value.join(', ') : String(value)}`}</Text>
              ))}
              {Object.entries(votes).map(([member, answer]) => (
                <Text key={'vote-' + member} wrap="truncate-end">
                  {'  ' + (deciders?.labels?.[member] ?? member).padEnd(18) + ' '}
                  <Text dimColor>{voteText(answer)}</Text>
                </Text>
              ))}
            </Box>
          ) : (
            <Text dimColor>No decision yet. /craft asks the deciders when they are on; /decide turns them on.</Text>
          )}
          <Text>{' '}</Text>
          <Text dimColor>Only the request text and changed paths leave the machine, never file contents.</Text>
          <Box flexDirection="row" columnGap={2}>
            <Button key="decider-mode" label={`mode → ${deciders?.mode === 'council' ? 'first' : 'council'}`} hotkey="m" plain onPress={() => toggleMode($)} />
            <Button key="decider-ping" label="ping the chain" hotkey="p" plain dimColor onPress={() => pingDeciders($)} />
          </Box>
        </Box>
      )
    }

    return (
      <Box flexDirection="column" rowGap={1}>
        {header}
        {staleReason && (
          <Text color="warning" wrap="truncate-end">{`◐ Showing the last good state. ${staleReason} · r retries`}</Text>
        )}
        {tabs}
        {body}
        {message && <Text color="suggestion" wrap="wrap">{message}</Text>}
        <Box flexDirection="row" columnGap={2}>
          <Button key="board-refresh" label="refresh" hotkey="r" plain dimColor onPress={() => refresh($)} />
          <Text dimColor>1–6 tabs · esc closes</Text>
        </Box>
      </Box>
    )
  })

  // 📄 The viewer: a spec document as Markdown, in a pane of its own.
  on('ui.render', { component: 'Pane', requestId: VIEWER }, async ($, e) => {
    const { Box, Text, Button, Markdown } = $.ui.resolve(e)
    const current = await read($, snapshot)
    const which = await read($, doc)
    const asking = await read($, confirmApprove)
    const spec = current?.spec
    if (!current?.repo || !spec?.name) {
      return <Text dimColor>No active spec. /craft {'<request>'} starts one on the task or project route.</Text>
    }
    const file = DOCS.find(item => item.id === which)?.file ?? 'spec.md'
    let text: string | null = null
    try {
      text = String(await $.fs.read(current.repo + '/.claude/specs/' + spec.name + '/' + file))
    } catch {
      text = null
    }
    const waiting = spec.state !== 'approved'
    return (
      <Box flexDirection="column" rowGap={1}>
        <Box flexDirection="row" columnGap={1} flexWrap="wrap">
          {DOCS.map(item => (
            <Button key={'doc-' + item.id} label={item.file} hotkey={item.hotkey} plain onPress={() => update($, doc, () => item.id)}>
              {item.id === which ? <Text inverse bold>{` ${item.file} `}</Text> : <Text dimColor>{` ${item.file} `}</Text>}
            </Button>
          ))}
          {waiting && !asking && (
            <Button key="spec-approve" label="approve…" hotkey="a" plain onPress={() => update($, confirmApprove, () => true)} />
          )}
        </Box>
        {waiting && asking && approvalBox($, { Box, Text, Button }, spec, 'the craft viewer')}
        {text === null ? (
          <Text dimColor>{`${file} does not exist for ${spec.name}.`}</Text>
        ) : (
          <Markdown text={docText(text, Math.max(30, e.props.bodyColumns ?? 80))} />
        )}
        <Text dimColor>s d t l switch · esc closes</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => next(e))
}
