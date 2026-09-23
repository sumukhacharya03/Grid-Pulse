import { useEffect, useReducer } from 'react'
import { ApiError } from './apiError'
import { localServer } from './localServer'
import type { ServerMessage, SimStatus, Snapshot, Tick } from './types'

export type Connection = 'connecting' | 'open' | 'reconnecting'

export interface Flash {
  id: string
  up: boolean
}

interface State {
  connection: Connection
  snapshot: Snapshot | null
  ticks: Tick[]
  seen: Set<string>
  flashes: Record<string, Flash>
  /** Monotonic counter of live ticks, to trigger one-shot effects. */
  liveCount: number
  /** Date.now() of the last live tick; trading pauses while results stream in. */
  lastLiveAt: number
  /** Bumped whenever someone trades or joins, so leaderboards refresh. */
  gameEvents: number
}

type Action =
  | { type: 'connection'; value: Connection }
  | { type: 'message'; msg: ServerMessage }

function reducer(state: State, action: Action): State {
  if (action.type === 'connection') return { ...state, connection: action.value }
  const { msg } = action
  switch (msg.type) {
    case 'snapshot':
      return {
        ...state,
        snapshot: msg.data,
        ticks: msg.data.ticks,
        seen: new Set(msg.data.ticks.map((t) => t.id)),
        flashes: {},
      }
    case 'tick': {
      if (!state.snapshot || state.seen.has(msg.tick.id)) return state
      const seen = new Set(state.seen)
      seen.add(msg.tick.id)
      return {
        ...state,
        ticks: [...state.ticks, msg.tick],
        seen,
        flashes: { ...state.flashes, [msg.tick.driver_code]: { id: msg.tick.id, up: msg.tick.change_pct >= 0 } },
        liveCount: state.liveCount + 1,
        lastLiveAt: msg.tick.live ? Date.now() : state.lastLiveAt,
      }
    }
    case 'sim':
      if (!state.snapshot) return state
      return { ...state, snapshot: { ...state.snapshot, sim: msg.sim as SimStatus, next_race: msg.next_race } }
    case 'game':
      return { ...state, gameEvents: state.gameEvents + 1 }
  }
}

const initial: State = {
  connection: 'connecting', snapshot: null, ticks: [], seen: new Set(), flashes: {}, liveCount: 0, lastLiveAt: 0, gameEvents: 0,
}

/** The GitHub Pages build has no server: the market replays in the browser. */
export const STATIC = import.meta.env.VITE_STATIC === '1'

export function useMarket() {
  const [state, dispatch] = useReducer(reducer, initial)

  useEffect(() => {
    if (!STATIC) return
    let unsubscribe = () => {}
    let disposed = false
    localServer()
      .ready.then(() => {
        if (disposed) return
        dispatch({ type: 'connection', value: 'open' })
        unsubscribe = localServer().subscribe((msg) => dispatch({ type: 'message', msg }))
      })
      .catch(() => dispatch({ type: 'connection', value: 'reconnecting' }))
    return () => {
      disposed = true
      unsubscribe()
    }
  }, [])

  useEffect(() => {
    if (STATIC) return
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let attempt = 0
    let disposed = false

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${proto}://${location.host}/ws`)
      socket.onopen = () => {
        attempt = 0
        dispatch({ type: 'connection', value: 'open' })
      }
      socket.onmessage = (e) => {
        try {
          dispatch({ type: 'message', msg: JSON.parse(e.data) as ServerMessage })
        } catch {
          /* ignore malformed frames */
        }
      }
      socket.onclose = () => {
        if (disposed) return
        dispatch({ type: 'connection', value: 'reconnecting' })
        const delay = Math.min(10_000, 800 * 2 ** attempt++)
        retry = setTimeout(connect, delay)
      }
    }
    connect()
    return () => {
      disposed = true
      clearTimeout(retry)
      socket?.close()
    }
  }, [])

  return state
}

export async function api<T = unknown>(path: string, body?: unknown, init: RequestInit = {}): Promise<T> {
  if (STATIC) {
    const headers = (init.headers ?? {}) as Record<string, string>
    return (await localServer().request(init.method ?? 'POST', path, body, headers)) as T
  }
  const res = await fetch(path, {
    ...init,
    method: init.method ?? 'POST',
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

export { ApiError }
