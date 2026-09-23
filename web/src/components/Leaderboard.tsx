import type { GameApi } from '../lib/game'
import { money } from '../lib/format'
import type { MarketView } from '../lib/market'
import { Change } from './ui'

export default function Leaderboard({ game, market }: { game: GameApi; market: MarketView }) {
  const board = game.board
  const meId = game.portfolio?.player.id
  const meOutside = board && board.me && board.me > board.top.length

  return (
    <section className="panel flex h-full flex-col p-5" aria-labelledby="leaderboard-title">
      <div className="flex items-baseline justify-between">
        <h2 id="leaderboard-title" className="text-xl font-black uppercase italic tracking-tight">Leaderboard</h2>
        <span className="text-xs text-faint">{board ? `${board.players} player${board.players === 1 ? '' : 's'}` : ''}</span>
      </div>
      {!board || board.top.length === 0 ? (
        <p className="flex flex-1 items-center justify-center py-8 text-center text-sm text-faint">No players yet. Be the first on the board.</p>
      ) : (
        <ol className="mt-3 space-y-1">
          {board.top.map((row) => {
            const mine = row.id === meId
            const top = row.top_holding ? market.byCode[row.top_holding] : undefined
            return (
              <li
                key={row.id}
                aria-current={mine ? 'true' : undefined}
                className={`flex items-center gap-3 rounded-lg px-2.5 py-1.5 text-sm ${mine ? 'bg-gold/10 ring-1 ring-gold/30' : ''}`}
              >
                <span className={`num w-6 text-right font-bold ${row.rank === 1 ? 'text-gold' : row.rank <= 3 ? 'text-ink' : 'text-faint'}`}>{row.rank}</span>
                <span className="min-w-0 flex-1 truncate font-semibold">
                  {row.name}
                  {mine && <span className="ml-1.5 text-xs font-normal text-gold">you</span>}
                </span>
                {top && (
                  <span className="hidden items-center gap-1 text-xs text-faint sm:flex" title={`Biggest holding: ${top.name}`}>
                    <span className="h-2.5 w-[3px] rounded-full" style={{ background: top.color }} aria-hidden="true" />
                    {top.code}
                  </span>
                )}
                <span className="num w-20 text-right text-dim">{money(row.value)}</span>
                <Change value={row.return_pct} className="w-20 justify-end text-xs" />
              </li>
            )
          })}
        </ol>
      )}
      {meOutside && <p className="mt-2 border-t border-line pt-2 text-sm text-dim">You're <span className="num font-semibold text-ink">#{board!.me}</span> of {board!.players}</p>}
      {board && board.players < 10 && (
        <p className="mt-auto pt-4 text-xs text-faint">
          Everyone on this server trades the same market. Share the link to challenge friends.
        </p>
      )}
    </section>
  )
}
