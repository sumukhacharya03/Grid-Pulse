import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import DriverPanel from './components/DriverPanel'
import Feed from './components/Feed'
import Header, { Logo } from './components/Header'
import IndexHero from './components/IndexHero'
import Leaderboard from './components/Leaderboard'
import MarketBoard from './components/MarketBoard'
import Portfolio from './components/Portfolio'
import RaceControl from './components/RaceControl'
import StatTiles from './components/StatTiles'
import TeamHeatmap from './components/TeamHeatmap'
import TickerTape from './components/TickerTape'
import TradeBox from './components/TradeBox'
import UnderTheHood from './components/UnderTheHood'
import { arrow } from './lib/format'
import { LIVE_QUIET_MS, useGame } from './lib/game'
import { useNow } from './lib/hooks'
import { buildMarket } from './lib/market'
import type { Range } from './lib/types'
import { useMarket } from './lib/useMarket'

interface Toast {
  id: number
  message: string
}

export default function App() {
  const { connection, snapshot, ticks, flashes, lastLiveAt, gameEvents } = useMarket()
  const [range, setRange] = useState<Range>('season')
  const [selected, setSelected] = useState<string | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])

  const market = useMemo(() => (snapshot ? buildMarket(snapshot, ticks, range) : null), [snapshot, ticks, range])
  const liveTicks = useMemo(() => ticks.filter((t) => t.live).length, [ticks])

  const toast = useCallback((message: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, message }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }, [])

  // The tab title doubles as a mini ticker.
  useEffect(() => {
    if (!market || !market.drivers.length) return
    document.title = `${arrow(market.index.change)} ${market.index.value.toFixed(1)} · Grid-Pulse`
  }, [market])

  const select = useCallback((code: string) => setSelected(code), [])
  const close = useCallback(() => setSelected(null), [])

  const ready = snapshot?.ready && market
  const empty = ready && market.drivers.length === 0
  const round = market?.latest?.round ?? 0
  const sim = snapshot?.sim ?? { running: false }

  const game = useGame(snapshot?.ready ? snapshot.epoch : null, gameEvents, !!sim.running)
  const now = useNow(1000).getTime()
  const marketOpen = !sim.running && now - lastLiveAt > LIVE_QUIET_MS
  const owned = useMemo(() => new Set(game.portfolio?.holdings.map((h) => h.driver_code) ?? []), [game.portfolio])
  const goJoin = useCallback(() => {
    setSelected(null)
    requestAnimationFrame(() => {
      document.getElementById('portfolio')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      document.getElementById('player-name')?.focus({ preventScroll: true })
    })
  }, [])

  return (
    <MotionConfig reducedMotion="user">
      <div className="backdrop" aria-hidden="true" />
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-ink focus:px-3 focus:py-2 focus:text-bg">
        Skip to market
      </a>
      <Header
        connection={connection}
        mode={snapshot?.mode ?? null}
        data={snapshot?.data ?? null}
        live={!!sim.running}
        round={round}
        totalRounds={snapshot?.calendar.length || 24}
        raceName={market?.latest?.race ?? null}
      />

      {connection === 'reconnecting' && snapshot && (
        <div role="status" className="border-b border-gold/20 bg-gold/10 px-4 py-2 text-center text-sm text-gold">
          Connection to the market lost. Reconnecting…
        </div>
      )}

      {ready && !empty && <TickerTape drivers={market.drivers} onSelect={select} />}

      <main id="main" className="mx-auto max-w-[1600px] space-y-4 px-4 py-5 sm:px-6">
        {!ready ? (
          <Loading kafka={snapshot?.mode === 'kafka'} />
        ) : empty ? (
          <EmptyMarket />
        ) : (
          <>
            <div className="grid gap-4 lg:grid-cols-12">
              <div className="flex lg:col-span-8">
                <IndexHero market={market} calendar={snapshot.calendar} range={range} onRange={setRange} />
              </div>
              <div className="flex lg:col-span-4 [&>section]:w-full">
                <RaceControl
                  mode={snapshot.mode}
                  data={snapshot.data}
                  isPublic={snapshot.public}
                  sim={sim}
                  nextRace={snapshot.next_race}
                  calendar={snapshot.calendar}
                  market={market}
                  ticks={ticks}
                  onSelect={select}
                  onError={toast}
                />
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-12">
              <div className="min-w-0 lg:col-span-8">
                <Portfolio game={game} market={market} marketOpen={marketOpen} startingCash={snapshot.game.starting_cash} onSelect={select} onError={toast} />
              </div>
              <div className="min-w-0 lg:col-span-4">
                <Leaderboard game={game} market={market} />
              </div>
            </div>

            <StatTiles market={market} onSelect={select} />

            <div className="grid items-start gap-4 lg:grid-cols-12">
              <div className="min-w-0 lg:col-span-8">
                <MarketBoard market={market} teams={snapshot.roster.teams} flashes={flashes} owned={owned} onSelect={select} />
              </div>
              <div className="min-w-0 self-stretch lg:col-span-4">
                <Feed ticks={ticks} market={market} onSelect={select} />
              </div>
            </div>

            <TeamHeatmap market={market} teams={snapshot.roster.teams} range={range} onSelect={select} />
            <UnderTheHood mode={snapshot.mode} data={snapshot.data} ticks={ticks.length} liveTicks={liveTicks} />
          </>
        )}
      </main>

      <footer className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 pb-8 pt-2 text-xs text-faint sm:px-6">
        <span>
          Grid-Pulse · {snapshot?.data === 'simulated' ? 'simulated 2025 season' : 'real 2025 results via FastF1'} · pretend money only · not affiliated with Formula 1
        </span>
        <span>
          Charts by{' '}
          <a className="underline decoration-white/20 underline-offset-2 hover:text-ink" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
            TradingView Lightweight Charts™
          </a>
        </span>
      </footer>

      {market && (
        <DriverPanel
          code={selected}
          market={market}
          order={market.drivers.map((d) => d.code)}
          onClose={close}
          onSelect={select}
          trade={(d) => <TradeBox driver={d} game={game} marketOpen={marketOpen} onError={toast} onJoin={goJoin} />}
        />
      )}

      <div className="fixed bottom-4 left-1/2 z-[70] flex w-[min(92vw,420px)] -translate-x-1/2 flex-col gap-2" aria-live="assertive">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              role="alert"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="rounded-xl border border-down/30 bg-[#1a0d11]/95 px-4 py-3 text-sm text-ink shadow-2xl backdrop-blur"
            >
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </MotionConfig>
  )
}

