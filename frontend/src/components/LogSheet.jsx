import { useMemo } from 'react'
import { formatDate, formatHoursMinutes } from '../lib/format.js'

const STATUS_ROW_INDEX = {
  off_duty: 0,
  sleeper_berth: 1,
  driving: 2,
  on_duty_not_driving: 3,
}

const STATUS_ROW_LABELS = [
  '1. Off Duty',
  '2. Sleeper Berth',
  '3. Driving',
  '4. On Duty',
]

const STATUS_ROW_COLORS = [
  '#94a3b8',
  '#6366f1',
  '#f97316',
  '#0ea5e9',
]

const VB_W = 1100
const VB_H = 800

const GRID_X = 170
const GRID_Y = 240
const GRID_HOURS = 24
const HOUR_W = 36 // (24 × 36 = 864) → grid spans 864
const ROW_H = 36
const ROW_COUNT = 4
const GRID_W = GRID_HOURS * HOUR_W
const GRID_H = ROW_COUNT * ROW_H
const TOTAL_COL_X = GRID_X + GRID_W + 8
const TOTAL_COL_W = 60

const REMARKS_Y = GRID_Y + GRID_H + 110

function hoursToX(h) {
  return GRID_X + (Math.max(0, Math.min(GRID_HOURS, h)) / GRID_HOURS) * GRID_W
}

function rowCenter(statusIndex) {
  return GRID_Y + statusIndex * ROW_H + ROW_H / 2
}

function HourTicks() {
  const ticks = []
  for (let h = 0; h <= GRID_HOURS; h += 1) {
    const x = GRID_X + h * HOUR_W
    ticks.push(
      <line
        key={`tick-${h}`}
        x1={x}
        y1={GRID_Y}
        x2={x}
        y2={GRID_Y + GRID_H}
        stroke={h % 1 === 0 ? '#475569' : '#cbd5e1'}
        strokeWidth={h % 6 === 0 ? 1.2 : 0.6}
      />,
    )
    // Sub-quarter ticks
    if (h < GRID_HOURS) {
      for (let q = 1; q < 4; q += 1) {
        const qx = x + (q * HOUR_W) / 4
        ticks.push(
          <line
            key={`q-${h}-${q}`}
            x1={qx}
            y1={GRID_Y + 4}
            x2={qx}
            y2={GRID_Y + GRID_H - 4}
            stroke="#cbd5e1"
            strokeWidth={0.4}
          />,
        )
      }
    }
  }
  return <g>{ticks}</g>
}

function HourLabels() {
  const labels = []
  for (let h = 0; h <= GRID_HOURS; h += 1) {
    const x = GRID_X + h * HOUR_W
    let text
    if (h === 0 || h === 24) text = 'Mid-\nnight'
    else if (h === 12) text = 'Noon'
    else text = String(h)
    const lines = text.split('\n')
    lines.forEach((line, i) => {
      labels.push(
        <text
          key={`lbl-${h}-${i}`}
          x={x}
          y={GRID_Y - 18 + i * 11}
          textAnchor="middle"
          fontSize={9.5}
          fontWeight={500}
          fill="#334155"
        >
          {line}
        </text>,
      )
    })
  }
  return <g>{labels}</g>
}

function RowDividers() {
  const lines = []
  for (let r = 0; r <= ROW_COUNT; r += 1) {
    const y = GRID_Y + r * ROW_H
    lines.push(
      <line
        key={`row-${r}`}
        x1={GRID_X}
        y1={y}
        x2={GRID_X + GRID_W}
        y2={y}
        stroke="#0f172a"
        strokeWidth={r === 0 || r === ROW_COUNT ? 1.5 : 1}
      />,
    )
  }
  return <g>{lines}</g>
}

function StatusLine({ entries }) {
  // Build a polyline that hops across the grid through the row for each entry.
  const points = useMemo(() => {
    const pts = []
    let prevRow = null
    for (const entry of entries) {
      const row = STATUS_ROW_INDEX[entry.status]
      if (row == null) continue
      const x1 = hoursToX(entry.start_hours)
      const x2 = hoursToX(entry.end_hours)
      const y = rowCenter(row)
      if (prevRow != null && prevRow !== row) {
        // Vertical jump at x1 from prev row to new row
        const prevY = rowCenter(prevRow)
        pts.push([x1, prevY])
        pts.push([x1, y])
      } else if (pts.length === 0) {
        pts.push([x1, y])
      }
      pts.push([x1, y])
      pts.push([x2, y])
      prevRow = row
    }
    return pts
  }, [entries])

  if (points.length === 0) return null

  const dStr = points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(' ')

  return (
    <g>
      <path
        d={dStr}
        fill="none"
        stroke="#0f172a"
        strokeWidth={2.4}
        strokeLinejoin="miter"
        strokeLinecap="butt"
      />
      <path
        d={dStr}
        fill="none"
        stroke="#f97316"
        strokeWidth={1.2}
        strokeLinejoin="miter"
        strokeLinecap="butt"
        opacity={0.9}
      />
    </g>
  )
}

