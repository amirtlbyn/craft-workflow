// Tests for the craft mod, run with `claude plugin test` from the plugin root.
// No session, no network, no Python: the test answers every call the mod makes
// beneath it, so each test states the world it runs in.

import { expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

const REPO = '/repo'
const SURFACES = ['terminal', 'desktop'] as const

type World = {
  argv: string[][]
  snapshot: Record<string, unknown>
  asked: string[]
  toasts: string[]
  submitted: string[]
  failUi: boolean
  clock: MockClock
  docs: Record<string, string>
  opened: Record<string, unknown>[]
}

function snapshotFor(specState: string): Record<string, unknown> {
  return {
    version: 1,
    repo: REPO,
    stack: {
      primary: 'go',
      label: 'Go',
      emoji: '🐹',
      detected: true,
      stacks: [{ id: 'go', dir: '', emoji: '🐹', label: 'Go', evidence: 'go.mod' }],
      concurrency: { model: 'goroutines', verdict: 'ready', skill: 'go-concurrency' },
    },
    session: { active: true, route: 'task', checkpoint: 'go test ./...' },
    spec: {
      name: '2026-10-10-daily-limit',
      state: specState,
      title: 'Daily withdrawal limit',
      risk: 'high',
      sha: '3f2a9c1e',
      approved_at: '',
      key: 'WDL',
      criteria: [
        { id: 'WDL-1', text: 'WHEN over the limit, THE service SHALL refuse.', class: 'BUSINESS RULE', developer: false, tests: ['limit_test.go::TestLimit'] },
        { id: 'WDL-2', text: 'A cancelled withdrawal SHALL NOT count. [developer]', class: 'BUSINESS RULE', developer: true, tests: [] },
      ],
      tasks: [
        { done: true, text: 'T1 — limit check in Withdraw()' },
        { done: false, text: 'T2 — cancelled withdrawals' },
      ],
      tasks_state: 'in progress',
      next_task: 'T2 — cancelled withdrawals',
      traced: 1,
    },
    checks: {},
    gate_a: {
      items: [
        { name: 'trace', ok: false, detail: 'exit 1' },
        { name: 'tests', ok: true, detail: { passed: 42, failed: 0 } },
        { name: 'race', ok: true, detail: {} },
      ],
      passed: 2,
      total: 3,
      green: false,
      started: true,
    },
    gate_b: { state: 'in review', green: false, blocking: 0, proposed: 1, rounds: 1 },
    findings: [{ id: 'F1', severity: 'High', lens: 'logic', where: 'ledger.go:88', title: 'Counter read before the lock', state: 'proposed' }],
    deciders: { enabled: true, mode: 'council', council: ['jev', 'groq', 'ollama'], order: ['jev'], ready: ['jev', 'ollama'], labels: {}, last: null },
  }
}

function world(on: On, specState = 'approved'): World {
  mock.store(on)
  const state: World = {
    argv: [],
    snapshot: snapshotFor(specState),
    asked: [],
    toasts: [],
    submitted: [],
    failUi: false,
    clock: mock.clock(on),
    docs: { 'spec.md': '# SPEC: Daily withdrawal limit\n\n<!-- template note -->\nThe limit text.', 'tasks.md': '# TASKS\n\n- [x] T1', 'log.md': '# LOG\n\n## spec approved' },
    opened: [],
  }
  on('session.start', () => ({ cwd: REPO }))
  on('session.cwd', () => ({ value: REPO }))
  on('session.usage', () => ({ value: {
    startedAt: 0,
    context: { tokens: 120000, window: 200000, percent: 60 },
    rateLimits: [{ kind: 'five_hour', percentUsed: 42, resetsAt: '2026-10-10T18:30:00Z' }],
    cost: { usd: 1.25 },
  } }))
  on('fs.read', ($, e) => {
    const path = String((e as { path?: string }).path ?? '')
    if (path.endsWith('.md')) {
      const text = state.docs[path.split('/').pop() ?? '']
      return text === undefined ? { deny: 'ENOENT: ' + path } : { value: text }
    }
    return { value: PRICES }
  })
  const PRICES = JSON.stringify({ families: [{ family: 'opus', match: ['opus'], input: 5, output: 25, cache_write: 6.25, cache_read: 0.5 }, { family: 'sonnet', match: ['sonnet'], input: 3, output: 15, cache_write: 3.75, cache_read: 0.3 }, { family: 'other', match: [''], input: 3, output: 15, cache_write: 3.75, cache_read: 0.3 }] })
  on('process.run', ($, e) => {
    const argv = [...(e as { argv: string[] }).argv]
    state.argv.push(argv)
    const script = argv[1] ?? ''
    if (script.endsWith('craft-ui-state')) {
      const stdout = JSON.stringify(state.failUi ? { version: 1, error: 'ValueError: boom' } : state.snapshot)
      return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    if (script.endsWith('craft-approve')) {
      state.snapshot = snapshotFor('approved')
      return { value: { exitCode: 0, stdout: 'Approved.', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    }
    if (script.endsWith('craft-spec')) return { value: { exitCode: 1, stdout: 'trace: x\nresult: FAIL — 1 of 2 criteria have a test\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    return { value: { exitCode: 0, stdout: 'ok', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('agent.list', () => ({ value: [] }))
  on('ui.open', ($, e) => {
    state.opened.push({ ...(e as Record<string, unknown>) })
    return { value: { isPlaced: true } }
  })
  on('ui.toast', ($, e) => {
    state.toasts.push(String((e as { text?: string }).text ?? e))
    return { value: undefined }
  })
  on('prompt.submit', ($, e) => {
    state.submitted.push(e.text)
    return { text: e.text } as never
  })
  on('ui.log', () => ({ value: undefined }))
  on('command.register', ($, e) => ({ value: { command: e.name } }) as never)
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e as never) as { Text: (props: { children: string[] }) => unknown }
    return Text({ children: ['the engine draws its own'] }) as never
  })
  return state
}

function answerAsk(on: On, state: World, prefix: string) {
  on('tool.call', { tool: 'AskUserQuestion' }, ($, e) => {
    const question = (e as unknown as { questions: { question: string; options: { label: string }[] }[] }).questions[0]!
    const labels = question.options.map(option => option.label)
    state.asked.push(...labels)
    const label = labels.find(option => option.startsWith(prefix)) ?? ''
    return { result: { questions: [question], answers: { [question.question]: label } } } as never
  })
}

async function start($: Engine) {
  await $.session.start({ cwd: REPO, surface: 'terminal', isInteractive: true } as never)
}

const PANE_PROPS = {
  title: '🗂 Craft',
  isFocused: true,
  bodyColumns: 70,
  placement: 'dock',
  scroll: { offset: 0, bodyRows: 40 },
  view: {},
} as const

const VIEWER_PROPS = { ...PANE_PROPS, title: '📄 spec.md', bodyColumns: 70 } as const

async function viewerText(ui: { find: (query: Record<string, unknown>) => Promise<{ props: Record<string, unknown> } | undefined> }) {
  return String((await ui.find({ type: 'Markdown' }))?.props.text ?? '')
}

const BAND_PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 12,
  bodyColumns: 120,
  scroll: { offset: 0, bodyRows: 12 },
  view: {},
} as const

test('/craft-status answers with the status, and no Claude turn', async ($, on) => {
  world(on)
  await start($)
  const answer = await $.command.run({ command: 'craft-status', args: '' } as never)
  const text = String((answer as { text?: string }).text)
  expect(text).toContain('🛠️ craft')
  expect(text).toContain('📦 task WDL')
  expect(text).toContain('🐹 go')
  expect(text).toContain('🧵 concurrency: goroutines · ready')
})

test('/craft-gates lists every Gate A check with its mark', async ($, on) => {
  world(on)
  await start($)
  const answer = await $.command.run({ command: 'craft-gates', args: '' } as never)
  const text = String((answer as { text?: string }).text)
  expect(text).toContain('🅰️ Gate A — spec verified: 2/3')
  expect(text).toContain('🔗 trace')
  expect(text).toContain('✗')
  expect(text).toContain('42 passed')
})

test('the board draws its status header and switches tabs on every surface', async ($, on) => {
  world(on)
  await start($)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ plugin: 'craft-workflow', surface, component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
    expect(await ui.find({ type: 'Text', text: /🛠️ craft/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /WDL-2/ })).toBeDefined()
    await ui.press({ key: 'tab-cost' })
    expect(await ui.find({ type: 'Text', text: /5-hour/ })).toBeDefined()
    await ui.press({ key: 'tab-review' })
    expect(await ui.find({ type: 'Text', text: /Counter read before the lock/ })).toBeDefined()
    await ui.press({ key: 'tab-spec' })
    await ui.unmount()
  }
})

test('CMOD-3: approve on the board shows title, sha and criteria count, and runs craft-approve only on confirm', async ($, on) => {
  const state = world(on, 'not approved')
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  const approved = () => state.argv.some(argv => String(argv[1]).endsWith('craft-approve'))
  await ui.press({ key: 'spec-approve' })
  expect(approved()).toBe(false)
  expect(await ui.find({ type: 'Text', text: /Approve "Daily withdrawal limit"\?/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /sha 3f2a9c1e · 2 criteria/ })).toBeDefined()
  await ui.press({ key: 'spec-cancel' })
  expect(approved()).toBe(false)
  expect(await ui.find({ key: 'spec-confirm' })).toBeUndefined()
  await ui.press({ key: 'spec-approve' })
  await ui.press({ key: 'spec-confirm' })
  expect(approved()).toBe(true)
  await ui.unmount()
})

test('confirming a finding writes its state through craft-session', async ($, on) => {
  const state = world(on)
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'tab-review' })
  await ui.press({ key: 'confirm-F1' })
  const call = state.argv.find(argv => String(argv[1]).endsWith('craft-session'))
  expect(call).toEqual(expect.arrayContaining(['finding', 'F1', '--state', 'confirmed']))
  await ui.unmount()
})

test('the band stays away while the board is placed, with status at the top', async ($, on) => {
  world(on)
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS as never })
  expect(await ui.find({ type: 'Text', text: /🛠️ craft/ })).toBeUndefined()
  await ui.unmount()
})

