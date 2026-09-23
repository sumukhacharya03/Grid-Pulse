import { AnimatePresence, motion } from 'motion/react'
import { useMemo, useState } from 'react'
import { money, pct, sessionShort } from '../lib/format'
import type { MarketView } from '../lib/market'
import type { Tick } from '../lib/types'
import { Change, Segmented } from './ui'

interface Props {
  ticks: Tick[]
  market: MarketView
  onSelect: (code: string) => void
}

type Filter = 'all' | 'big'
const LIMIT = 90

export default function Feed({ ticks, market, onSelect }: Props) {
  const [filter, setFilter] = useState<Filter>('all')

  const groups = useMemo(() => {
    const picked: Tick[] = []
    for (let i = ticks.length - 1; i >= 0 && picked.length < LIMIT; i--) {
      const t = ticks[i]
      if (Math.abs(t.change_pct) < (filter === 'big' ? 1 : 0.005)) continue
      picked.push(t)
    }
    const out: { key: string; race: string; session: string; round: number; live: boolean; items: Tick[] }[] = []
    for (const t of picked) {
      const key = `${t.round}:${t.session}`
      const last = out[out.length - 1]
      if (last?.key === key) last.items.push(t)
      else out.push({ key, race: t.race, session: t.session, round: t.round, live: t.live, items: [t] })
    }
    return out
  }, [ticks, filter])

  return (
    <section className="panel flex max-h-[calc(100dvh-6rem)] flex-col overflow-hidden lg:sticky lg:top-20" aria-labelledby="feed-title">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3.5">
        <h2 id="feed-title" className="text-xl font-black uppercase italic tracking-tight">Pit wall</h2>
        <Segmented
          label="Feed filter"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'all', label: 'All moves' },
            { value: 'big', label: '±1%+', title: 'Only moves of 1% or more' },
          ]}
        />
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto" aria-live="polite" aria-relevant="additions">
        {groups.length === 0 && <p className="px-4 py-12 text-center text-sm text-faint">No price moves yet.</p>}
        {groups.map((g) => (
          <div key={g.key}>
            <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-line bg-surface/95 px-4 py-2 backdrop-blur">
              {g.live && <span className="rounded bg-[#ff2d3d]/15 px-1.5 text-[0.6rem] font-bold uppercase tracking-widest text-[#ff5a66]">Live</span>}
              <span className="truncate text-xs font-bold text-dim">{g.race.replace(' Grand Prix', ' GP')}</span>
              <span className="ml-auto rounded bg-white/5 px-1.5 py-0.5 text-[0.65rem] font-bold tracking-wider text-faint">
                R{g.round} · {sessionShort(g.session)}
              </span>
            </div>
            <ul>
              <AnimatePresence initial={false}>
                {g.items.map((t) => {
                  const d = market.byCode[t.driver_code]
                  const [headline, ...rest] = [...t.moves].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))
                  return (
                    <motion.li
                      key={t.id}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      transition={{ duration: 0.3 }}
                    >
                      <button onClick={() => onSelect(t.driver_code)} className="flex w-full gap-3 border-b border-line px-4 py-2.5 text-left transition-colors hover:bg-white/[0.035]">
                        <span className="mt-1 h-8 w-[3px] shrink-0 rounded-full" style={{ background: d?.color }} aria-hidden="true" />
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-2">
                            <span className="font-bold">{t.driver_code}</span>
                            <Change value={t.change_pct} className="text-sm" />
                            <span className="num ml-auto text-xs text-faint">{money(t.value_after)}</span>
                          </span>
                          {headline && (
                            <span className="mt-0.5 block truncate text-xs text-dim">
                              {headline.label}
                              <span className="num text-faint"> {pct(headline.pct)}</span>
                              {rest.length > 0 && <span className="text-faint"> · +{rest.length} more</span>}
                            </span>
                          )}
                        </span>
                      </button>
                    </motion.li>
                  )
                })}
              </AnimatePresence>
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}
