import {
  BaselineSeries,
  ColorType,
  CrosshairMode,
  createChart,
  createSeriesMarkers,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { money, withAlpha } from '../lib/format'
import type { Point } from '../lib/market'

export interface ChartMarker {
  time: number
  label: string
  color: string
  shape?: 'circle' | 'arrowUp' | 'arrowDown' | 'square'
  above?: boolean
}

interface Props {
  data: Point[]
  /** Values above this render green, below red. */
  base: number
  height?: number | string
  markers?: ChartMarker[]
  format?: (v: number) => string
  /** Line colour for the "up" side; defaults to the gain colour. */
  upColor?: string
  label: string
}

const UP = '#1fe08f'
const DOWN = '#ff4d6a'

export default function PriceChart({ data, base, height = 280, markers = [], format = money, upColor = UP, label }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const series = useRef<ISeriesApi<'Baseline'> | null>(null)
  const markerApi = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const count = useRef(0)
  // Options at creation time; later changes are applied by the effect below.
  const initial = useRef({ base, upColor, format })

  useEffect(() => {
    if (!host.current) return
    const { base, upColor, format } = initial.current
    const c = createChart(host.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#5d6678',
        fontFamily: "'JetBrains Mono Variable', ui-monospace, monospace",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: 'rgba(255,255,255,0.045)' },
      },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: 'rgba(255,255,255,0.25)', style: LineStyle.Dashed, labelBackgroundColor: '#161b24' },
        horzLine: { color: 'rgba(255,255,255,0.25)', style: LineStyle.Dashed, labelBackgroundColor: '#161b24' },
      },
      handleScroll: { vertTouchDrag: false },
    })
    const s = c.addSeries(BaselineSeries, {
      baseValue: { type: 'price', price: base },
      topLineColor: upColor,
      topFillColor1: withAlpha(upColor, 0.28),
      topFillColor2: withAlpha(upColor, 0.02),
      bottomLineColor: DOWN,
      bottomFillColor1: withAlpha(DOWN, 0.02),
      bottomFillColor2: withAlpha(DOWN, 0.28),
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerRadius: 5,
      crosshairMarkerBorderColor: '#06070a',
      priceFormat: { type: 'custom', formatter: format, tickmarksFormatter: (prices: number[]) => prices.map(format), minMove: 0.01 },
    })
    s.createPriceLine({ price: base, color: 'rgba(255,255,255,0.22)', lineStyle: LineStyle.Dotted, lineWidth: 1, axisLabelVisible: false, title: '' })
    chart.current = c
    series.current = s
    markerApi.current = createSeriesMarkers(s, [])
    return () => {
      c.remove()
      chart.current = null
      series.current = null
      count.current = 0
    }
  }, [])

  useEffect(() => {
    series.current?.applyOptions({
      baseValue: { type: 'price', price: base },
      topLineColor: upColor,
      topFillColor1: withAlpha(upColor, 0.28),
      topFillColor2: withAlpha(upColor, 0.02),
      priceFormat: { type: 'custom', formatter: format, tickmarksFormatter: (prices: number[]) => prices.map(format), minMove: 0.01 },
    })
  }, [base, upColor, format])

  useEffect(() => {
    if (!series.current || !chart.current) return
    series.current.setData(data.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })))
    // Refit on first load or when a whole new history arrives; otherwise
    // keep the user's zoom while live points stream in.
    if (count.current === 0 || Math.abs(data.length - count.current) > 25) chart.current.timeScale().fitContent()
    count.current = data.length
  }, [data])

  useEffect(() => {
    const m: SeriesMarker<Time>[] = markers
      .map((mk) => ({
        time: mk.time as UTCTimestamp,
        position: mk.above === false ? ('belowBar' as const) : ('aboveBar' as const),
        shape: mk.shape ?? 'circle',
        color: mk.color,
        text: mk.label,
        size: 0.6,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number))
    markerApi.current?.setMarkers(m)
  }, [markers])

  return <div ref={host} role="img" aria-label={label} style={{ height }} className="w-full" />
}
