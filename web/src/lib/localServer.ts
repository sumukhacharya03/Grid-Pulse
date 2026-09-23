/**
 * The browser-only edition's "server" (GitHub Pages build).
 *
 * The Python engine prices the whole real 2025 season ahead of time
 * (scripts/publish_pages.py -> market.json). This replays those ticks with
 * the same messages and timing as the dashboard server, and runs the trading
 * game in localStorage with the same rules as gridpulse/game.py. Here the
 * leaderboard is you against the market: $100k put into the Pulse Index
 * when the live season starts.
 */
import { ApiError } from './apiError'
import type { ServerMessage, SimStatus, Snapshot, Tick } from './types'

interface LiveSession { session: string; field: number; ticks: Tick[] }
interface LiveRace { race: string; round: number; sessions: LiveSession[] }
interface StaticData { snapshot: Snapshot; live: LiveRace[] }
interface Holding { units: number; cost: number }
interface Season { cash: number; holdings: Record<string, Holding>; trades: { driver_code: string; side: 'buy' | 'sell'; amount: number; price: number; ts: number }[] }
interface GameState { name: string | null; seasons: Record<string, Season> }

// Seconds between results / before each session, as in gridpulse/server.py.
const SPEEDS: Record<string, [number, number]> = { normal: [1.1, 3.0], fast: [0.3, 1.2], instant: [0, 0] }
const LIVE_QUIET_MS = 8000
const MIN_TRADE = 100
const NAME_RE = /^[A-Za-z0-9][A-Za-z0-9 _.-]{1,18}[A-Za-z0-9]$/
const TOKEN = 'local'
const MARKET_KEY = 'gp.static.market'
const GAME_KEY = 'gp.static.game'

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable: progress lasts for this tab only */
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

class LocalServer {
  private data!: StaticData
  private flat: { race: number; session: number; tick: Tick }[] = []
  private progress = 0 // live ticks already played
  private season = 1
  private sim: SimStatus = { running: false }
  private stopRequested = false
  private generation = 0 // bumped per run and on reset, so a stale loop stops and stays quiet
  private lastLiveAt = 0
  private listeners = new Set<(m: ServerMessage) => void>()
  readonly ready: Promise<void>

  constructor() {
    this.ready = this.init()
  }

  private async init() {
    const res = await fetch(`${import.meta.env.BASE_URL}market.json`)
    if (!res.ok) throw new Error(`market.json: ${res.status}`)
    this.data = (await res.json()) as StaticData
    this.data.live.forEach((race, r) => race.sessions.forEach((s, i) => s.ticks.forEach((tick) => this.flat.push({ race: r, session: i, tick }))))
    const saved = load(MARKET_KEY, { season: 1, progress: 0 })
    this.season = saved.season
    this.progress = Math.min(saved.progress, this.flat.length)
  }

  // ---- market -------------------------------------------------------------
  subscribe(fn: (m: ServerMessage) => void) {
    this.listeners.add(fn)
    fn({ type: 'snapshot', data: this.snapshot() })
    return () => this.listeners.delete(fn)
  }

  private emit(m: ServerMessage) {
    this.listeners.forEach((fn) => fn(m))
  }

  private liveTicks() {
    return this.flat.slice(0, this.progress).map((f) => f.tick)
  }

  private nextRace(): string | null {
    const next = this.flat[this.progress]
    return next ? this.data.live[next.race].race : null
  }

  private snapshot(): Snapshot {
    return {
      ...this.data.snapshot,
      epoch: this.season,
      ticks: [...this.data.snapshot.ticks, ...this.liveTicks()],
      sim: this.sim,
      next_race: this.nextRace(),
    }
  }

  private setSim(sim: SimStatus) {
    this.sim = sim
    this.emit({ type: 'sim', sim, next_race: this.nextRace() })
  }

  private persist() {
    save(MARKET_KEY, { season: this.season, progress: this.progress })
  }

  private prices(): Record<string, number> {
    const prices: Record<string, number> = {}
    for (const [code, v] of Object.entries(this.data.snapshot.values)) prices[code] = v.baseline_value
    for (const t of [...this.data.snapshot.ticks, ...this.liveTicks()]) prices[t.driver_code] = t.value_after
    return prices
  }

