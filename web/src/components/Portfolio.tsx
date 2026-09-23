import { useMemo, useState, type FormEvent } from 'react'
import { liveValue, type GameApi } from '../lib/game'
import { money } from '../lib/format'
import { useTweened } from '../lib/hooks'
import type { MarketView } from '../lib/market'
import { Avatar, Change } from './ui'

interface Props {
  game: GameApi
  market: MarketView
  marketOpen: boolean
  startingCash: number
  onSelect: (code: string) => void
  onError: (message: string) => void
}

export function MarketStatus({ open }: { open: boolean }) {
  return (
    <span className={`flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-widest ${open ? 'bg-up/10 text-up' : 'bg-[#ff2d3d]/10 text-[#ff5a66]'}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${open ? 'bg-up' : 'bg-[#ff2d3d]'}`} aria-hidden="true" />
      {open ? 'Trading open' : 'Trading paused'}
    </span>
  )
}

export default function Portfolio({ game, market, marketOpen, startingCash, onSelect, onError }: Props) {
  return (
    <section id="portfolio" className="panel h-full p-5" aria-labelledby="portfolio-title">
      <div className="flex items-center justify-between gap-3">
        <h2 id="portfolio-title" className="text-xl font-black uppercase italic tracking-tight">
          {game.joined ? 'Your portfolio' : 'Play the market'}
        </h2>
        <MarketStatus open={marketOpen} />
      </div>
      {game.joined && game.portfolio ? (
        <Holdings game={game} market={market} onSelect={onSelect} />
      ) : (
        <Join game={game} startingCash={startingCash} onError={onError} />
      )}
    </section>
  )
}

function Join({ game, startingCash, onError }: { game: GameApi; startingCash: number; onError: (m: string) => void }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      await game.join(name)
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3 grid gap-5 md:grid-cols-[1fr_auto] md:items-end">
      <div>
        <p className="max-w-lg text-dim">
          Start with <span className="num font-semibold text-ink">${startingCash.toLocaleString()}</span> of pretend money.
          Back drivers before a weekend, watch your picks move live, and climb the leaderboard.
        </p>
        <ol className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-faint">
          <li><span className="num text-gold">1</span> Pick a name</li>
          <li><span className="num text-gold">2</span> Open a driver and buy</li>
          <li><span className="num text-gold">3</span> Hit Go live</li>
        </ol>
      </div>
      <form onSubmit={submit} className="flex w-full gap-2 md:w-auto">
        <label htmlFor="player-name" className="sr-only">Player name</label>
        <input
          id="player-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={20}
          minLength={3}
          required
          autoComplete="nickname"
          placeholder="Your name"
          className="h-11 min-w-0 flex-1 rounded-xl border border-line bg-black/30 px-3.5 text-sm placeholder:text-faint focus:border-line-strong focus:outline-none md:w-52"
        />
        <button
          type="submit"
          disabled={busy || name.trim().length < 3}
          className="h-11 shrink-0 rounded-xl bg-gold px-5 text-sm font-black uppercase italic tracking-wider text-bg transition-transform hover:scale-[1.03] disabled:opacity-50 disabled:hover:scale-100"
        >
          Join
        </button>
      </form>
      <p className="text-xs text-faint md:col-span-2">No sign-up: your account is saved in this browser.</p>
    </div>
  )
}

function Holdings({ game, market, onSelect }: { game: GameApi; market: MarketView; onSelect: (c: string) => void }) {
  const p = game.portfolio!
  const prices = useMemo(() => Object.fromEntries(market.drivers.map((d) => [d.code, d.value])), [market.drivers])
  const holdings = useMemo(
    () => p.holdings.map((h) => ({ ...h, live: liveValue(h, prices) })).sort((a, b) => b.live - a.live),
    [p.holdings, prices],
  )
  const invested = holdings.reduce((s, h) => s + h.live, 0)
  const total = p.cash + invested
  const shown = useTweened(total)
  const ret = (total / p.starting_cash - 1) * 100

  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div>
          <div className="text-sm text-dim">{p.player.name}</div>
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="num text-4xl font-semibold tracking-tight">
              ${shown.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <Change value={ret} badge className="text-sm" />
          </div>
        </div>
        <dl className="flex gap-6 text-sm">
          <div><dt className="text-xs text-faint">Rank</dt><dd className="num font-semibold">{p.rank ? `#${p.rank}` : '—'}<span className="text-faint"> / {p.players}</span></dd></div>
          <div><dt className="text-xs text-faint">Cash</dt><dd className="num font-semibold">{money(p.cash)}</dd></div>
          <div><dt className="text-xs text-faint">Invested</dt><dd className="num font-semibold">{money(invested)}</dd></div>
        </dl>
      </div>

      {/* Allocation bar */}
      <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-white/5" role="img" aria-label="Portfolio allocation">
        {holdings.map((h) => (
          <span key={h.driver_code} style={{ width: `${(h.live / total) * 100}%`, background: market.byCode[h.driver_code]?.color }} title={`${h.driver_code} ${money(h.live)}`} />
        ))}
      </div>

      {holdings.length === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-line-strong px-4 py-5 text-center text-sm text-dim">
          No drivers yet. Open any driver and hit <span className="font-bold text-ink">Buy</span>, then <span className="font-bold text-ink">Go live</span>.
        </p>
      ) : (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {holdings.map((h) => {
            const d = market.byCode[h.driver_code]
            const pnl = h.cost ? (h.live / h.cost - 1) * 100 : 0
            return (
              <li key={h.driver_code}>
                <button onClick={() => onSelect(h.driver_code)} className="flex w-full items-center gap-3 rounded-xl border border-line bg-black/20 p-2.5 text-left transition-colors hover:border-line-strong">
                  {d && <Avatar code={d.code} color={d.color} size={36} className="rounded-lg" />}
                  <span className="min-w-0 flex-1">
                    <span className="block font-bold">{h.driver_code}</span>
                    <span className="num block text-xs text-faint">cost {money(h.cost)}</span>
                  </span>
                  <span className="text-right">
                    <span className="num block text-sm font-semibold">{money(h.live)}</span>
                    <Change value={pnl} className="text-xs" />
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
      <button
        onClick={() => {
          if (confirm(`Sign out ${p.player.name}? The account only lives in this browser, so it can't be recovered.`)) game.leave()
        }}
        className="mt-3 text-xs text-faint underline decoration-white/20 underline-offset-2 hover:text-dim">
        Not {p.player.name}? Sign out of this browser
      </button>
    </div>
  )
}