test('with status "both" the band shows the gates and the cost', { options: { status: 'both' } }, async ($, on) => {
  world(on)
  await start($)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ plugin: 'craft-workflow', surface, component: 'AbovePrompt', props: BAND_PROPS as never })
    expect(await ui.find({ type: 'Text', text: /🛠️ craft/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /5h/ })).toBeDefined()
    expect(await ui.find({ key: 'band-board' })).toBeDefined()
    await ui.unmount()
  }
})

test('the spec gate asks, and approving in the dialog lets the write through', async ($, on) => {
  const state = world(on, 'not approved')
  answerAsk(on, state, '✅')
  on('tool.call', { tool: 'Write' }, () => ({ result: 'written' }))
  await start($)
  const result = await $.tool.call({ tool: 'Write', file_path: REPO + '/internal/wallet/limit.go', content: 'package wallet' } as never)
  expect(state.asked.length).toBe(3)
  expect(state.argv.some(argv => String(argv[1]).endsWith('craft-approve'))).toBe(true)
  expect((result as { deny?: string }).deny).toBeUndefined()
})

test('keeping the gate shut refuses the write with a reason Claude can act on', async ($, on) => {
  const state = world(on, 'not approved')
  answerAsk(on, state, '🚫')
  on('tool.call', { tool: 'Write' }, () => ({ result: 'written' }))
  await start($)
  const result = await $.tool.call({ tool: 'Write', file_path: REPO + '/internal/wallet/limit.go', content: 'x' } as never)
  expect(String((result as { deny?: string; text?: string }).deny ?? (result as { text?: string }).text)).toContain('spec gate shut')
})

