export type SessionKind = 'practice' | 'qualifying' | 'sprint_qualifying' | 'sprint' | 'race'

export interface Move {
  label: string
  pct: number
}

export interface Tick {
  id: string
  driver_code: string
  race: string
  round: number
  session: string
  session_name: string
  kind: SessionKind
  position: number | null
  expected: number
  grid: number | null
  status: string | null
  points: number
  fastest_lap: boolean
  value_before: number
  value_after: number
  change_pct: number
  moves: Move[]
  ts: number
  live: boolean
}

export interface DriverMeta {
  code: string
  name: string
  number: number
  country: string
  team: string
  active: boolean
}

export interface Team {
  name: string
  color: string
}

export interface Session {
  key: string
  name: string
  kind: SessionKind
  ts: number
}

export interface Race {
  round: number
  name: string
  short: string
  country: string
  circuit: string
  dates: string[]
  sprint: boolean
  historical: boolean
  sessions: Session[]
}

export interface ValueRecord {
  driver_code: string
  driver_name: string
  team: string
  baseline_value: number
  current_value: number
}

export interface SimStatus {
  running: boolean
  race?: string
  round?: number
  speed?: string
  session?: string
  session_name?: string
  kind?: SessionKind
  session_index?: number
  total_sessions?: number
  phase?: 'starting' | 'live'
  sent?: number
  field?: number
  warning?: string | null
  finished?: string
  stopped?: boolean
  data?: DataSource
  /** Unix seconds; in public mode the next weekend can't start before this. */
  cooldown_until?: number
}

export type DataSource = 'real' | 'simulated'

export type Mode = 'kafka' | 'demo' | 'static'

export interface Snapshot {
  mode: Mode
  data: DataSource
  public: boolean
  game: { starting_cash: number }
  ready: boolean
  epoch: number | null
  roster: { drivers: Record<string, DriverMeta>; teams: Record<string, Team> }
  calendar: Race[]
  values: Record<string, ValueRecord>
  ticks: Tick[]
  sim: SimStatus
  next_race: string | null
}

export type Range = 'session' | 'weekend' | 'season'

export type ServerMessage =
  | { type: 'snapshot'; data: Snapshot }
  | { type: 'tick'; tick: Tick }
  | { type: 'sim'; sim: SimStatus; next_race: string | null }
  | { type: 'game' }
