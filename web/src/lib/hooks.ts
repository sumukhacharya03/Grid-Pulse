import { useEffect, useRef, useState } from 'react'

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const mq = matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setReduced(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduced
}

/** Eases a number towards `target` so price changes roll instead of jump. */
export function useTweened(target: number, duration = 700): number {
  const reduced = useReducedMotion()
  const [value, setValue] = useState(target)
  const from = useRef(target)
  const current = useRef(target)

  useEffect(() => {
    if (reduced || !Number.isFinite(target)) {
      current.current = target
      return
    }
    from.current = current.current
    const start = performance.now()
    let raf = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      current.current = from.current + (target - from.current) * eased
      setValue(current.current)
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, reduced])

  return reduced || !Number.isFinite(target) ? target : value
}

export function useNow(interval = 1000): Date {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), interval)
    return () => clearInterval(id)
  }, [interval])
  return now
}