test('a write under .claude/ is never asked about', async ($, on) => {
  const state = world(on, 'not approved')
  answerAsk(on, state, '🚫')
  on('tool.call', { tool: 'Write' }, () => ({ result: 'written' }))
  await start($)
  await $.tool.call({ tool: 'Write', file_path: REPO + '/.claude/specs/x/spec.md', content: 'x' } as never)
  expect(state.asked.length).toBe(0)
})

test('each model request lands on its own agent in the cost tab', async ($, on) => {
  world(on)
  on('agent.spawn', () => ({ model: 'sonnet', agentId: 'agent-1' }) as never)
  on('turn.step', async function* () {
    return {
      turnId: 'turn-1',
      index: 0,
      answer: '',
      toolUses: [],
      stopReason: 'end_turn',
      usage: { model: 'claude-sonnet-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 9000, cache_creation_input_tokens: 0 },
    } as never
  })
  await start($)
  await $.agent.spawn({ prompt: 'review the diff', subagentType: 'craft-workflow:reviewer', description: 'review' } as never)
  const stream = $.turn.step({ turnId: 'turn-1', index: 0, model: 'sonnet', messageCount: 3, agentId: 'agent-1' } as never)
  for await (const _chunk of stream as AsyncIterable<unknown>) {
    // drain the stream; the result is what the mod's hook saw
  }
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'tab-cost' })
  const row = await ui.find({ type: 'Text', text: /^reviewer / })
  expect(row?.text).toContain('reviewer')
  expect(row?.text).toContain('$0.04')
  await ui.unmount()
})