  private start(speed: string) {
    if (this.sim.running) throw new ApiError(409, 'A weekend is already running')
    if (!(speed in SPEEDS)) throw new ApiError(400, `speed must be one of ${Object.keys(SPEEDS).join(', ')}`)
    if (this.progress >= this.flat.length) throw new ApiError(400, 'The season is complete. Reset the market to race again.')
    this.stopRequested = false
    this.generation++
    const raceIndex = this.flat[this.progress].race
    this.sim = { running: true, race: this.data.live[raceIndex].race, round: this.data.live[raceIndex].round, phase: 'starting' }
    void this.run(raceIndex, speed, this.generation)
  }

  private async run(raceIndex: number, speed: string, generation: number) {
    const [resultGap, sessionGap] = SPEEDS[speed]
    const race = this.data.live[raceIndex]
    const base = { running: true, race: race.race, round: race.round, speed, data: 'real' as const, total_sessions: race.sessions.length, warning: null }
    const alive = () => generation === this.generation && !this.stopRequested
    try {
      while (alive() && this.flat[this.progress]?.race === raceIndex) {
        const { session: index } = this.flat[this.progress]
        const session = race.sessions[index]
        const first = session.ticks[0]
        const status = { ...base, session: session.session, session_name: first.session_name, kind: first.kind, session_index: index, field: session.field }
        let sent = session.ticks.findIndex((t) => t.id === this.flat[this.progress].tick.id)
        if (sent === 0) {
          this.setSim({ ...status, phase: 'starting', sent: 0 })
          await sleep(sessionGap * 1000)
        }
        while (alive() && this.flat[this.progress]?.race === raceIndex && this.flat[this.progress].session === index) {
          const tick = this.flat[this.progress].tick
          this.progress++
          sent++
          this.persist()
          this.lastLiveAt = Date.now()
          this.emit({ type: 'tick', tick })
          this.setSim({ ...status, phase: 'live', sent })
          // Instant: no yield between results, so React renders each session once, not per tick.
          if (resultGap) await sleep(resultGap * 1000 * (0.6 + Math.random() * 0.8))
        }
      }
    } finally {
      if (generation === this.generation) this.setSim({ running: false, finished: race.race, stopped: this.stopRequested, warning: null })
    }
  }

  private reset() {
    this.stopRequested = true
    this.generation++
    this.progress = 0
    this.season += 1
    this.sim = { running: false }
    this.persist()
    this.emit({ type: 'snapshot', data: this.snapshot() })
  }

  // ---- game -----------------------------------------------------------------
  private game(): GameState {
    return load<GameState>(GAME_KEY, { name: null, seasons: {} })
  }

  private seasonState(g: GameState): Season {
    const key = String(this.season)
    g.seasons[key] ??= { cash: this.data.snapshot.game.starting_cash, holdings: {}, trades: [] }
    return g.seasons[key]
  }

  private requirePlayer(headers: Record<string, string>) {
    const g = this.game()
    if (!g.name || headers.Authorization !== `Bearer ${TOKEN}`) throw new ApiError(401, 'Join the game first')
    return g
  }

  /** The benchmark: the starting cash put into the Pulse Index when the live season began. */
  private marketValue(prices: Record<string, number>) {
    const values = this.data.snapshot.values
    const atStart = Object.values(values).reduce((s, v) => s + v.current_value, 0)
    const now = Object.keys(values).reduce((s, c) => s + (prices[c] ?? values[c].current_value), 0)
    return this.data.snapshot.game.starting_cash * (now / atStart)
  }

  private portfolio(g: GameState) {
    const prices = this.prices()
    const s = this.seasonState(g)
    const start = this.data.snapshot.game.starting_cash
    const holdings = Object.entries(s.holdings)
      .map(([code, h]) => {
        const value = h.units * (prices[code] ?? 0)
        return { driver_code: code, units: h.units, cost: h.cost, value, pnl_pct: h.cost ? (value / h.cost - 1) * 100 : 0 }
      })
      .sort((a, b) => b.value - a.value)
    const value = s.cash + holdings.reduce((sum, h) => sum + h.value, 0)
    const rank = value >= this.marketValue(prices) ? 1 : 2
    return {
      player: { id: 1, name: g.name! }, epoch: this.season, starting_cash: start, cash: s.cash, holdings, value,
      return_pct: (value / start - 1) * 100, rank, players: 2, trades: [...s.trades].reverse().slice(0, 15),
    }
  }

