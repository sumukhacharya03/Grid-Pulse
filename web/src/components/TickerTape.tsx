import type { DriverView } from '../lib/market'
import { money } from '../lib/format'
import { Change } from './ui'

interface Props {
  drivers: DriverView[]
  onSelect: (code: string) => void
}

export default function TickerTape({ drivers, onSelect }: Props) {
  const items = drivers.filter((d) => d.active)
  const row = (hidden: boolean) =>
    items.map((d) => (
      <button
        key={`${d.code}-${hidden}`}
        tabIndex={hidden ? -1 : 0}
        aria-hidden={hidden || undefined}
        onClick={() => onSelect(d.code)}
        className="flex shrink-0 items-center gap-2.5 px-5 py-2 text-sm transition-colors hover:bg-white/5"
      >
        <span className="h-3.5 w-[3px] rounded-full" style={{ background: d.color }} aria-hidden="true" />
        <span className="font-bold tracking-wide">{d.code}</span>
        <span className="num text-dim">{money(d.value)}</span>
        <Change value={d.change} className="text-xs" />
      </button>
    ))

  return (
    <div className="no-scrollbar group relative overflow-hidden border-b border-line bg-surface/60 motion-reduce:overflow-x-auto" aria-label="Driver price ticker">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-bg to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-bg to-transparent" />
      <div className="flex w-max animate-marquee group-hover:[animation-play-state:paused] group-focus-within:[animation-play-state:paused] motion-reduce:animate-none">
        {row(false)}
        {row(true)}
      </div>
    </div>
  )
}
