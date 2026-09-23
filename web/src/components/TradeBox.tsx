import { useState } from 'react'
import { liveValue, type GameApi } from '../lib/game'
import { money } from '../lib/format'
import type { DriverView } from '../lib/market'
import { Change } from './ui'

interface Props {
  driver: DriverView
  game: GameApi
  marketOpen: boolean
  onError: (message: string) => void
  onJoin: () => void
}

const CHIPS = [0.1, 0.25, 0.5, 1]

export default function TradeBox({ driver: d, game, marketOpen, onError, onJoin }: Props) {
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  const p = game.portfolio

  if (!game.joined || !p) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gold/25 bg-gold/[0.06] p-4">
        <p className="text-sm text-dim">Think {d.code} will beat the market? Join the game to back them.</p>
        <button onClick={onJoin} className="rounded-lg bg-gold px-4 py-2 text-sm font-black uppercase italic tracking-wider text-bg">Play</button>
      </div>
    )
  }

  const holding = p.holdings.find((h) => h.driver_code === d.code)
  const owned = holding ? liveValue(holding, { [d.code]: d.value }) : 0
  const pnl = holding?.cost ? (owned / holding.cost - 1) * 100 : 0
  const value = Number(amount)
  const valid = Number.isFinite(value) && value > 0

  const run = async (side: 'buy' | 'sell', dollars: number | null) => {
    setBusy(true)
    setDone(null)
    try {
      await game.trade(d.code, side, dollars)
      setDone(side === 'buy' ? `Bought ${money(dollars ?? 0)} of ${d.code}` : `Sold ${dollars ? money(dollars) : 'all'} of ${d.code}`)
      setAmount('')
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const disabled = busy || !marketOpen

  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="eyebrow">Trade {d.code}</h3>
        <span className="text-xs text-faint">Cash <span className="num text-dim">{money(p.cash)}</span></span>
      </div>
      {holding && (
        <p className="mt-2 flex items-center gap-2 text-sm">
          You own <span className="num font-semibold">{money(owned)}</span> <Change value={pnl} className="text-xs" />
        </p>
      )}

      {!marketOpen && (
        <p className="mt-3 rounded-lg bg-[#ff2d3d]/10 px-3 py-2 text-sm text-[#ff7a82]">
          Trading is paused while a session is live. It reopens as soon as the results stop.
        </p>
      )}

      <form
        className="mt-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (valid) run('buy', value)
        }}
      >
        <label htmlFor="trade-amount" className="sr-only">Amount in dollars</label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <span className="num pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint">$</span>
            <input
              id="trade-amount"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ''))}
              placeholder="Amount"
              className="num h-11 w-full rounded-xl border border-line bg-black/30 pl-7 pr-3 text-sm placeholder:text-faint focus:border-line-strong focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={disabled || !valid || !d.active}
            className="h-11 rounded-xl bg-up px-5 text-sm font-black uppercase tracking-wider text-bg disabled:opacity-40"
            title={d.active ? undefined : 'Benched drivers can only be sold'}
          >
            Buy
          </button>
          <button
            type="button"
            onClick={() => valid && run('sell', value)}
            disabled={disabled || !valid || !holding}
            className="h-11 rounded-xl bg-down px-5 text-sm font-black uppercase tracking-wider text-bg disabled:opacity-40"
          >
            Sell
          </button>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {CHIPS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setAmount((Math.floor(p.cash * f * 100) / 100).toFixed(2))}
              disabled={p.cash < 100}
              className="rounded-md border border-line px-2 py-0.5 text-xs text-dim hover:border-line-strong hover:text-ink disabled:opacity-40"
            >
              {f === 1 ? 'All cash' : `${f * 100}%`}
            </button>
          ))}
          {holding && (
            <button type="button" onClick={() => run('sell', null)} disabled={disabled} className="ml-auto rounded-md border border-down/30 px-2 py-0.5 text-xs text-down hover:bg-down/10 disabled:opacity-40">
              Sell all
            </button>
          )}
        </div>
      </form>
      {done && <p role="status" className="mt-2 text-xs text-up">{done}</p>}
    </div>
  )
}