function RemarksAnnotations({ entries }) {
  // Build one annotation per duty-status change (skip the implicit pre-trip
  // off-duty padding so we don't draw a tick at midnight on every page).
  const changes = []
  let prevStatus = null
  let prevDesc = null
  for (const entry of entries) {
    if (entry.status !== prevStatus || entry.description !== prevDesc) {
      if (entry.description) {
        changes.push({
          x: hoursToX(entry.start_hours),
          label: entry.description,
          time: formatHourOfDay(entry.start_hours),
        })
      }
      prevStatus = entry.status
      prevDesc = entry.description
    }
  }
  // Collapse adjacent identical labels that land at nearly the same x.
  const dedup = []
  for (const c of changes) {
    const last = dedup[dedup.length - 1]
    if (!last || last.label !== c.label || Math.abs(last.x - c.x) > 8) {
      dedup.push(c)
    }
  }

  // FMCSA paper-log style: solid vertical tick drops from the bottom of the
  // 24-hour grid, then kinks 45° down-and-to-the-right. The remark sits along
  // that oblique — description above the line, time below.
  const VERTICAL_DROP = 22
  const OBLIQUE_LEN = 70
  const OBLIQUE_DELTA = OBLIQUE_LEN * Math.SQRT1_2 // ≈ 49.5

  return (
    <g>
      {dedup.map((c, i) => {
        const elbowY = GRID_Y + GRID_H + VERTICAL_DROP
        const tipX = c.x - OBLIQUE_DELTA
        const tipY = elbowY + OBLIQUE_DELTA
        const rot = `rotate(-45, ${c.x}, ${elbowY})`
        return (
          <g key={`rem-${i}`}>
            <line
              x1={c.x} y1={GRID_Y + GRID_H}
              x2={c.x} y2={elbowY}
              stroke="#0f172a" strokeWidth={0.9}
            />
            <line
              x1={c.x} y1={elbowY}
              x2={tipX} y2={tipY}
              stroke="#0f172a" strokeWidth={0.9}
            />
            <text
              x={c.x - 6} y={elbowY - 3}
              transform={rot}
              fontSize={9.5} fontWeight={500}
              fill="#0f172a" textAnchor="end"
            >
              {c.label}
            </text>
            <text
              x={c.x - 6} y={elbowY + 11}
              transform={rot}
              fontSize={8.5}
              fill="#475569" textAnchor="end"
            >
              {c.time}
            </text>
          </g>
        )
      })}
    </g>
  )
}

