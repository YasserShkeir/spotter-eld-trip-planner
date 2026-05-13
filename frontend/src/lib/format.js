export function formatHoursMinutes(totalMinutes) {
  if (totalMinutes == null || Number.isNaN(totalMinutes)) return '—'
  const total = Math.round(totalMinutes)
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${String(m).padStart(2, '0')}m`
}

export function formatMiles(miles) {
  if (miles == null) return '—'
  return `${miles.toLocaleString(undefined, {
    maximumFractionDigits: miles >= 100 ? 0 : 1,
  })} mi`
}

export function formatDateTime(iso, opts = {}) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    ...opts,
  })
}

export function formatDate(iso) {
  if (!iso) return ''
  // For dates that come as YYYY-MM-DD, parse as local-noon so the date
  // doesn't shift due to timezone.
  const parts = iso.split('-')
  if (parts.length === 3) {
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]), 12)
    return d.toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }
  return iso
}

export function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export const STATUS_COLORS = {
  off_duty: 'var(--status-off)',
  sleeper_berth: 'var(--status-sleeper)',
  driving: 'var(--status-driving)',
  on_duty_not_driving: 'var(--status-on-duty)',
}

export const STATUS_LABELS = {
  off_duty: 'Off Duty',
  sleeper_berth: 'Sleeper Berth',
  driving: 'Driving',
  on_duty_not_driving: 'On Duty (Not Driving)',
}

export const STOP_COLORS = {
  origin: 'var(--stop-origin)',
  pickup: 'var(--stop-pickup)',
  dropoff: 'var(--stop-dropoff)',
  fuel: 'var(--stop-fuel)',
  rest: 'var(--stop-rest)',
  break: 'var(--stop-break)',
  restart: 'var(--stop-restart)',
}

export const STOP_GLYPHS = {
  origin: '·',
  pickup: 'P',
  dropoff: 'D',
  fuel: 'F',
  rest: 'Z',
  break: 'B',
  restart: 'R',
}
