/** Driver photo URL (the Pages build is served from /Grid-Pulse/, not /). */
export function driverImg(code: string): string {
  return `${import.meta.env.BASE_URL}drivers/${code}.jpg`
}

export function money(value: number, digits = 2): string {
  const abs = Math.abs(value)
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(digits)}B`
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(digits)}M`
  if (abs >= 1e3) return `$${(value / 1e3).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export function pct(value: number, digits = 2): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±'
  return `${sign}${Math.abs(value).toFixed(digits)}%`
}

export function arrow(value: number): string {
  return value > 0.0001 ? '▲' : value < -0.0001 ? '▼' : '■'
}

export function trendClass(value: number): string {
  return value > 0.0001 ? 'text-up' : value < -0.0001 ? 'text-down' : 'text-dim'
}

export function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

export function sessionShort(key: string): string {
  return (
    {
      practice1: 'FP1',
      practice2: 'FP2',
      practice3: 'FP3',
      sprint_qualifying: 'SQ',
      sprint_race: 'SPR',
      qualifying: 'Q',
      race: 'RACE',
    } as Record<string, string>
  )[key] ?? key
}

export function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgb(${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255} / ${alpha})`
}
