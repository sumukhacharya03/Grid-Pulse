import { AnimatePresence, motion } from 'motion/react'
import { useMemo, useState, type ReactNode } from 'react'
import { sessionShort, shortDate } from '../lib/format'
import { useNow } from '../lib/hooks'
import type { DriverView, MarketView } from '../lib/market'
import type { DataSource, Mode, Race, SimStatus, Tick } from '../lib/types'
import { api } from '../lib/useMarket'
import { Avatar, Change, Segmented } from './ui'

type Speed = 'normal' | 'fast' | 'instant'

interface Props {
  mode: Mode
  data: DataSource
  isPublic: boolean
  sim: SimStatus
  nextRace: string | null
  calendar: Race[]
  market: MarketView
  ticks: Tick[]
  onSelect: (code: string) => void
  onError: (message: string) => void
}

export default function RaceControl({ mode, data, isPublic, sim, nextRace, calendar, market, ticks, onSelect, onError }: Props) {
  const [speed, setSpeed] = useState<Speed>('fast')
  const now = useNow(1000).getTime() / 1000
  const cooldown = Math.max(0, Math.ceil((sim.cooldown_until ?? 0) - now))
  const [pending, setPending] = useState(false)
  const race = calendar.find((r) => r.name === (sim.running ? sim.race : nextRace))

  const call = async (path: string, body?: unknown) => {
    setPending(true)
    try {
      await api(path, body)
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="panel flex flex-col overflow-hidden" aria-labelledby="race-control-title">
      {race && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-6 -top-10 select-none text-[9rem] font-black italic leading-none text-white/[0.035]"
        >
          {String(race.round).padStart(2, '0')}
        </div>
      )}
      <div className="flex items-center justify-between px-5 pt-5">
        <h2 id="race-control-title" className="eyebrow flex items-center gap-2">
          {sim.running ? (
            <>
              <span className="h-2 w-2 animate-live rounded-full bg-[#ff2d3d]" aria-hidden="true" />
              <span className="text-[#ff5a66]">Live · Race control</span>
            </>
          ) : (
            'Race control'
          )}
        </h2>
        {race && <span className="num text-xs text-faint">Round {race.round}/24</span>}
      </div>

      {sim.running && race ? (
        <LiveView sim={sim} race={race} market={market} ticks={ticks} onSelect={onSelect} onStop={isPublic ? undefined : () => call('/api/simulate/stop')} pending={pending} />
      ) : (
        <div className="flex flex-1 flex-col px-5 pb-5">
          {sim.finished && <Recap raceName={sim.finished} stopped={!!sim.stopped} ticks={ticks} market={market} calendar={calendar} onSelect={onSelect} />}
          {sim.warning && !sim.running && <p className="mt-3 rounded-lg bg-gold/10 px-3 py-2 text-sm text-gold">{sim.warning}</p>}

          {race ? (
            <>
              <div className="mt-4">
                <div className="eyebrow text-faint">Next up</div>
                <h3 className="mt-1 text-2xl font-bold leading-tight">{race.name}</h3>
                <p className="mt-1 text-sm text-dim">
                  {race.circuit} · {shortDate(race.dates[0])} – {shortDate(race.dates[2])}
                  {race.sprint && <span className="ml-2 rounded bg-gold/15 px-1.5 py-0.5 text-[0.65rem] font-bold uppercase tracking-widest text-gold">Sprint</span>}
                </p>
              </div>
              <ol className="mt-4 flex flex-wrap gap-1.5" aria-label="Sessions this weekend">
                {race.sessions.map((s) => (
                  <li key={s.key} className="rounded-md border border-line bg-black/20 px-2 py-1 text-[0.7rem] font-bold tracking-wider text-dim">
                    {sessionShort(s.key)}
                  </li>
                ))}
              </ol>

              <Expectation market={market} onSelect={onSelect} />
              <UpNext calendar={calendar} after={race.round} />

              <div className="mt-auto pt-6">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <span className="text-xs text-faint">Replay speed</span>
                  <Segmented
                    label="Replay speed"
                    value={speed}
                    onChange={setSpeed}
                    options={[
                      { value: 'normal' as Speed, label: 'Real', title: 'About a second per result' },
                      { value: 'fast' as Speed, label: 'Fast', title: 'A few results per second' },
                      ...(isPublic ? [] : [{ value: 'instant' as Speed, label: 'Instant', title: 'Price the whole weekend at once' }]),
                    ]}
                  />
                </div>
                <button
                  onClick={() => call('/api/simulate', { race: race.name, speed })}
                  disabled={pending || cooldown > 0}
                  className="group relative flex h-14 w-full items-center justify-center gap-3 overflow-hidden rounded-xl bg-gradient-to-r from-[#e10600] to-[#ff3b2f] text-base font-black uppercase italic tracking-wider text-white shadow-[0_10px_30px_-10px_rgb(225_6_0/0.8)] transition-transform hover:scale-[1.015] active:scale-[0.99] disabled:opacity-60"
                >
                  <span aria-hidden="true" className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
                  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M7 4.5v15l13-7.5z" /></svg>
                  {cooldown > 0 ? `Trading window · ${cooldown}s` : `Go live · ${race.short}`}
                </button>
                <p className="mt-2 text-center text-xs text-faint">
                  {cooldown > 0
                    ? 'Place your trades before the next weekend starts'
                    : `${data === 'real' ? 'Replays the real 2025 results' : 'Simulates every session'}${
                        mode === 'kafka' ? ' through Kafka (priced by realtime_service.py)' : ', pricing each result as it lands'
                      }`}
                </p>
              </div>
            </>
          ) : (
            <div className="mt-6 flex flex-1 flex-col items-center justify-center text-center">
              <div className="text-4xl" aria-hidden="true">🏁</div>
              <h3 className="mt-2 text-xl font-bold">Season complete</h3>
              <p className="mt-1 max-w-xs text-sm text-dim">All 24 rounds are priced in.</p>
              {mode !== 'kafka' ? (
                <button onClick={() => call('/api/reset')} disabled={pending} className="mt-4 rounded-lg border border-line-strong px-4 py-2 text-sm font-semibold hover:bg-white/5">
                  Reset to mid-season
                </button>
              ) : (
                <p className="mt-3 text-xs text-faint">Re-run calculation_service.py to reset the market.</p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}

/** What the market is pricing in: its expected finishing order is simply the value ranking. */
function Expectation({ market, onSelect }: { market: MarketView; onSelect: (c: string) => void }) {
  const top = market.drivers.filter((d) => d.active).slice(0, 5)
  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <span className="eyebrow text-faint">Market expects</span>
        <span className="text-[0.68rem] text-faint">beat it and the stock rises</span>
      </div>
      <ol className="mt-2 grid grid-cols-5 gap-1.5">
        {top.map((d, i) => (
          <li key={d.code}>
            <button
              onClick={() => onSelect(d.code)}
              className="flex w-full flex-col items-center gap-1 rounded-lg border border-line bg-black/20 py-2 transition-colors hover:border-line-strong"
              title={`${d.name}: expected P${i + 1}`}
            >
              <span className="num text-[0.65rem] text-faint">P{i + 1}</span>
              <Avatar code={d.code} color={d.color} size={34} className="rounded-lg" />
              <span className="text-xs font-bold">{d.code}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  )
}

function UpNext({ calendar, after }: { calendar: Race[]; after: number }) {
  const upcoming = calendar.filter((r) => r.round > after).slice(0, 3)
  if (!upcoming.length) return null
  return (
    <div className="mt-4">
      <span className="eyebrow text-faint">Then</span>
      <ul className="mt-1.5 space-y-1 text-sm">
        {upcoming.map((r) => (
          <li key={r.round} className="flex items-center gap-2 text-dim">
            <span className="num w-8 text-xs text-faint">R{r.round}</span>
            <span className="truncate">{r.name.replace(' Grand Prix', ' GP')}</span>
            {r.sprint && <span className="rounded bg-gold/10 px-1 text-[0.6rem] font-bold uppercase text-gold">Sprint</span>}
            <span className="num ml-auto text-xs text-faint">{shortDate(r.dates[2])}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function LiveView({ sim, race, market, ticks, onSelect, onStop, pending }: {
  sim: SimStatus; race: Race; market: MarketView; ticks: Tick[]; onSelect: (c: string) => void; onStop?: () => void; pending: boolean
}) {
  const tower = useMemo(
    () =>
      ticks
        .filter((t) => t.round === race.round && t.session === sim.session)
        .sort((a, b) => (a.position ?? 99) - (b.position ?? 99)),
    [ticks, race.round, sim.session],
  )
  const index = sim.session_index ?? 0

  return (
    <div className="flex min-h-0 flex-1 flex-col px-5 pb-5">
      <div className="mt-3">
        <h3 className="text-xl font-bold leading-tight">{race.name}</h3>
        <ol className="mt-3 grid gap-1" style={{ gridTemplateColumns: `repeat(${race.sessions.length}, minmax(0, 1fr))` }} aria-label="Session progress">
          {race.sessions.map((s, i) => (
            <li key={s.key} aria-current={i === index ? 'step' : undefined}>
              <div className={`h-1 rounded-full ${i < index ? 'bg-white/60' : i === index ? 'bg-[#ff2d3d]' : 'bg-white/10'}`} />
              <div className={`mt-1 text-center text-[0.65rem] font-bold tracking-wider ${i === index ? 'text-ink' : 'text-faint'}`}>{sessionShort(s.key)}</div>
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="font-semibold">
          {sim.session_name}
          {sim.phase === 'starting' && <span className="ml-2 animate-pulse text-dim">lights out…</span>}
        </span>
        <span className="num text-xs text-dim">{tower.length}/{sim.field ?? 20} classified</span>
      </div>

      <ol className="scrollbar-thin mt-2 max-h-[20rem] min-h-[12rem] flex-1 overflow-y-auto rounded-lg border border-line bg-black/25" aria-label={`${sim.session_name} classification`} aria-live="polite">
        <AnimatePresence initial={false}>
          {tower.map((t) => {
            const d: DriverView | undefined = market.byCode[t.driver_code]
            return (
              <motion.li
                key={t.id}
                layout
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                <button onClick={() => onSelect(t.driver_code)} className="flex w-full items-center gap-2.5 border-b border-line px-3 py-1.5 text-left text-sm last:border-0 hover:bg-white/5">
                  <span className="num w-7 text-right text-xs text-faint">{t.position ? `P${t.position}` : 'DNF'}</span>
                  <span className="h-4 w-[3px] rounded-full" style={{ background: d?.color }} aria-hidden="true" />
                  <span className="w-10 font-bold">{t.driver_code}</span>
                  <span className="min-w-0 flex-1 truncate text-xs text-faint">{t.moves[0]?.label ?? 'As expected'}</span>
                  <Change value={t.change_pct} className="text-xs" />
                </button>
              </motion.li>
            )
          })}
        </AnimatePresence>
        {!tower.length && <li className="px-3 py-6 text-center text-sm text-faint">Waiting for the first classification…</li>}
      </ol>

      {sim.warning && <p className="mt-3 rounded-lg bg-gold/10 px-3 py-2 text-sm text-gold">{sim.warning}</p>}
      {onStop ? (
        <button onClick={onStop} disabled={pending} className="mt-4 h-11 rounded-xl border border-line-strong text-sm font-bold uppercase tracking-wider text-dim transition-colors hover:bg-white/5 hover:text-ink">
          Stop weekend
        </button>
      ) : (
        <p className="mt-4 text-center text-xs text-faint">Trading reopens when the weekend ends</p>
      )}
    </div>
  )
}

function Recap({ raceName, stopped, ticks, market, calendar, onSelect }: {
  raceName: string; stopped: boolean; ticks: Tick[]; market: MarketView; calendar: Race[]; onSelect: (c: string) => void
}) {
  const recap = useMemo(() => {
    const round = calendar.find((r) => r.name === raceName)?.round
    const mine = ticks.filter((t) => t.round === round)
    const winner = mine.find((t) => t.kind === 'race' && t.position === 1)
    const first: Record<string, number> = {}
    const last: Record<string, number> = {}
    for (const t of mine) {
      first[t.driver_code] ??= t.value_before
      last[t.driver_code] = t.value_after
    }
    const moves = Object.keys(first).map((c) => ({ code: c, change: (last[c] / first[c] - 1) * 100}))
    moves.sort((a, b) => b.change - a.change)
    return { winner, best: moves[0], worst: moves[moves.length - 1] }
  }, [raceName, ticks, calendar])

  if (!recap.best) return null
  const rows = [
    recap.winner && { label: 'Winner', code: recap.winner.driver_code, value: <span className="text-gold">P1</span> },
    { label: 'Top gainer', code: recap.best.code, value: <Change value={recap.best.change} /> },
    { label: 'Biggest drop', code: recap.worst.code, value: <Change value={recap.worst.change} /> },
  ].filter(Boolean) as { label: string; code: string; value: ReactNode }[]

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-xl border border-line bg-gradient-to-br from-white/[0.05] to-transparent p-4">
      <div className="eyebrow text-faint">{stopped ? 'Stopped early' : 'Weekend complete'} · {raceName}</div>
      <ul className="mt-2 space-y-1.5">
        {rows.map((r) => (
          <li key={r.label}>
            <button onClick={() => onSelect(r.code)} className="flex w-full items-center justify-between gap-3 rounded-md px-1 py-0.5 text-sm hover:bg-white/5">
              <span className="text-dim">{r.label}</span>
              <span className="flex items-center gap-2">
                <span className="h-3 w-[3px] rounded-full" style={{ background: market.byCode[r.code]?.color }} aria-hidden="true" />
                <span className="font-bold">{market.byCode[r.code]?.name ?? r.code}</span>
                {r.value}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}
