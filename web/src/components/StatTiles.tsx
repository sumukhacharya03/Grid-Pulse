import type { ReactNode } from 'react'
import type { DriverView, MarketView } from '../lib/market'
import { Avatar, Change } from './ui'

interface Props {
  market: MarketView
  onSelect: (code: string) => void
}

export default function StatTiles({ market, onSelect }: Props) {
  const active = market.drivers.filter((d) => d.active)
  if (!active.length) return null
  const byChange = [...active].sort((a, b) => b.change - a.change)
  const leader = [...active].sort((a, b) => a.pointsRank - b.pointsRank)[0]
  const undervalued = [...active].sort((a, b) => b.gap - a.gap || a.pointsRank - b.pointsRank)[0]

  const tiles: { title: string; driver: DriverView; metric: ReactNode; note: string; accent: string }[] = [
    { title: 'Top gainer', driver: byChange[0], metric: <Change value={byChange[0].change} />, note: 'Biggest rise in range', accent: 'from-up/15' },
    { title: 'Biggest faller', driver: byChange[byChange.length - 1], metric: <Change value={byChange[byChange.length - 1].change} />, note: 'Steepest drop in range', accent: 'from-down/15' },
    {
      title: 'Championship leader', driver: leader, accent: 'from-gold/15',
      metric: <span className="num text-gold">{leader.stats.points} pts</span>,
      note: `${leader.stats.wins} win${leader.stats.wins === 1 ? '' : 's'} · ${leader.stats.podiums} podiums`,
    },
    {
      title: 'Most undervalued', driver: undervalued, accent: 'from-[#64c4ff]/15',
      metric: <span className="num text-[#8fd6ff]">{undervalued.gap > 0 ? `+${undervalued.gap} ranks` : 'Fairly priced'}</span>,
      note: `P${undervalued.pointsRank} on points, #${undervalued.valueRank} by value`,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {tiles.map((t) => (
        <button
          key={t.title}
          onClick={() => onSelect(t.driver.code)}
          className={`panel group flex items-center gap-3.5 bg-gradient-to-br ${t.accent} to-transparent p-4 text-left transition-colors hover:border-line-strong`}
        >
          <Avatar code={t.driver.code} color={t.driver.color} size={52} className="transition-transform group-hover:scale-105" />
          <div className="min-w-0 flex-1">
            <div className="eyebrow text-[0.62rem]">{t.title}</div>
            <div className="mt-0.5 truncate text-lg font-bold leading-tight">{t.driver.name}</div>
            <div className="mt-0.5 flex items-center gap-2 text-sm">
              {t.metric}
              <span className="truncate text-xs text-faint">{t.note}</span>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
