import type { Connection } from '../lib/useMarket'
import { useNow } from '../lib/hooks'

interface Props {
  connection: Connection
  mode: 'kafka' | 'demo' | null
  data: 'real' | 'simulated' | null
  live: boolean
  round: number
  totalRounds: number
  raceName: string | null
}

export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="38" height="38" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="14" fill="#11151c" stroke="rgba(255,255,255,0.08)" />
        <path d="M6 36h13l5-14 8 26 6-18 4 6h16" fill="none" stroke="rgba(225,6,0,0.25)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
        <path className="pulse-line" d="M6 36h13l5-14 8 26 6-18 4 6h16" fill="none" stroke="#ff2d20" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="leading-none">
        <div className="text-[1.35rem] font-black uppercase italic tracking-tight">
          Grid<span className="text-brand">/</span>Pulse
        </div>
        <div className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.32em] text-faint">F1 Driver Exchange</div>
      </div>
    </div>
  )
}

export default function Header({ connection, mode, data, live, round, totalRounds, raceName }: Props) {
  const now = useNow()
  const open = connection === 'open'
  const status = !open
    ? { label: connection === 'connecting' ? 'Connecting' : 'Reconnecting', dot: 'bg-gold', text: 'text-gold' }
    : live
      ? { label: 'Live', dot: 'bg-[#ff2d3d] animate-live', text: 'text-[#ff5a66]' }
      : { label: 'Market open', dot: 'bg-up', text: 'text-up' }

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/75 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-4 px-4 sm:px-6">
        <Logo />

        <div className="mx-auto hidden min-w-0 flex-1 items-center justify-center gap-3 md:flex" aria-label="Season progress">
          <span className="eyebrow shrink-0">Season 2025</span>
          <div className="flex h-1.5 w-full max-w-xs gap-[3px]" aria-hidden="true">
            {Array.from({ length: totalRounds }, (_, i) => (
              <span
                key={i}
                className={`h-full flex-1 rounded-full ${i < round ? (i === round - 1 && live ? 'bg-[#ff2d3d]' : 'bg-white/70') : 'bg-white/10'}`}
              />
            ))}
          </div>
          <span className="num shrink-0 text-xs text-dim">
            R{round}/{totalRounds}
            {raceName && <span className="ml-2 hidden font-sans font-semibold text-ink lg:inline">{raceName}</span>}
          </span>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {data && (
            <span
              className={`hidden rounded-md border px-2 py-1 text-[0.65rem] font-bold uppercase tracking-widest xl:inline ${data === 'real' ? 'border-gold/30 text-gold' : 'border-line text-dim'}`}
              title={data === 'real' ? 'Actual 2025 results, fetched with FastF1' : 'A simulated 2025 season'}
            >
              {data === 'real' ? 'Real 2025 data' : 'Simulated season'}
            </span>
          )}
          {mode && (
            <span
              className="hidden rounded-md border border-line px-2 py-1 text-[0.65rem] font-bold uppercase tracking-widest text-dim sm:inline"
              title={mode === 'kafka' ? 'Streaming from the Kafka pipeline' : 'Demo mode: market built in-process, no Kafka broker'}
            >
              {mode === 'kafka' ? 'Kafka stream' : 'Demo mode'}
            </span>
          )}
          <span role="status" className={`flex items-center gap-2 text-xs font-bold uppercase tracking-widest ${status.text}`}>
            <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden="true" />
            {status.label}
          </span>
          <time className="num hidden text-xs text-faint lg:block" dateTime={now.toISOString()}>
            {now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </time>
        </div>
      </div>
    </header>
  )
}
