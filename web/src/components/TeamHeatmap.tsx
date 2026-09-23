import { useMemo } from 'react'
import { money, pct } from '../lib/format'
import type { DriverView, MarketView } from '../lib/market'
import { squarify } from '../lib/treemap'
import type { Range, Team } from '../lib/types'

interface Props {
  market: MarketView
  teams: Record<string, Team>
  range: Range
  onSelect: (code: string) => void
}

const W = 1000
const H = 460
const HEADER = 26
// Change that saturates the colour scale, per range.
const SATURATE: Record<Range, number> = { session: 1.5, weekend: 4, season: 25 }

// Tile area follows value^0.3 so a $0.4M rookie is still a readable tile
// next to a $75M world champion (linear area would make it a sliver).
const weight = (d: DriverView) => Math.pow(d.value, 0.3)

function tone(change: number, range: Range): string {
  const t = Math.min(1, Math.abs(change) / SATURATE[range])
  if (Math.abs(change) < 0.005) return '#151a21'
  const color = change > 0 ? 'var(--color-up)' : 'var(--color-down)'
  return `color-mix(in oklab, ${color} ${Math.round(12 + t * 58)}%, #0f1319)`
}

export default function TeamHeatmap({ market, teams, range, onSelect }: Props) {
  const layout = useMemo(() => {
    const active = market.drivers.filter((d) => d.active)
    const byTeam = new Map<string, DriverView[]>()
    for (const d of active) byTeam.set(d.team, [...(byTeam.get(d.team) ?? []), d])
    const groups = [...byTeam.entries()].map(([team, drivers]) => ({ team, drivers, w: drivers.reduce((s, d) => s + weight(d), 0) }))
    return squarify(groups, (g) => g.w, { x: 0, y: 0, w: W, h: H }).map(({ item, rect }) => {
      const inner = { x: rect.x + 3, y: rect.y + HEADER, w: rect.w - 6, h: rect.h - HEADER - 3 }
      const cap = item.drivers.reduce((s, d) => s + d.value, 0)
      const ref = item.drivers.reduce((s, d) => s + d.value / (1 + d.change / 100), 0)
      return {
        ...item,
        rect,
        change: (cap / ref - 1) * 100,
        tiles: squarify(item.drivers, weight, inner),
      }
    })
  }, [market.drivers])

  const pos = (r: { x: number; y: number; w: number; h: number }) => ({
    left: `${(r.x / W) * 100}%`,
    top: `${(r.y / H) * 100}%`,
    width: `${(r.w / W) * 100}%`,
    height: `${(r.h / H) * 100}%`,
  })

  return (
    <section className="panel p-4 sm:p-5" aria-labelledby="heatmap-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="heatmap-title" className="text-xl font-black uppercase italic tracking-tight">Constructors heatmap</h2>
          <p className="text-xs text-faint">Tile size follows market value (compressed scale) · colour shows change over the selected range</p>
        </div>
        <div className="flex items-center gap-2 text-[0.65rem] text-faint" aria-hidden="true">
          <span className="num">−{SATURATE[range]}%</span>
          <span className="h-2 w-28 rounded-full" style={{ background: 'linear-gradient(90deg, var(--color-down), #151a21, var(--color-up))' }} />
          <span className="num">+{SATURATE[range]}%</span>
        </div>
      </div>

      <div className="relative mt-4 w-full overflow-hidden rounded-xl bg-black/40" style={{ aspectRatio: `${W} / ${H}`, minHeight: 260 }}>
        {layout.map((g) => {
          const team = teams[g.team]
          return (
            <div key={g.team} className="absolute" style={pos(g.rect)}>
              <div className="absolute inset-[1.5px] rounded-lg border border-white/[0.06]" />
              <div className="absolute inset-x-2 top-0 flex h-[26px] items-center gap-1.5 overflow-hidden text-[0.68rem] font-bold uppercase tracking-wider">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: team?.color }} aria-hidden="true" />
                <span className="truncate text-dim">{team?.name ?? g.team}</span>
                <span className={`num ml-auto shrink-0 ${g.change >= 0 ? 'text-up' : 'text-down'}`}>{pct(g.change, 1)}</span>
              </div>
            </div>
          )
        })}
        {layout.flatMap((g) =>
          g.tiles.map(({ item: d, rect }) => {
            const wPct = rect.w / W
            const hPct = rect.h / H
            const big = wPct > 0.09 && hPct > 0.16
            const tiny = wPct < 0.045 || hPct < 0.08
            return (
              <button
                key={d.code}
                onClick={() => onSelect(d.code)}
                title={`${d.name} · ${money(d.value)} · ${pct(d.change)}`}
                aria-label={`${d.name}, ${money(d.value)}, ${pct(d.change)}`}
                className="group absolute p-[1.5px]"
                style={pos(rect)}
              >
                <span
                  className="flex h-full w-full flex-col items-center justify-center overflow-hidden rounded-md transition-[filter,box-shadow] group-hover:brightness-125 group-hover:[box-shadow:inset_0_0_0_1px_rgb(255_255_255/0.5)]"
                  style={{ background: tone(d.change, range) }}
                >
                  {!tiny && <span className={`font-black tracking-wide ${big ? 'text-xl' : 'text-xs'}`}>{d.code}</span>}
                  {!tiny && <span className={`num ${big ? 'text-sm' : 'text-[0.65rem]'} text-white/85`}>{pct(d.change, big ? 2 : 1)}</span>}
                  {big && <span className="num mt-0.5 text-[0.7rem] text-white/55">{money(d.value)}</span>}
                </span>
              </button>
            )
          }),
        )}
      </div>
    </section>
  )
}
