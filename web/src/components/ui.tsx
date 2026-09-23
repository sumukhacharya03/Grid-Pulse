import type { ReactNode } from 'react'
import { arrow, pct, trendClass } from '../lib/format'

export function Avatar({ code, color, size = 48, className = '' }: { code: string; color: string; size?: number; className?: string }) {
  return (
    <div
      className={`relative shrink-0 overflow-hidden rounded-xl bg-raised ${className}`}
      style={{ width: size, height: size, boxShadow: `0 0 0 1.5px ${color}, 0 6px 18px -6px ${color}` }}
    >
      <img
        src={`/drivers/${code}.jpg`}
        alt=""
        loading="lazy"
        className="h-full w-full object-cover"
        style={{ objectPosition: '50% 12%', transform: 'scale(1.25)', transformOrigin: '50% 10%' }}
        onError={(e) => ((e.currentTarget.style.visibility = 'hidden'))}
      />
    </div>
  )
}

export function Change({ value, className = '', digits = 2, badge = false }: { value: number; className?: string; digits?: number; badge?: boolean }) {
  const tone = trendClass(value)
  const bg = badge ? (value > 0.0001 ? 'bg-up/12' : value < -0.0001 ? 'bg-down/12' : 'bg-white/5') : ''
  return (
    <span className={`num inline-flex items-center gap-1 whitespace-nowrap ${tone} ${bg} ${badge ? 'rounded-md px-1.5 py-0.5' : ''} ${className}`}>
      <span aria-hidden="true" className="text-[0.7em]">{arrow(value)}</span>
      {pct(value, digits)}
    </span>
  )
}

interface SegmentedProps<T extends string> {
  value: T
  options: { value: T; label: ReactNode; title?: string }[]
  onChange: (v: T) => void
  label: string
  size?: 'sm' | 'md'
}

export function Segmented<T extends string>({ value, options, onChange, label, size = 'sm' }: SegmentedProps<T>) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-line bg-black/30 p-0.5">
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            role="radio"
            aria-checked={active}
            title={o.title}
            onClick={() => onChange(o.value)}
            className={`rounded-md font-semibold transition-colors ${size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-sm'} ${
              active ? 'bg-white/10 text-ink shadow-[inset_0_0_0_1px_rgb(255_255_255/0.08)]' : 'text-dim hover:text-ink'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

export function TeamDot({ color, className = '' }: { color: string; className?: string }) {
  return <span aria-hidden="true" className={`inline-block h-2 w-2 shrink-0 rounded-full ${className}`} style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
}
