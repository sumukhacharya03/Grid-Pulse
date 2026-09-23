import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './useMarket'

export interface Holding {
  driver_code: string
  units: number
  cost: number
  value: number
  pnl_pct: number
}

export interface Portfolio {
  player: { id: number; name: string }
  epoch: number
  starting_cash: number
  cash: number
  holdings: Holding[]
  value: number
  return_pct: number
  rank: number | null
  players: number
  trades: { driver_code: string; side: 'buy' | 'sell'; amount: number; price: number; ts: number }[]
}

export interface Leaderboard {
  players: number
  me: number | null
  starting_cash: number
  top: { rank: number; id: number; name: string; value: number; return_pct: number; top_holding: string | null }[]
}

const TOKEN_KEY = 'gp.token'

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable: the account lasts for this tab only */
  }
}

/** Your account lives in this browser: the server hands out a token on join. */
export function useGame(epoch: number | null, gameEvents: number, simRunning: boolean) {
  const [token, setToken] = useState<string | null>(readToken)
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [board, setBoard] = useState<Leaderboard | null>(null)
  const tokenRef = useRef(token)

  const headers = useCallback((): Record<string, string> => (tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}), [])

  const refreshMe = useCallback(async () => {
    if (!tokenRef.current) return  // signed out: leave() and join() manage the state
    try {
      setPortfolio(await api<Portfolio>('/api/game/me', undefined, { method: 'GET', headers: headers() }))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        // The server no longer knows this account (its data was wiped).
        writeToken(null)
        tokenRef.current = null
        setToken(null)
        setPortfolio(null)
      }
    }
  }, [headers])

  const refreshBoard = useCallback(async () => {
    try {
      setBoard(await api<Leaderboard>('/api/game/leaderboard', undefined, { method: 'GET', headers: headers() }))
    } catch {
      /* market not ready yet */
    }
  }, [headers])

  // New market season (epoch) or account: reload everything.
  useEffect(() => {
    if (epoch == null) return
    // oxlint-disable-next-line react/set-state-in-effect -- async fetch: state is only set once the request resolves
    refreshMe()
    refreshBoard()
  }, [epoch, token, refreshMe, refreshBoard])

  // Someone traded or joined: refresh the board (debounced), and ours after a weekend.
  useEffect(() => {
    if (epoch == null || !gameEvents) return
    const id = setTimeout(refreshBoard, 600)
    return () => clearTimeout(id)
  }, [gameEvents, epoch, refreshBoard])

  useEffect(() => {
    if (epoch == null || simRunning) return
    // oxlint-disable-next-line react/set-state-in-effect -- async fetch: state is only set once the request resolves
    refreshMe()
    refreshBoard()
  }, [simRunning, epoch, refreshMe, refreshBoard])

  // Values drift with every tick, so re-rank now and then while the tab is open.
  useEffect(() => {
    const id = setInterval(() => document.visibilityState === 'visible' && refreshBoard(), 15_000)
    return () => clearInterval(id)
  }, [refreshBoard])

  const join = useCallback(async (name: string) => {
    const res = await api<{ token: string; portfolio: Portfolio }>('/api/game/join', { name })
    writeToken(res.token)
    tokenRef.current = res.token
    setToken(res.token)
    setPortfolio(res.portfolio)
  }, [])

  const trade = useCallback(
    async (driver: string, side: 'buy' | 'sell', amount: number | null) => {
      const next = await api<Portfolio>('/api/game/trade', { driver, side, amount }, { headers: headers() })
      setPortfolio(next)
      return next
    },
    [headers],
  )

  const leave = useCallback(() => {
    writeToken(null)
    tokenRef.current = null
    setToken(null)
    setPortfolio(null)
  }, [])

  return { joined: !!token && !!portfolio, portfolio, board, join, trade, leave }
}

export type GameApi = ReturnType<typeof useGame>

/** Live value of a holding at the latest streamed price. */
export function liveValue(h: Holding, prices: Record<string, number>): number {
  const p = prices[h.driver_code]
  return p ? h.units * p : h.value
}

/** Trading pauses while a weekend is running and for a few seconds after the last live result. */
export const LIVE_QUIET_MS = 8000