function Loading({ kafka }: { kafka: boolean }) {
  return (
    <div aria-busy="true" aria-label="Loading market">
      <p className="mb-4 text-sm text-faint">{kafka ? 'Replaying the market from Kafka…' : 'Opening the market…'}</p>
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="skeleton h-[430px] lg:col-span-8" />
        <div className="skeleton h-[430px] lg:col-span-4" />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton h-[86px]" />)}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 2xl:grid-cols-3 lg:w-2/3">
        {Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton h-[180px]" />)}
      </div>
    </div>
  )
}

function EmptyMarket() {
  return (
    <div className="panel mx-auto mt-10 max-w-xl p-8 text-center">
      <div className="flex justify-center"><Logo /></div>
      <h1 className="mt-6 text-2xl font-bold">No market yet</h1>
      <p className="mt-2 text-sm text-dim">
        Kafka is connected but no market has been published. Build it once with the batch pipeline and this page updates by itself:
      </p>
      <pre className="num mt-4 overflow-x-auto rounded-xl border border-line bg-black/40 p-4 text-left text-xs leading-relaxed text-dim">
{`python baseline_market_value/producer1.py
python generator/historical/producer2.py
python calculation_service.py`}
      </pre>
      <p className="mt-3 text-xs text-faint">Or run <code className="num">python dashboard.py --mode demo</code> to explore without Kafka.</p>
    </div>
  )
}