test('CMOD-1: cost rows of main, reviewer and deep-reviewer put the cost at the same column', async ($, on) => {
  world(on)
  const types: Record<string, string> = { 'craft-workflow:reviewer': 'agent-r', 'craft-workflow:deep-reviewer': 'agent-d' }
  on('agent.spawn', ($, e) => ({ model: 'sonnet', agentId: types[(e as { subagentType: string }).subagentType] }) as never)
  on('turn.step', async function* () {
    return {
      turnId: 'turn-1',
      index: 0,
      answer: '',
      toolUses: [],
      stopReason: 'end_turn',
      usage: { model: 'claude-opus-5-5', input_tokens: 12000, output_tokens: 3000, cache_read_input_tokens: 900000, cache_creation_input_tokens: 0 },
    } as never
  })
  await start($)
  for (const subagentType of Object.keys(types)) {
    await $.agent.spawn({ prompt: 'review', subagentType, description: 'review' } as never)
  }
  for (const agentId of [undefined, 'agent-r', 'agent-d']) {
    const stream = $.turn.step({ turnId: 'turn-1', index: 0, model: 'opus', messageCount: 3, agentId } as never)
    for await (const _chunk of stream as AsyncIterable<unknown>) {
      // drain the stream
    }
  }
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'tab-cost' })
  // A row is the Text that holds the whole line, the cost included.
  const rows = (await ui.findAll({ type: 'Text', text: /^(main|reviewer|deep-reviewer) .*\$/ }))
  expect(rows.map(row => row.text.split(' ')[0]).sort()).toEqual(['deep-reviewer', 'main', 'reviewer'])
  // Up to the bar, each row is plain ASCII, so a character is one terminal column.
  const cells = rows.map(row => row.text.replace(/ [█░]+$/, ''))
  for (const cell of cells) expect(cell).toMatch(/^[\x20-\x7e]+\$\d+\.\d\d$/)
  expect(new Set(cells.map(cell => cell.length)).size).toBe(1)
  expect(new Set(cells.map(cell => cell.lastIndexOf(' ') + 1)).size).toBe(1)
  await ui.unmount()
})

test('CMOD-2: header and band show each Gate A check by name with a coloured ✓ ✗ ○', { options: { status: 'both' } }, async ($, on) => {
  const state = world(on)
  const gateA = state.snapshot.gate_a as { items: { name: string; ok: boolean | null; detail: unknown }[] }
  gateA.items.push({ name: 'lint', ok: null, detail: 'not run' })
  await start($)
  for (const component of ['Pane', 'AbovePrompt'] as const) {
    const props = component === 'Pane' ? PANE_PROPS : BAND_PROPS
    const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component, ...(component === 'Pane' ? { requestId: 'craft-board' } : {}), props: props as never })
    for (const [name, glyph, color] of [['trace', '✗', 'error'], ['tests', '✓', 'success'], ['lint', '○', 'subtle']]) {
      const strip = await ui.find({ type: 'Text', text: new RegExp(`^ ${name} ${glyph}$`) })
      expect(strip).toBeDefined()
      const mark = (strip?.children ?? []).find(child => typeof child === 'object' && (child as { props?: { color?: string } }).props?.color)
      expect((mark as { props: { color: string } }).props.color).toBe(color)
    }
    expect(await ui.find({ type: 'Text', text: /❌|✅|🔗/ })).toBeUndefined()
    await ui.unmount()
  }
})

test('CMOD-4: confirming on the board after the gate refused an edit submits one prompt to retry it', async ($, on) => {
  const state = world(on, 'not approved')
  answerAsk(on, state, '👀')
  on('tool.call', { tool: 'Write' }, () => ({ result: 'written' }))
  await start($)
  const refused = await $.tool.call({ tool: 'Write', file_path: REPO + '/internal/wallet/limit.go', content: 'x' } as never)
  expect((refused as { deny?: string }).deny).toBeDefined()
  expect(state.submitted).toEqual([])
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'spec-approve' })
  await ui.press({ key: 'spec-confirm' })
  await state.clock.settle()
  expect(state.submitted).toHaveLength(1)
  expect(state.submitted[0]).toContain('approved the spec')
  expect(state.submitted[0]).toContain('internal/wallet/limit.go')
  await ui.unmount()
})

