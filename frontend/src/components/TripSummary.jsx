import { formatHoursMinutes, formatMiles } from '../lib/format.js'

export default function TripSummary({ summary, route, inputs }) {
  if (!summary) return null

  const items = [
    {
      label: 'Total distance',
      value: formatMiles(summary.total_distance_miles ?? 0),
      sub:
        route?.total_duration_seconds != null
          ? `${formatHoursMinutes(route.total_duration_seconds / 60)} driving`
          : null,
    },
    {
      label: 'Driving time',
      value: formatHoursMinutes(summary.total_drive_minutes),
      sub: 'CMV at the wheel',
    },
    {
      label: 'On duty (other)',
      value: formatHoursMinutes(summary.total_on_duty_not_driving_minutes),
      sub: 'Pickup, drop-off, fuel',
    },
    {
      label: 'Off duty / sleeper',
      value: formatHoursMinutes(
        (summary.total_off_duty_minutes || 0) + (summary.total_sleeper_berth_minutes || 0),
      ),
      sub: 'Breaks + rests',
    },
    {
      label: 'Total trip',
      value: formatHoursMinutes(summary.total_trip_minutes),
      sub: `${summary.number_of_days || 1} log day${summary.number_of_days === 1 ? '' : 's'}`,
    },
    {
      label: 'Cycle hours used',
      value: `${(summary.cycle_hours_used_at_end ?? inputs?.current_cycle_hours ?? 0).toFixed(1)}h`,
      sub: 'of 70h / 8 days',
    },
  ]

  return (
    <div className="card">
      <div className="card__header">
        <h2 className="card__title">Trip summary</h2>
      </div>
      <div className="card__body">
        <div className="summary-grid">
          {items.map((it) => (
            <div className="stat" key={it.label}>
              <div className="stat__label">{it.label}</div>
              <div className="stat__value">{it.value}</div>
              {it.sub ? <div className="stat__sub">{it.sub}</div> : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
