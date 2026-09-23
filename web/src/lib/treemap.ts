export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

function worst(row: number[], side: number): number {
  const sum = row.reduce((a, b) => a + b, 0)
  const max = Math.max(...row)
  const min = Math.min(...row)
  return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min))
}

/** Squarified treemap (Bruls et al.): tiles keep aspect ratios near 1. */
export function squarify<T>(items: T[], weight: (item: T) => number, bounds: Rect): { item: T; rect: Rect }[] {
  const sorted = [...items].filter((i) => weight(i) > 0).sort((a, b) => weight(b) - weight(a))
  const total = sorted.reduce((s, i) => s + weight(i), 0)
  if (!total || bounds.w <= 0 || bounds.h <= 0) return []
  const scale = (bounds.w * bounds.h) / total
  const areas = sorted.map((i) => weight(i) * scale)
  const out: { item: T; rect: Rect }[] = []
  let rect = { ...bounds }
  let row: number[] = []
  let start = 0

  const place = () => {
    const sum = row.reduce((a, b) => a + b, 0)
    if (rect.w >= rect.h) {
      const colW = sum / rect.h
      let y = rect.y
      row.forEach((a, k) => {
        const h = a / colW
        out.push({ item: sorted[start + k], rect: { x: rect.x, y, w: colW, h } })
        y += h
      })
      rect = { x: rect.x + colW, y: rect.y, w: rect.w - colW, h: rect.h }
    } else {
      const rowH = sum / rect.w
      let x = rect.x
      row.forEach((a, k) => {
        const w = a / rowH
        out.push({ item: sorted[start + k], rect: { x, y: rect.y, w, h: rowH } })
        x += w
      })
      rect = { x: rect.x, y: rect.y + rowH, w: rect.w, h: rect.h - rowH }
    }
    start += row.length
    row = []
  }

  let i = 0
  while (i < areas.length) {
    const side = Math.min(rect.w, rect.h)
    const candidate = [...row, areas[i]]
    if (!row.length || worst(candidate, side) <= worst(row, side)) {
      row = candidate
      i++
    } else {
      place()
    }
  }
  if (row.length) place()
  return out
}