test('keeping the gate shut does not resume Claude after a later approval on the board', async ($, on) => {
  const state = world(on, 'not approved')
  answerAsk(on, state, '🚫')
  on('tool.call', { tool: 'Write' }, () => ({ result: 'written' }))
  await start($)
  await $.tool.call({ tool: 'Write', file_path: REPO + '/internal/wallet/limit.go', content: 'x' } as never)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'spec-approve' })
  await ui.press({ key: 'spec-confirm' })
  await state.clock.settle()
  expect(state.argv.some(argv => String(argv[1]).endsWith('craft-approve'))).toBe(true)
  expect(state.submitted).toEqual([])
  await ui.unmount()
})

test('CMOD-5: a notice clears 8 seconds after it is shown, and a newer notice restarts the wait', async ($, on) => {
  const state = world(on)
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'spec-trace' })
  expect(await ui.find({ type: 'Text', text: /^trace result: FAIL/ })).toBeDefined()
  await state.clock.advance(5_000)
  await ui.press({ key: 'tab-deciders' })
  await ui.press({ key: 'decider-mode' })
  expect(await ui.find({ type: 'Text', text: /^decider mode: first/ })).toBeDefined()
  await state.clock.advance(4_000)
  expect(await ui.find({ type: 'Text', text: /^decider mode: first/ })).toBeDefined()
  await state.clock.advance(4_500)
  expect(await ui.find({ type: 'Text', text: /^decider mode: first/ })).toBeUndefined()
  await ui.unmount()
})

test('CMOD-6: both gates turning green on one refresh raise exactly one toast', async ($, on) => {
  const state = world(on)
  await start($)
  expect(state.toasts).toEqual([])
  ;(state.snapshot.gate_a as { green: boolean }).green = true
  ;(state.snapshot.gate_b as { state: string }).state = 'green'
  await $.command.run({ command: 'craft-status', args: '' } as never)
  expect(state.toasts).toEqual(['🎉 Both gates green: /finish'])
})

test('CMOD-7: a failed craft-ui-state keeps the last good board and names the failure with r to retry', async ($, on) => {
  const state = world(on)
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  state.failUi = true
  await ui.press({ key: 'board-refresh' })
  expect(await ui.find({ type: 'Text', text: /WDL-2/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /last good state\. ValueError: boom · r retries/ })).toBeDefined()
  expect((await ui.find({ key: 'board-refresh' }))?.props.hotkey).toBe('r')
  state.failUi = false
  await ui.press({ key: 'board-refresh' })
  expect(await ui.find({ type: 'Text', text: /last good state/ })).toBeUndefined()
  await ui.unmount()
})

test('CMOD-8: c and x act on the first finding waiting for adjudication, most severe first', async ($, on) => {
  const state = world(on)
  state.snapshot.findings = [
    { id: 'F1', severity: 'Low', lens: 'style', where: 'a.go:1', title: 'Name', state: 'proposed' },
    { id: 'F2', severity: 'High', lens: 'logic', where: 'b.go:2', title: 'Race', state: 'proposed' },
    { id: 'F3', severity: 'Critical', lens: 'logic', where: 'c.go:3', title: 'Fixed already', state: 'fixed' },
  ]
  await start($)
  const ui = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  await ui.press({ key: 'tab-review' })
  const confirms = (await ui.findAll({ type: 'Button' })).filter(button => String(button.key).startsWith('confirm-'))
  expect(confirms.map(button => button.key)).toEqual(['confirm-F2', 'confirm-F1'])
  expect((await ui.find({ key: 'confirm-F2' }))?.props.hotkey).toBe('c')
  expect((await ui.find({ key: 'reject-F2' }))?.props.hotkey).toBe('x')
  expect((await ui.find({ key: 'confirm-F1' }))?.props.hotkey).toBeUndefined()
  expect((await ui.find({ key: 'reject-F1' }))?.props.hotkey).toBeUndefined()
  await ui.unmount()
})

