import { useId } from 'react'
import type { Point } from '../lib/market'

interface Props {
  points: Point[]
  width?: number
  height?: number
  up: boolean
}

export default function Sparkline({ points, width = 96, height = 32, up }: Props) {
  const id = useId()
  if (points.length < 2) return <svg width={width} height={height} aria-hidden="true" />
  const values = points.map((p) => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const step = width / (points.length - 1)
  const coords = values.map((v, i) => [i * step, height - 2 - ((v - min) / span) * (height - 4)] as const)
  const line = coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('')
  const color = up ? 'var(--color-up)' : 'var(--color-down)'
  const [lx, ly] = coords[coords.length - 1]
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${line}L${width},${height}L0,${height}Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="2.5" fill={color} />
    </svg>
  )
}