function formatHourOfDay(decimalHours) {
  const h = Math.floor(decimalHours)
  const m = Math.round((decimalHours - h) * 60)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function HeaderFields({ day, dayIndex, totalDays, carrier, mainOffice, homeTerminal, truckNumbers }) {
  const dateParts = (day.date || '').split('-')
  const yyyy = dateParts[0] || ''
  const mm = dateParts[1] || ''
  const dd = dateParts[2] || ''
  return (
    <g fontFamily="Inter, system-ui, sans-serif">
      <text x={28} y={28} fontSize={22} fontWeight={700} fill="#0f172a">
        Driver's Daily Log
      </text>
      <text x={28} y={48} fontSize={10} fill="#64748b">
        (24 hours)
      </text>
      <text x={28} y={64} fontSize={10} fill="#64748b">
        Day {dayIndex + 1} of {totalDays} · {formatDate(day.date)}
      </text>

      {/* Date stamps */}
      <g transform={`translate(${VB_W - 480}, 18)`}>
        <text x={0} y={12} fontSize={10} fill="#64748b">
          Original — File at home terminal
        </text>
        <text x={0} y={26} fontSize={10} fill="#64748b">
          Duplicate — Driver retains in possession for 8 days
        </text>

        <g transform="translate(0, 42)">
          <text x={0} y={12} fontSize={10} fill="#0f172a">
            {mm || '__'}
          </text>
          <line x1={-2} y1={16} x2={36} y2={16} stroke="#0f172a" />
          <text x={16} y={28} fontSize={8} fill="#64748b" textAnchor="middle">
            (month)
          </text>

          <text x={50} y={12} fontSize={10} fill="#0f172a">
            {dd || '__'}
          </text>
          <line x1={48} y1={16} x2={86} y2={16} stroke="#0f172a" />
          <text x={67} y={28} fontSize={8} fill="#64748b" textAnchor="middle">
            (day)
          </text>

          <text x={100} y={12} fontSize={10} fill="#0f172a">
            {yyyy || '____'}
          </text>
          <line x1={98} y1={16} x2={156} y2={16} stroke="#0f172a" />
          <text x={127} y={28} fontSize={8} fill="#64748b" textAnchor="middle">
            (year)
          </text>

          <text x={186} y={12} fontSize={10} fontWeight={500} fill="#0f172a">
            {(day.miles_driven ?? 0).toFixed(0)}
          </text>
          <line x1={172} y1={16} x2={266} y2={16} stroke="#0f172a" />
          <text x={219} y={28} fontSize={8} fill="#64748b" textAnchor="middle">
            (total miles driving today)
          </text>
        </g>
      </g>

      {/* From / To */}
      <g transform="translate(28, 88)">
        <text x={0} y={12} fontSize={10} fontWeight={600} fill="#0f172a">
          From:
        </text>
        <text x={40} y={12} fontSize={10} fill="#0f172a">
          {day.starting_location || '—'}
        </text>
        <line x1={38} y1={16} x2={500} y2={16} stroke="#0f172a" />

        <text x={520} y={12} fontSize={10} fontWeight={600} fill="#0f172a">
          To:
        </text>
        <text x={552} y={12} fontSize={10} fill="#0f172a">
          {day.ending_location || '—'}
        </text>
        <line x1={550} y1={16} x2={1000} y2={16} stroke="#0f172a" />
      </g>

      {/* Carrier rows */}
      <g transform="translate(28, 116)">
        <text x={0} y={12} fontSize={9} fill="#64748b">
          Name of carrier or carriers
        </text>
        <text x={0} y={28} fontSize={10} fontWeight={500} fill="#0f172a">
          {carrier}
        </text>
        <line x1={0} y1={32} x2={500} y2={32} stroke="#0f172a" />

        <text x={520} y={12} fontSize={9} fill="#64748b">
          Main office address
        </text>
        <text x={520} y={28} fontSize={10} fontWeight={500} fill="#0f172a">
          {mainOffice}
        </text>
        <line x1={520} y1={32} x2={1000} y2={32} stroke="#0f172a" />
      </g>

      <g transform="translate(28, 156)">
        <text x={0} y={12} fontSize={9} fill="#64748b">
          Truck/Tractor & trailer numbers
        </text>
        <text x={0} y={28} fontSize={10} fontWeight={500} fill="#0f172a">
          {truckNumbers}
        </text>
        <line x1={0} y1={32} x2={500} y2={32} stroke="#0f172a" />

        <text x={520} y={12} fontSize={9} fill="#64748b">
          Home terminal address
        </text>
        <text x={520} y={28} fontSize={10} fontWeight={500} fill="#0f172a">
          {homeTerminal}
        </text>
        <line x1={520} y1={32} x2={1000} y2={32} stroke="#0f172a" />
      </g>
    </g>
  )
}

export default function LogSheet({
  day,
  dayIndex,
  totalDays,
  carrier = 'Spotter ELD Demo Carrier',
  mainOffice = '—',
  homeTerminal = '—',
  truckNumbers = '—',
}) {
  if (!day) return null
  const totals = day.totals || {}
  const totalsArr = [
    { key: 'off_duty', minutes: totals.off_duty || 0 },
    { key: 'sleeper_berth', minutes: totals.sleeper_berth || 0 },
    { key: 'driving', minutes: totals.driving || 0 },
    { key: 'on_duty_not_driving', minutes: totals.on_duty_not_driving || 0 },
  ]
  const grandTotal = totalsArr.reduce((a, b) => a + b.minutes, 0)

  return (
    <div className="logsheet">
      <svg
        className="logsheet__svg"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label={`Daily log for ${day.date}`}
      >
        <rect x={0} y={0} width={VB_W} height={VB_H} fill="#ffffff" />

        <HeaderFields
          day={day}
          dayIndex={dayIndex}
          totalDays={totalDays}
          carrier={carrier}
          mainOffice={mainOffice}
          homeTerminal={homeTerminal}
          truckNumbers={truckNumbers}
        />

        {/* Status row labels */}
        {STATUS_ROW_LABELS.map((label, i) => (
          <g key={label}>
            <rect
              x={GRID_X - 160}
              y={GRID_Y + i * ROW_H}
              width={156}
              height={ROW_H}
              fill={i % 2 === 0 ? '#f8fafc' : '#ffffff'}
              stroke="#cbd5e1"
              strokeWidth={0.5}
            />
            <circle
              cx={GRID_X - 148}
              cy={GRID_Y + i * ROW_H + ROW_H / 2}
              r={4}
              fill={STATUS_ROW_COLORS[i]}
            />
            <text
              x={GRID_X - 138}
              y={GRID_Y + i * ROW_H + ROW_H / 2 + 4}
              fontSize={10.5}
              fontWeight={500}
              fill="#0f172a"
            >
              {label}
            </text>
          </g>
        ))}

        {/* Grid base */}
        <rect
          x={GRID_X}
          y={GRID_Y}
          width={GRID_W}
          height={GRID_H}
          fill="#ffffff"
          stroke="#0f172a"
          strokeWidth={1.5}
        />
        <HourTicks />
        <HourLabels />
        <RowDividers />

        {/* The actual duty-status line */}
        <StatusLine entries={day.entries || []} />

        {/* Totals column */}
        <g>
          <rect
            x={TOTAL_COL_X}
            y={GRID_Y - 22}
            width={TOTAL_COL_W}
            height={20}
            fill="#0f172a"
          />
          <text
            x={TOTAL_COL_X + TOTAL_COL_W / 2}
            y={GRID_Y - 8}
            textAnchor="middle"
            fontSize={10}
            fontWeight={600}
            fill="#ffffff"
          >
            Total Hrs
          </text>
          {totalsArr.map((t, i) => (
            <g key={t.key}>
              <rect
                x={TOTAL_COL_X}
                y={GRID_Y + i * ROW_H}
                width={TOTAL_COL_W}
                height={ROW_H}
                fill={i % 2 === 0 ? '#f8fafc' : '#ffffff'}
                stroke="#0f172a"
                strokeWidth={0.7}
              />
              <text
                x={TOTAL_COL_X + TOTAL_COL_W / 2}
                y={GRID_Y + i * ROW_H + ROW_H / 2 + 4}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="#0f172a"
                fontFamily="JetBrains Mono, ui-monospace, monospace"
              >
                {formatHoursMinutes(t.minutes)}
              </text>
            </g>
          ))}
          <rect
            x={TOTAL_COL_X}
            y={GRID_Y + GRID_H + 2}
            width={TOTAL_COL_W}
            height={20}
            fill="#0f172a"
          />
          <text
            x={TOTAL_COL_X + TOTAL_COL_W / 2}
            y={GRID_Y + GRID_H + 16}
            textAnchor="middle"
            fontSize={11}
            fontWeight={700}
            fill="#ffffff"
            fontFamily="JetBrains Mono, ui-monospace, monospace"
          >
            = {formatHoursMinutes(grandTotal)}
          </text>
        </g>

        {/* Remarks header */}
        <g transform={`translate(28, ${GRID_Y + GRID_H + 30})`}>
          <text x={0} y={0} fontSize={11} fontWeight={700} fill="#0f172a">
            Remarks
          </text>
          <line x1={0} y1={6} x2={1000} y2={6} stroke="#0f172a" />
        </g>

        <RemarksAnnotations entries={day.entries || []} />

        {/* Bottom: shipping docs / signature */}
        <g transform={`translate(28, ${VB_H - 130})`}>
          <text x={0} y={0} fontSize={9} fill="#64748b">
            Shipping Documents
          </text>
          <line x1={0} y1={20} x2={500} y2={20} stroke="#0f172a" />
          <text x={0} y={36} fontSize={9} fill="#64748b">
            Pro or Shipping No.
          </text>
          <line x1={0} y1={56} x2={500} y2={56} stroke="#0f172a" />

          <text x={520} y={0} fontSize={9} fill="#64748b">
            Driver's signature (in full)
          </text>
          <line x1={520} y1={20} x2={1000} y2={20} stroke="#0f172a" />
          <text x={520} y={36} fontSize={9} fontStyle="italic" fill="#64748b">
            I certify that these entries are true and correct.
          </text>
          <line x1={520} y1={56} x2={1000} y2={56} stroke="#0f172a" />
        </g>

        <g transform={`translate(28, ${VB_H - 50})`}>
          <text x={0} y={0} fontSize={9} fill="#94a3b8">
            Auto-generated by Spotter ELD trip planner · Property-carrying driver · 70 hr / 8 day cycle
          </text>
        </g>
      </svg>

      <div className="logsheet-totals">
        {totalsArr.map((t, i) => (
          <span key={t.key}>
            <span
              className="logsheet-totals__dot"
              style={{ background: STATUS_ROW_COLORS[i] }}
            />
            <strong>{STATUS_ROW_LABELS[i].replace(/^\d\.\s*/, '')}:</strong>{' '}
            {formatHoursMinutes(t.minutes)}
          </span>
        ))}
        <span style={{ marginLeft: 'auto' }}>
          <strong>Miles today:</strong> {(day.miles_driven ?? 0).toFixed(1)}
        </span>
      </div>
    </div>
  )
}
