import LogSheet from './LogSheet.jsx'

export default function LogSheetList({ days = [], inputs }) {
  if (!days.length) return null

  const carrier = 'Spotter ELD Demo Carrier'
  const mainOffice =
    inputs?.current_location?.label?.split(',').slice(-2).join(',').trim() || '—'
  const homeTerminal = inputs?.current_location?.label || '—'
  const truckNumbers = `T-${Math.floor(Math.random() * 9000 + 1000)} / Trailer ${Math.floor(
    Math.random() * 900 + 100,
  )}`

  return (
    <div className="card">
      <div className="card__header">
        <h2 className="card__title">Daily ELD logs</h2>
        <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {days.length} day{days.length === 1 ? '' : 's'} ·{' '}
          <button
            type="button"
            className="btn btn--ghost"
            style={{ padding: '4px 10px', fontSize: 12 }}
            onClick={() => window.print()}
          >
            Print logs
          </button>
        </span>
      </div>
      <div className="card__body">
        <div className="logsheets">
          {days.map((day, i) => (
            <LogSheet
              key={day.date}
              day={day}
              dayIndex={i}
              totalDays={days.length}
              carrier={carrier}
              mainOffice={mainOffice}
              homeTerminal={homeTerminal}
              truckNumbers={truckNumbers}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