test('CSL-9: o on the spec and tasks tabs opens the viewer pane, focused, Escape closes it, comments removed', async ($, on) => {
  const state = world(on)
  await start($)
  const board = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-board', props: PANE_PROPS as never })
  expect((await board.find({ key: 'spec-read' }))?.props.hotkey).toBe('o')
  await board.press({ key: 'spec-read' })
  expect(state.opened.at(-1)).toMatchObject({ id: 'craft-doc', focus: true, closeOnEscape: true })
  const viewer = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-doc', props: VIEWER_PROPS as never })
  const spec = await viewerText(viewer)
  expect(spec).toContain('# SPEC: Daily withdrawal limit')
  expect(spec).toContain('The limit text.')
  expect(spec).not.toContain('template note')
  await viewer.unmount()
  await board.press({ key: 'tab-tasks' })
  expect((await board.find({ key: 'tasks-read' }))?.props.hotkey).toBe('o')
  await board.press({ key: 'tasks-read' })
  expect(state.opened.at(-1)).toMatchObject({ id: 'craft-doc', focus: true, closeOnEscape: true })
  const tasks = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-doc', props: VIEWER_PROPS as never })
  expect(await viewerText(tasks)).toContain('- [x] T1')
  await tasks.unmount()
  await board.unmount()
})

test('CSL-10: s d t l switch the viewer between the spec files, and a missing file says so in one line', async ($, on) => {
  world(on)
  await start($)
  const viewer = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-doc', props: VIEWER_PROPS as never })
  const hotkeys = await Promise.all(['spec', 'design', 'tasks', 'log'].map(async id => (await viewer.find({ key: 'doc-' + id }))?.props.hotkey))
  expect(hotkeys).toEqual(['s', 'd', 't', 'l'])
  await viewer.press({ key: 'doc-design' })
  expect(await viewer.find({ type: 'Text', text: /design\.md does not exist for 2026-10-10-daily-limit\./ })).toBeDefined()
  expect(await viewer.find({ type: 'Markdown' })).toBeUndefined()
  await viewer.press({ key: 'doc-log' })
  expect(await viewerText(viewer)).toContain('## spec approved')
  await viewer.press({ key: 'doc-tasks' })
  expect(await viewerText(viewer)).toContain('- [x] T1')
  await viewer.press({ key: 'doc-spec' })
  expect(await viewerText(viewer)).toContain('The limit text.')
  await viewer.unmount()
})

test('CSL-11: the viewer offers approve on a spec not approved, and runs craft-approve only after the confirm', async ($, on) => {
  const state = world(on, 'not approved')
  await start($)
  const approved = () => state.argv.some(argv => String(argv[1]).endsWith('craft-approve'))
  const viewer = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-doc', props: VIEWER_PROPS as never })
  await viewer.press({ key: 'spec-approve' })
  expect(approved()).toBe(false)
  expect(await viewer.find({ type: 'Text', text: /Approve "Daily withdrawal limit"\?/ })).toBeDefined()
  await viewer.press({ key: 'spec-cancel' })
  expect(approved()).toBe(false)
  await viewer.press({ key: 'spec-approve' })
  await viewer.press({ key: 'spec-confirm' })
  expect(approved()).toBe(true)
  expect(await viewer.find({ key: 'spec-approve' })).toBeUndefined()
  await viewer.unmount()
})

test('CSL-12: a table wider than the pane becomes one block per row, and a table that fits stays a table', async ($, on) => {
  const state = world(on)
  const criterion = 'IF a request asks for more rows than the export limit, THEN THE export API SHALL reject it and export nothing.'
  const failure = 'One request exports the whole table and times out the worker.'
  state.docs['spec.md'] = [
    '| ID | Criterion | Class | Failure it catches |',
    '|---|---|---|---|',
    `| EXP-3 | ${criterion} | SECURITY BOUNDARY | ${failure} |`,
    '',
    '| Key | Value |',
    '|---|---|',
    '| a | b |',
  ].join('\n')
  await start($)
  const viewer = await $.ui.mount({ plugin: 'craft-workflow', surface: 'terminal', component: 'Pane', requestId: 'craft-doc', props: VIEWER_PROPS as never })
  const text = await viewerText(viewer)
  expect(text).toContain('**EXP-3** · SECURITY BOUNDARY')
  expect(text).toContain(`*Criterion:* ${criterion}`)
  expect(text).toContain(`*Failure it catches:* ${failure}`)
  expect(text).not.toContain('| EXP-3 |')
  expect(text).toContain('| Key | Value |\n|---|---|\n| a | b |')
  await viewer.unmount()
})