  private leaderboard() {
    const g = this.game()
    const prices = this.prices()
    const start = this.data.snapshot.game.starting_cash
    const rows = [{ id: 0, name: 'The market (Pulse Index)', value: this.marketValue(prices), top_holding: null as string | null }]
    if (g.name) {
      const p = this.portfolio(g)
      rows.push({ id: 1, name: g.name, value: p.value, top_holding: p.holdings[0]?.driver_code ?? null })
    }
    rows.sort((a, b) => b.value - a.value)
    return {
      players: rows.length,
      me: g.name ? rows.findIndex((r) => r.id === 1) + 1 : null,
      starting_cash: start,
      top: rows.map((r, i) => ({ ...r, rank: i + 1, return_pct: (r.value / start - 1) * 100 })),
    }
  }

  private trade(body: { driver?: string; side?: string; amount?: number | null }, headers: Record<string, string>) {
    const g = this.requirePlayer(headers)
    if (this.sim.running || Date.now() - this.lastLiveAt < LIVE_QUIET_MS) throw new ApiError(423, 'Trading is paused while a session is live')
    const code = (body.driver ?? '').toUpperCase()
    const side = body.side
    if (side !== 'buy' && side !== 'sell') throw new ApiError(422, "side must be 'buy' or 'sell'")
    const price = this.prices()[code]
    if (!price) throw new ApiError(404, `Unknown driver ${code}`)
    let amount = body.amount ?? null
    if (amount !== null && !(Number.isFinite(amount) && amount > 0 && amount < 1e12)) throw new ApiError(400, 'Enter a positive amount')

    const s = this.seasonState(g)
    const h = s.holdings[code] ?? { units: 0, cost: 0 }
    let units: number
    if (side === 'buy') {
      if (!this.data.snapshot.roster.drivers[code]?.active) throw new ApiError(400, `${code} is not on the grid anymore; the stock can only be sold.`)
      if (amount === null || amount < MIN_TRADE) throw new ApiError(400, `The minimum trade is $${MIN_TRADE}`)
      if (amount > s.cash + 0.005) throw new ApiError(400, `Not enough cash (you have $${s.cash.toFixed(2)})`)
      amount = Math.min(amount, s.cash)
      units = amount / price
      h.units += units
      h.cost += amount
      s.cash -= amount
    } else {
      if (h.units <= 0) throw new ApiError(400, `You don't own any ${code}`)
      const held = h.units * price
      if (amount === null || amount >= held - 0.01) {
        amount = held
        units = h.units
      } else {
        if (amount < MIN_TRADE) throw new ApiError(400, `The minimum trade is $${MIN_TRADE}`)
        units = amount / price
      }
      h.cost -= h.cost * (units / h.units)
      h.units -= units
      s.cash += amount
    }
    s.cash = Math.round(s.cash * 100) / 100
    if (h.units <= 1e-12) delete s.holdings[code]
    else s.holdings[code] = h
    s.trades.push({ driver_code: code, side, amount: Math.round(amount * 100) / 100, price, ts: Date.now() / 1000 })
    save(GAME_KEY, g)
    return this.portfolio(g)
  }

  // ---- the "HTTP" API ---------------------------------------------------------
  async request(method: string, path: string, body: unknown, headers: Record<string, string>): Promise<unknown> {
    await this.ready
    const b = (body ?? {}) as Record<string, unknown>
    switch (`${method} ${path}`) {
      case 'POST /api/simulate':
        this.start(String(b.speed ?? 'fast'))
        return { ok: true }
      case 'POST /api/simulate/stop':
        this.stopRequested = true
        return { ok: true }
      case 'POST /api/reset':
        this.reset()
        return { ok: true }
      case 'POST /api/game/join': {
        const name = String(b.name ?? '').split(/\s+/).filter(Boolean).join(' ')
        if (!NAME_RE.test(name)) throw new ApiError(400, 'Pick a name of 3-20 letters, numbers, spaces, dots, dashes or underscores.')
        if (name.toLowerCase().startsWith('the market')) throw new ApiError(409, 'That name is taken by the market.')
        const g: GameState = { ...this.game(), name }
        save(GAME_KEY, g)
        return { token: TOKEN, portfolio: this.portfolio(g) }
      }
      case 'GET /api/game/me':
        return this.portfolio(this.requirePlayer(headers))
      case 'POST /api/game/trade':
        return this.trade(b, headers)
      case 'GET /api/game/leaderboard':
        return this.leaderboard()
    }
    throw new ApiError(404, `Not found: ${path}`)
  }
}

let server: LocalServer | null = null

export function localServer(): LocalServer {
  server ??= new LocalServer()
  return server
}
