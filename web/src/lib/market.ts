import type { DriverMeta, Range, Snapshot, Tick } from './types'

export interface Point {
  time: number
  value: number
}

export interface DriverStats {
  points: number
  wins: number
  podiums: number
  poles: number
  dnfs: number
  starts: number
  avgFinish: number | null
  bestFinish: number | null
  beatRate: number | null
}

export interface DriverView extends DriverMeta {
  teamName: string
  color: string
  baseline: number
  value: number
  change: number
  seasonChange: number
  history: Point[]
  ticks: Tick[]
  lastTick: Tick | null
  stats: DriverStats
  valueRank: number
  pointsRank: number
  /** Championship rank better than market rank => positive (undervalued). */
  gap: number
}

export interface MarketView {
  drivers: DriverView[]
  byCode: Record<string, DriverView>
  index: { series: Point[]; value: number; change: number }
  marketCap: number
  latest: { round: number; session: string; race: string; sessionName: string } | null
  roundsPriced: Set<number>
}

const INDEX_BASE = 1000

/** Strictly increasing times, as the chart library requires. */
function monotonic(points: Point[]): Point[] {
  const sorted = [...points].sort((a, b) => a.time - b.time)
  const out: Point[] = []
  for (const p of sorted) {
    if (out.length && out[out.length - 1].time === p.time) out[out.length - 1] = p
    else out.push(p)
  }
  return out
}

export function buildMarket(snapshot: Snapshot, ticks: Tick[], range: Range): MarketView {
  const { roster, values } = snapshot
  const codes = Object.keys(values)
  const baseline: Record<string, number> = {}
  const current: Record<string, number> = {}
  for (const code of codes) {
    baseline[code] = values[code].baseline_value
    current[code] = values[code].baseline_value
  }

  const last = ticks[ticks.length - 1]
  const latest = last
    ? { round: last.round, session: last.session, race: last.race, sessionName: last.session_name }
    : null

  const perDriver: Record<string, Tick[]> = Object.fromEntries(codes.map((c) => [c, []]))
  const reference: Record<string, number> = { ...baseline }
  const refSet = new Set<string>()
  const indexPoints: Point[] = []
  const baseSum = codes.reduce((s, c) => s + baseline[c], 0) || 1
  let sum = baseSum
  const roundsPriced = new Set<number>()

  const firstTs = ticks.length ? ticks[0].ts : 0
  if (ticks.length) indexPoints.push({ time: firstTs - 86400, value: INDEX_BASE })

  for (const t of ticks) {
    if (!(t.driver_code in current)) continue
    roundsPriced.add(t.round)
    perDriver[t.driver_code].push(t)
    const inWindow =
      range === 'weekend'
        ? latest && t.round === latest.round
        : range === 'session'
          ? latest && t.round === latest.round && t.session === latest.session
          : false
    if (inWindow && !refSet.has(t.driver_code)) {
      reference[t.driver_code] = t.value_before
      refSet.add(t.driver_code)
    }
    sum += t.value_after - current[t.driver_code]
    current[t.driver_code] = t.value_after
    indexPoints.push({ time: t.ts, value: (sum / baseSum) * INDEX_BASE })
  }

  // Drivers without a tick in the window haven't moved within it.
  if (range !== 'season') {
    for (const code of codes) if (!refSet.has(code)) reference[code] = current[code]
  }

  const drivers: DriverView[] = codes.map((code) => {
    const meta = roster.drivers[code] ?? {
      code, name: values[code].driver_name, number: 0, country: '', team: values[code].team, active: true,
    }
    const team = roster.teams[meta.team] ?? { name: meta.team, color: '#888888' }
    const mine = perDriver[code]
    const history = monotonic([
      ...(ticks.length ? [{ time: firstTs - 86400, value: baseline[code] }] : []),
      ...mine.map((t) => ({ time: t.ts, value: t.value_after })),
    ])
    return {
      ...meta,
      teamName: team.name,
      color: team.color,
      baseline: baseline[code],
      value: current[code],
      change: reference[code] ? (current[code] / reference[code] - 1) * 100 : 0,
      seasonChange: (current[code] / baseline[code] - 1) * 100,
      history,
      ticks: mine,
      lastTick: mine[mine.length - 1] ?? null,
      stats: statsFor(mine),
      valueRank: 0,
      pointsRank: 0,
      gap: 0,
    }
  })

  const byValue = [...drivers].sort((a, b) => b.value - a.value)
  byValue.forEach((d, i) => (d.valueRank = i + 1))
  const byPoints = [...drivers].sort((a, b) => b.stats.points - a.stats.points || b.stats.wins - a.stats.wins)
  byPoints.forEach((d, i) => (d.pointsRank = i + 1))
  for (const d of drivers) d.gap = d.valueRank - d.pointsRank

  const refSum = codes.reduce((s, c) => s + reference[c], 0) || 1
  return {
    drivers: byValue,
    byCode: Object.fromEntries(drivers.map((d) => [d.code, d])),
    index: {
      series: monotonic(indexPoints),
      value: (sum / baseSum) * INDEX_BASE,
      change: (sum / refSum - 1) * 100,
    },
    marketCap: sum,
    latest,
    roundsPriced,
  }
}

function statsFor(ticks: Tick[]): DriverStats {
  let points = 0, wins = 0, podiums = 0, poles = 0, dnfs = 0, starts = 0, beat = 0, graded = 0
  const finishes: number[] = []
  for (const t of ticks) {
    if (t.kind === 'race' || t.kind === 'sprint') {
      points += t.points
      if (t.position == null) dnfs++
    }
    if (t.kind === 'race') {
      starts++
      if (t.position != null) {
        finishes.push(t.position)
        if (t.position === 1) wins++
        if (t.position <= 3) podiums++
      }
    }
    if (t.kind === 'qualifying' && t.position === 1) poles++
    if (t.kind !== 'practice' && t.position != null) {
      graded++
      if (t.position < t.expected) beat++
    }
  }
  return {
    points, wins, podiums, poles, dnfs, starts,
    avgFinish: finishes.length ? finishes.reduce((a, b) => a + b, 0) / finishes.length : null,
    bestFinish: finishes.length ? Math.min(...finishes) : null,
    beatRate: graded ? beat / graded : null,
  }
}

export function sessionTicks(ticks: Tick[], round: number, session: string): Tick[] {
  return ticks.filter((t) => t.round === round && t.session === session)
}
