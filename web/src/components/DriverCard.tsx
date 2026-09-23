import { memo } from 'react'
import { money, withAlpha } from '../lib/format'
import { useTweened } from '../lib/hooks'
import type { DriverView } from '../lib/market'
import type { Flash } from '../lib/useMarket'
import Sparkline from './Sparkline'
import { Avatar, Change } from './ui'

interface Props {
  driver: DriverView
  flash?: Flash
  owned?: boolean
  onSelect: (code: string) => void
}

function DriverCard({ driver: d, flash, owned, onSelect }: Props) {
  const value = useTweened(d.value)
  const recent = d.history.slice(-40)

  return (
    <button
      onClick={() => onSelect(d.code)}
      aria-label={`${d.name}, ${money(d.value)}, ${d.change >= 0 ? 'up' : 'down'} ${Math.abs(d.change).toFixed(2)} percent`}
      className={`group relative isolate flex h-full w-full flex-col overflow-hidden rounded-2xl border border-line bg-surface p-4 text-left transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 ${
        d.active ? '' : 'opacity-55'
      }`}
      style={{ ['--team' as string]: d.color }}
    >
      {/* Team light, number watermark, hover glow */}
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px]" style={{ background: d.color }} />
      <span
        aria-hidden="true"
        className="absolute inset-0 -z-10 opacity-60 transition-opacity group-hover:opacity-100"
        style={{ background: `radial-gradient(120% 90% at 0% 0%, ${withAlpha(d.color, 0.16)}, transparent 55%)` }}
      />
      <span aria-hidden="true" className="pointer-events-none absolute -right-2 -top-5 -z-10 select-none text-[5.5rem] font-black italic leading-none" style={{ color: withAlpha(d.color, 0.09) }}>
        {d.number}
      </span>
      <span aria-hidden="true" className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity group-hover:opacity-100" style={{ boxShadow: `inset 0 0 0 1px ${withAlpha(d.color, 0.55)}, 0 12px 40px -18px ${d.color}` }} />
      {flash && <span key={flash.id} aria-hidden="true" className={`pointer-events-none absolute inset-0 rounded-2xl ${flash.up ? 'flash-up' : 'flash-down'}`} />}

      <div className="flex items-start gap-3">
        <Avatar code={d.code} color={d.color} size={54} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-black tracking-wide">{d.code}</span>
            <span className="num text-xs text-faint">#{d.valueRank}</span>
            {!d.active && <span className="rounded bg-white/10 px-1.5 text-[0.6rem] font-bold uppercase tracking-widest text-dim">Reserve</span>}
            {owned && <span className="rounded bg-gold/15 px-1.5 text-[0.6rem] font-bold uppercase tracking-widest text-gold">Owned</span>}
          </div>
          <div className="truncate text-sm font-semibold text-dim">{d.name}</div>
          <div className="truncate text-xs text-faint">{d.teamName}</div>
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between gap-2">
        <div>
          <div className="num text-2xl font-semibold leading-none">{money(value)}</div>
          <Change value={d.change} className="mt-1.5 text-sm" badge />
        </div>
        <Sparkline points={recent} up={recent.length < 2 || recent[recent.length - 1].value >= recent[0].value} />
      </div>

      <div className="mt-3 flex items-center gap-3 border-t border-line pt-2.5 text-[0.7rem] text-faint">
        <span><span className="num text-dim">{d.stats.points}</span> pts</span>
        <span><span className="num text-dim">{d.stats.wins}</span> W</span>
        <span><span className="num text-dim">{d.stats.podiums}</span> Pod</span>
        <span className="ml-auto">P{d.pointsRank} in standings</span>
      </div>
    </button>
  )
}

export default memo(DriverCard)
