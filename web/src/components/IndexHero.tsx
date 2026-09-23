import { useMemo } from 'react'
import { money } from '../lib/format'
import { useTweened } from '../lib/hooks'
import type { MarketView } from '../lib/market'
import type { Race, Range } from '../lib/types'
import PriceChart, { type ChartMarker } from './PriceChart'
import { Change, Segmented } from './ui'

interface Props {
  market: MarketView
  calendar: Race[]
  range: Range
  onRange: (r: Range) => void
}

const indexFormat = (v: number) => v.toFixed(1)

const RANGE_OPTIONS: { value: Range; label: string; title: string }[] = [
  { value: 'session', label: 'Session', title: 'Change over the latest session' },
  { value: 'weekend', label: 'Weekend', title: 'Change over the latest race weekend' },
  { value: 'season', label: 'Season', title: 'Change since the baseline valuation' },
]

export default function IndexHero({ market, calendar, range, onRange }: Props) {
  const value = useTweened(market.index.value)
  const cap = useTweened(market.marketCap)

  const markers = useMemo<ChartMarker[]>(
    () =>
      calendar
        .filter((r) => market.roundsPriced.has(r.round))
        .map((r) => {
          const race = r.sessions.find((s) => s.key === 'race')
          return { time: race ? race.ts + 150 : 0, label: r.country, color: 'rgba(238,242,247,0.55)', shape: 'circle' as const }
        })
        .filter((m) => m.time),
    [calendar, market.roundsPriced],
  )

  const rangeLabel = { session: market.latest?.sessionName ?? 'Session', weekend: market.latest?.race ?? 'Weekend', season: 'Since baseline' }[range]

  return (
    <section className="panel flex w-full flex-col overflow-hidden p-5 sm:p-6" aria-labelledby="index-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="index-title" className="eyebrow flex items-center gap-2">
            Pulse Index
            <span className="rounded bg-white/5 px-1.5 py-0.5 text-[0.6rem] tracking-widest text-faint" title="Cap-weighted index of every driver on the exchange, base 1000 at the baseline valuation">
              Base 1000
            </span>
          </h2>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="num text-5xl font-semibold tracking-tighter sm:text-6xl">
              {value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <Change value={market.index.change} badge className="text-base" />
            <span className="text-sm text-faint">{rangeLabel}</span>
          </div>
          <p className="mt-1 text-sm text-dim">
            Total market cap <span className="num text-ink">{money(cap)}</span> across {market.drivers.length} drivers
          </p>
        </div>
        <Segmented label="Change range" value={range} options={RANGE_OPTIONS} onChange={onRange} size="md" />
      </div>

      {/* Absolutely positioned so the chart fills the space without feeding back into it. */}
      <div className="relative -mx-2 mt-4 min-h-[300px] flex-1">
        <div className="absolute inset-0">
          <PriceChart
            data={market.index.series}
            base={1000}
            markers={markers}
            height="100%"
            format={indexFormat}
            label={`Pulse Index chart, currently ${market.index.value.toFixed(1)}`}
          />
        </div>
      </div>
    </section>
  )
}
