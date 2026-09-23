import type { Mode } from '../lib/types'

interface Props {
  mode: Mode
  data: 'real' | 'simulated'
  ticks: number
  liveTicks: number
}

const STAGES = [
  { title: 'Produce', items: ['producer1 · baseline values', 'producer2 · historical sessions', 'producer3 · live sessions'] },
  { title: 'Kafka topics', items: ['drivers-baseline-value', 'historical-performance-*', 'realtime-performance-*'] },
  { title: 'Price', items: ['calculation_service · batch epoch', 'realtime_service · live stream'] },
  { title: 'Serve', items: ['market-ticks (event log)', 'driver-stock-values', 'dashboard · WebSocket'] },
]

const RULES: [string, string][] = [
  ['Expectation', 'The market expects each driver to finish where their value ranks. Every place above or below that moves the price.'],
  ['Qualifying', '±0.12% per place vs expectation, +0.6% for pole, +0.2% for the rest of the top three.'],
  ['Race', '±0.25% per place vs expectation, +0.06% per point, +1% for the win, +0.4% for a podium, +0.2% for fastest lap.'],
  ['Retirements', 'Crash −2.5%, collision −1.5%, mechanical −1%. Sprints count 40%, practice is a small signal.'],
]

export default function UnderTheHood({ mode, data, ticks, liveTicks }: Props) {
  return (
    <section className="panel p-5 sm:p-6" aria-labelledby="uth-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="uth-title" className="text-xl font-black uppercase italic tracking-tight">Under the hood</h2>
        <p className="num text-xs text-faint">
          {ticks.toLocaleString()} price moves · {liveTicks.toLocaleString()} live · {data === 'real' ? 'real 2025 results' : 'simulated season'} ·{' '}
          {mode === 'kafka' ? 'streamed from Kafka' : mode === 'static' ? 'browser edition, priced ahead by the Python engine' : 'demo mode, priced in-process'}
        </p>
      </div>

      <ol className="mt-5 grid gap-3 md:grid-cols-4" aria-label="Data pipeline">
        {STAGES.map((stage, i) => (
          <li key={stage.title} className="relative rounded-xl border border-line bg-black/25 p-4">
            <div className="flex items-center gap-2">
              <span className="num grid h-6 w-6 place-items-center rounded-md bg-brand/20 text-xs font-bold text-[#ff6a5f]">{i + 1}</span>
              <span className="font-bold uppercase tracking-wider">{stage.title}</span>
            </div>
            <ul className="mt-2.5 space-y-1">
              {stage.items.map((item) => (
                <li key={item} className="num truncate text-[0.72rem] text-dim" title={item}>{item}</li>
              ))}
            </ul>
            {i < STAGES.length - 1 && (
              <span aria-hidden="true" className="absolute -right-2.5 top-1/2 z-10 hidden h-5 w-5 -translate-y-1/2 place-items-center rounded-full border border-line bg-surface text-[0.6rem] text-faint md:grid">
                ▶
              </span>
            )}
          </li>
        ))}
      </ol>

      <dl className="mt-5 grid gap-x-8 gap-y-3 md:grid-cols-2">
        {RULES.map(([term, text]) => (
          <div key={term}>
            <dt className="text-sm font-bold">{term}</dt>
            <dd className="text-sm text-dim">{text}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
