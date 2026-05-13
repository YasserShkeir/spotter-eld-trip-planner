import { formatDateTime, formatHoursMinutes, formatMiles, STOP_COLORS } from '../lib/format.js'

const KIND_LABEL = {
  origin: 'Origin',
  pickup: 'Pickup',
  dropoff: 'Drop-off',
  fuel: 'Fuel stop',
  rest: '10-hour rest',
  break: '30-min break',
  restart: '34-hour restart',
}

export default function StopsList({ stops = [] }) {
  if (!stops.length) return null
  return (
    <div className="card">
      <div className="card__header">
        <h2 className="card__title">Stops & rest schedule</h2>
        <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {stops.length} stop{stops.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="card__body card__body--flush">
        <div className="stops-list">
          {stops.map((stop, idx) => (
            <div className="stops-list__item" key={`${stop.kind}-${idx}-${stop.arrival}`}>
              <span
                className="stops-list__dot"
                style={{ background: STOP_COLORS[stop.kind] }}
                aria-hidden
              />
              <div>
                <div className="stops-list__title">
                  {stop.label || KIND_LABEL[stop.kind] || stop.kind}
                </div>
                <div className="stops-list__sub">
                  {formatDateTime(stop.arrival)}
                  {stop.duration_minutes > 0
                    ? ` · ${formatHoursMinutes(stop.duration_minutes)}`
                    : ''}
                </div>
              </div>
              <div className="stops-list__meta">
                {stop.distance_from_origin_miles > 0
                  ? formatMiles(stop.distance_from_origin_miles)
                  : '—'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
