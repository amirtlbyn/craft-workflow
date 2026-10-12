// The craft mod's state contract. claude plugin validate holds every $.state key
// the hooks module names to this file.

export type Tab = 'spec' | 'tasks' | 'gates' | 'review' | 'cost' | 'deciders'
export type DocName = 'spec' | 'design' | 'tasks' | 'log'

export type CheckView = {
  exit_code: number | null
  at?: string
  command: string
  summary: Record<string, number | string | null>
}

export type GateItem = { name: string; ok: boolean | null; detail: unknown }

export type Finding = {
  id?: string
  severity?: string
  lens?: string
  where?: string
  title?: string
  state?: string
}

export type Criterion = {
  id: string
  text: string
  class: string
  developer: boolean
  tests?: string[] | null
}

export type Snapshot = {
  version: number
  error?: string
  repo?: string
  stack?: {
    primary: string
    label: string
    emoji: string
    detected: boolean
    stacks: { id: string; dir: string; emoji: string; label: string; evidence: string }[]
    concurrency: { model?: string; verdict?: string; skill?: string; summary?: string }
  }
  session?: { active: boolean; route: string; checkpoint: string }
  spec?: {
    name: string
    state: string
    title: string
    risk: string
    sha: string
    approved_at: string
    key: string
    criteria: Criterion[]
    tasks: { done: boolean; text: string }[]
    tasks_state: string
    next_task: string
    traced?: number
    trace_at?: string
  }
  checks?: Record<string, CheckView>
  gate_a?: { items: GateItem[]; passed: number; total: number; green: boolean; started: boolean }
  gate_b?: { state: string; green: boolean; blocking: number; proposed: number; rounds: number }
  findings?: Finding[]
  deciders?: {
    enabled: boolean
    approve?: boolean
    mode?: string
    order?: string[]
    council?: string[]
    ready?: string[]
    labels?: Record<string, string>
    cost_total?: number
    decisions?: number
    last?: Record<string, unknown> | null
  }
}

export type AgentCost = {
  model: string
  input: number
  output: number
  cacheRead: number
  cacheWrite: number
  steps: number
  weight: number
}

export type CostBook = {
  key: string
  startedAt: number
  agents: Record<string, AgentCost>
  ledgerAtStart: number
}

declare module 'claude-code' {
  interface PluginState {
    'craft-workflow': {
      snapshot: Snapshot | null
      tab: Tab
      costs: CostBook | null
      notice: string
      doc: DocName
      placed: boolean
      confirmApprove: boolean
      stale: string
    }
  }
}
