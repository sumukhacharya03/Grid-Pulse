import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useRef, type ReactNode } from 'react'
import { driverImg, money, ordinal, pct, sessionShort, withAlpha } from '../lib/format'
import { useTweened } from '../lib/hooks'
import type { DriverView, MarketView } from '../lib/market'
import type { Tick } from '../lib/types'
import PriceChart, { type ChartMarker } from './PriceChart'
import { Change } from './ui'

interface Props {
  code: string | null
  market: MarketView
  order: string[]
  onClose: () => void
  onSelect: (code: string) => void
  /** Rendered under the hero: the trading box. */
  trade: (driver: DriverView) => ReactNode
}

export default function DriverPanel({ code, market, order, onClose, onSelect, trade }: Props) {
  const driver = code ? market.byCode[code] : undefined
  return (
    <AnimatePresence>
      {driver && (
        <Panel key="panel" driver={driver} order={order} onClose={onClose} onSelect={onSelect} trade={trade(driver)} />
      )}
    </AnimatePresence>
  )
}

function Panel({ driver: d, order, onClose, onSelect, trade }: {
  driver: DriverView; order: string[]; onClose: () => void; onSelect: (c: string) => void; trade: ReactNode
}) {
  const dialog = useRef<HTMLDivElement>(null)
  const returnFocus = useRef<Element | null>(null)
  const value = useTweened(d.value)

  useEffect(() => {
    returnFocus.current = document.activeElement
    dialog.current?.focus()
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
      ;(returnFocus.current as HTMLElement | null)?.focus?.()
    }
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      const typing = /input|textarea|select/i.test((e.target as HTMLElement).tagName)
      if (!typing && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
        const i = order.indexOf(d.code)
        if (i < 0) return
        const next = order[(i + (e.key === 'ArrowRight' ? 1 : order.length - 1)) % order.length]
        onSelect(next)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [d.code, order, onClose, onSelect])

  const markers = useMemo<ChartMarker[]>(() => {
    const out: ChartMarker[] = []
    for (const t of d.ticks) {
      if (t.kind === 'race' && t.position === 1) out.push({ time: t.ts, label: 'W', color: '#ffc53d', shape: 'arrowUp', above: false })
      else if (t.kind === 'qualifying' && t.position === 1) out.push({ time: t.ts, label: 'P', color: '#8fd6ff', shape: 'circle' })
      else if ((t.kind === 'race' || t.kind === 'sprint') && t.position == null) out.push({ time: t.ts, label: 'DNF', color: '#ff4d6a', shape: 'arrowDown' })
    }
    return out
  }, [d.ticks])

  const big = useMemo(() => {
    const sorted = [...d.ticks].sort((a, b) => b.change_pct - a.change_pct)
    return { up: sorted.slice(0, 3).filter((t) => t.change_pct > 0), down: sorted.slice(-3).reverse().filter((t) => t.change_pct < 0) }
  }, [d.ticks])

  const recent = d.ticks.slice(-8).reverse()
  const s = d.stats
  const stats: [string, string, string?][] = [
    ['Points', String(s.points), `P${d.pointsRank} in standings`],
    ['Wins', String(s.wins)],
    ['Podiums', String(s.podiums)],
    ['Poles', String(s.poles)],
    ['DNFs', String(s.dnfs)],
    ['Avg finish', s.avgFinish ? s.avgFinish.toFixed(1) : '—', s.bestFinish ? `Best ${ordinal(s.bestFinish)}` : undefined],
    ['Market rank', `#${d.valueRank}`, d.gap > 0 ? `Undervalued by ${d.gap}` : d.gap < 0 ? `Priced ${-d.gap} above form` : 'Fairly priced'],
    ['Beat expectation', s.beatRate == null ? '—' : `${Math.round(s.beatRate * 100)}%`, 'of quali + race sessions'],
  ]

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <motion.div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
      <motion.div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="driver-name"
        tabIndex={-1}
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 36 }}
        className="scrollbar-thin relative h-full w-full max-w-[560px] overflow-y-auto border-l border-line bg-bg shadow-2xl focus:outline-none"
      >
        {/* Hero */}
        <div className="relative isolate overflow-hidden" style={{ background: `linear-gradient(135deg, ${withAlpha(d.color, 0.45)}, ${withAlpha(d.color, 0.06)} 60%, transparent)` }}>
          <span aria-hidden="true" className="absolute -right-4 -top-8 -z-10 select-none text-[12rem] font-black italic leading-none" style={{ color: withAlpha(d.color, 0.16) }}>
            {d.number}
          </span>
          <img
            src={driverImg(d.code)}
            alt={d.name}
            className="absolute bottom-0 right-6 -z-10 h-[88%] w-auto object-contain opacity-95 [mask-image:radial-gradient(ellipse_65%_75%_at_50%_35%,black_45%,transparent_78%)]"
            style={{ mixBlendMode: 'luminosity' }}
          />
          <div className="absolute inset-0 -z-10 bg-gradient-to-t from-bg via-bg/40 to-transparent" />
          <div className="flex items-center justify-between p-4">
            <div className="flex gap-1.5">
              {(['ArrowLeft', 'ArrowRight'] as const).map((k) => (
                <button
                  key={k}
                  aria-label={k === 'ArrowLeft' ? 'Previous driver' : 'Next driver'}
                  onClick={() => {
                    const i = order.indexOf(d.code)
                    onSelect(order[(i + (k === 'ArrowRight' ? 1 : order.length - 1)) % order.length])
                  }}
                  className="grid h-9 w-9 place-items-center rounded-lg bg-black/30 text-dim backdrop-blur hover:text-ink"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                    <path d={k === 'ArrowLeft' ? 'm15 18-6-6 6-6' : 'm9 18 6-6-6-6'} />
                  </svg>
                </button>
              ))}
            </div>
            <button onClick={onClose} aria-label="Close" className="grid h-9 w-9 place-items-center rounded-lg bg-black/30 text-dim backdrop-blur hover:text-ink">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </div>
          <div className="px-6 pb-6 pt-16">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-dim">
              <span className="h-3 w-[3px] rounded-full" style={{ background: d.color }} aria-hidden="true" />
              {d.teamName} · {d.country} · #{d.number}
            </div>
            <h2 id="driver-name" className="mt-1 text-4xl font-black uppercase italic leading-[0.95] tracking-tight">
              {d.name.split(' ').slice(0, -1).join(' ')}
              <span className="block" style={{ color: d.color }}>{d.name.split(' ').slice(-1)}</span>
            </h2>
            <div className="mt-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="num text-4xl font-semibold">{money(value)}</span>
              <Change value={d.seasonChange} badge className="text-sm" />
              <span className="text-xs text-faint">since baseline {money(d.baseline)}</span>
            </div>
            {!d.active && <p className="mt-2 text-sm text-dim">Not on the grid anymore; the stock is frozen.</p>}
          </div>
        </div>

        <div className="space-y-6 p-6 pt-2">
          {trade}
          <div className="-mx-2">
            <PriceChart data={d.history} base={d.baseline} markers={markers} height={230} label={`${d.name} price history`} />
            <p className="mt-1 px-2 text-[0.7rem] text-faint">
              <span className="text-gold">W</span> win · <span className="text-[#8fd6ff]">P</span> pole · <span className="text-down">DNF</span> retirement · dotted line = baseline
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {stats.map(([label, v, hint]) => (
              <div key={label} className="rounded-xl border border-line bg-surface p-3">
                <dt className="text-[0.65rem] font-bold uppercase tracking-wider text-faint">{label}</dt>
                <dd className="num mt-1 text-xl font-semibold">{v}</dd>
                {hint && <dd className="mt-0.5 text-[0.68rem] leading-tight text-faint">{hint}</dd>}
              </div>
            ))}
          </dl>

          <div className="grid gap-4 sm:grid-cols-2">
            <MoveList title="Biggest gains" ticks={big.up} empty="No gains yet" />
            <MoveList title="Biggest drops" ticks={big.down} empty="No drops yet" />
          </div>

          <div>
            <h3 className="eyebrow mb-2">Recent sessions</h3>
            <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line">
              {recent.map((t) => (
                <li key={t.id} className="bg-surface px-3.5 py-2.5">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="rounded bg-white/5 px-1.5 py-0.5 text-[0.65rem] font-bold tracking-wider text-faint">{sessionShort(t.session)}</span>
                    <span className="truncate font-semibold">{t.race.replace(' Grand Prix', ' GP')}</span>
                    <span className="num text-xs text-dim">{t.position ? `P${t.position}` : 'DNF'}</span>
                    <Change value={t.change_pct} className="ml-auto text-sm" />
                  </div>
                  {t.moves.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {t.moves.map((m) => (
                        <span key={m.label} className={`rounded-md px-1.5 py-0.5 text-[0.68rem] ${m.pct >= 0 ? 'bg-up/10 text-up' : 'bg-down/10 text-down'}`}>
                          {m.label} <span className="num opacity-75">{pct(m.pct)}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
              {!recent.length && <li className="bg-surface px-3.5 py-6 text-center text-sm text-faint">No sessions yet.</li>}
            </ul>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

function MoveList({ title, ticks, empty }: { title: string; ticks: Tick[]; empty: string }) {
  return (
    <div>
      <h3 className="eyebrow mb-2">{title}</h3>
      <ul className="space-y-1.5">
        {ticks.map((t) => {
          const headline = [...t.moves].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))[0]
          return (
            <li key={t.id} className="rounded-xl border border-line bg-surface px-3 py-2">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate font-semibold">{t.race.replace(' Grand Prix', ' GP')} <span className="text-faint">{sessionShort(t.session)}</span></span>
                <Change value={t.change_pct} className="text-sm" />
              </div>
              {headline && <div className="mt-0.5 truncate text-xs text-faint">{headline.label}</div>}
            </li>
          )
        })}
        {!ticks.length && <li className="text-sm text-faint">{empty}</li>}
      </ul>
    </div>
  )
}
