import { LayoutGroup, motion } from 'motion/react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { money } from '../lib/format'
import type { DriverView, MarketView } from '../lib/market'
import type { Team } from '../lib/types'
import type { Flash } from '../lib/useMarket'
import DriverCard from './DriverCard'
import Sparkline from './Sparkline'
import { Avatar, Change, Segmented, TeamDot } from './ui'

type Sort = 'value' | 'change' | 'points' | 'name'
type View = 'cards' | 'table'

interface Props {
  market: MarketView
  teams: Record<string, Team>
  flashes: Record<string, Flash>
  owned: Set<string>
  onSelect: (code: string) => void
}

const SORTERS: Record<Sort, (a: DriverView, b: DriverView) => number> = {
  value: (a, b) => b.value - a.value,
  change: (a, b) => b.change - a.change,
  points: (a, b) => a.pointsRank - b.pointsRank,
  name: (a, b) => a.name.localeCompare(b.name),
}

export default function MarketBoard({ market, teams, flashes, owned, onSelect }: Props) {
  const [sort, setSort] = useState<Sort>('value')
  const [view, setView] = useState<View>(() => {
    try {
      return localStorage.getItem('gp.view') === 'table' ? 'table' : 'cards'
    } catch {
      return 'cards'
    }
  })
  const [team, setTeam] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const search = useRef<HTMLInputElement>(null)

  useEffect(() => {
    try {
      localStorage.setItem('gp.view', view)
    } catch {
      /* storage unavailable */
    }
  }, [view])

  // "/" jumps to search, like most trading terminals and dev tools.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (e.key === '/' && !/input|textarea|select/i.test(target.tagName)) {
        e.preventDefault()
        search.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const drivers = useMemo(() => {
    const q = query.trim().toLowerCase()
    return market.drivers
      .filter((d) => !team || d.team === team)
      .filter((d) => !q || d.name.toLowerCase().includes(q) || d.code.toLowerCase().includes(q) || d.teamName.toLowerCase().includes(q))
      .sort((a, b) => Number(b.active) - Number(a.active) || SORTERS[sort](a, b))
  }, [market.drivers, team, query, sort])

  const teamList = useMemo(() => {
    const present = new Set(market.drivers.map((d) => d.team))
    return Object.entries(teams).filter(([key]) => present.has(key))
  }, [teams, market.drivers])

  return (
    <section className="panel p-4 sm:p-5" aria-labelledby="board-title">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="board-title" className="text-xl font-black uppercase italic tracking-tight">
          The grid <span className="num ml-1 align-middle text-sm font-normal not-italic text-faint">{drivers.length}</span>
        </h2>
        <div className="relative ml-auto w-full sm:w-56">
          <label htmlFor="driver-search" className="sr-only">Search drivers</label>
          <input
            id="driver-search"
            ref={search}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search drivers"
            className="h-9 w-full rounded-lg border border-line bg-black/30 pl-9 pr-8 text-sm placeholder:text-faint focus:border-line-strong focus:outline-none"
          />
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-line px-1.5 text-[0.65rem] text-faint">/</kbd>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="sort" className="sr-only">Sort by</label>
          <select
            id="sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="h-9 rounded-lg border border-line bg-black/30 px-2.5 text-sm font-semibold text-ink focus:outline-none"
          >
            <option value="value">Sort: Market value</option>
            <option value="change">Sort: Change</option>
            <option value="points">Sort: Standings</option>
            <option value="name">Sort: Name</option>
          </select>
          <Segmented
            label="Layout"
            value={view}
            onChange={setView}
            options={[
              { value: 'cards', label: 'Cards' },
              { value: 'table', label: 'Table' },
            ]}
          />
        </div>
      </div>

      <div className="no-scrollbar -mx-1 mt-3 flex gap-1.5 overflow-x-auto px-1 pb-1" role="group" aria-label="Filter by team">
        <Chip active={!team} onClick={() => setTeam(null)}>All teams</Chip>
        {teamList.map(([key, t]) => (
          <Chip key={key} active={team === key} onClick={() => setTeam(team === key ? null : key)}>
            <TeamDot color={t.color} />
            {t.name}
          </Chip>
        ))}
      </div>

      {drivers.length === 0 ? (
        <p className="py-16 text-center text-sm text-faint">No drivers match “{query}”.</p>
      ) : view === 'cards' ? (
        <LayoutGroup>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 2xl:grid-cols-3">
            {drivers.map((d) => (
              <motion.div key={d.code} layout transition={{ type: 'spring', stiffness: 380, damping: 34 }}>
                <DriverCard driver={d} flash={flashes[d.code]} owned={owned.has(d.code)} onSelect={onSelect} />
              </motion.div>
            ))}
          </div>
        </LayoutGroup>
      ) : (
        <Table drivers={drivers} flashes={flashes} sort={sort} onSort={setSort} onSelect={onSelect} />
      )}
    </section>
  )
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
        active ? 'border-white/25 bg-white/10 text-ink' : 'border-line text-dim hover:border-line-strong hover:text-ink'
      }`}
    >
      {children}
    </button>
  )
}

function Table({ drivers, flashes, sort, onSort, onSelect }: {
  drivers: DriverView[]; flashes: Record<string, Flash>; sort: Sort; onSort: (s: Sort) => void; onSelect: (c: string) => void
}) {
  const header = (key: Sort | null, label: string, className = '') => (
    <th scope="col" className={`px-3 py-2 font-semibold ${className}`} aria-sort={key && sort === key ? 'descending' : undefined}>
      {key ? (
        <button onClick={() => onSort(key)} className={`uppercase tracking-wider hover:text-ink ${sort === key ? 'text-ink' : ''}`}>
          {label}{sort === key && <span aria-hidden="true"> ↓</span>}
        </button>
      ) : (
        <span className="uppercase tracking-wider">{label}</span>
      )}
    </th>
  )
  return (
    <div className="scrollbar-thin -mx-4 mt-4 overflow-x-auto sm:-mx-5">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[0.68rem] text-faint">
            {header(null, '#', 'w-10 text-right')}
            {header('name', 'Driver')}
            {header('value', 'Value', 'text-right')}
            {header('change', 'Change', 'text-right')}
            {header(null, 'Trend')}
            {header('points', 'Pts', 'text-right')}
            {header(null, 'W · Pod · Pole · DNF', 'text-right')}
          </tr>
        </thead>
        <tbody>
          {drivers.map((d) => {
            const flash = flashes[d.code]
            return (
              <tr
                key={d.code}
                onClick={() => onSelect(d.code)}
                className={`cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-white/[0.035] ${d.active ? '' : 'opacity-55'}`}
              >
                <td className="num px-3 py-2 text-right text-faint">{d.valueRank}</td>
                <td className="px-3 py-2">
                  <button onClick={(e) => { e.stopPropagation(); onSelect(d.code) }} className="flex items-center gap-3 text-left">
                    <Avatar code={d.code} color={d.color} size={34} className="rounded-lg" />
                    <span>
                      <span className="block font-bold">{d.name}</span>
                      <span className="flex items-center gap-1.5 text-xs text-faint"><TeamDot color={d.color} className="h-1.5 w-1.5" />{d.teamName}</span>
                    </span>
                  </button>
                </td>
                <td className="relative px-3 py-2 text-right">
                  {flash && <span key={flash.id} aria-hidden="true" className={`absolute inset-1 rounded-md ${flash.up ? 'flash-up' : 'flash-down'}`} />}
                  <span className="num relative font-semibold">{money(d.value)}</span>
                </td>
                <td className="px-3 py-2 text-right"><Change value={d.change} /></td>
                <td className="px-3 py-2"><Sparkline points={d.history.slice(-40)} width={88} height={26} up={d.seasonChange >= 0} /></td>
                <td className="num px-3 py-2 text-right">{d.stats.points}</td>
                <td className="num px-3 py-2 text-right text-dim">
                  {d.stats.wins} · {d.stats.podiums} · {d.stats.poles} · <span className={d.stats.dnfs ? 'text-down' : ''}>{d.stats.dnfs}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
