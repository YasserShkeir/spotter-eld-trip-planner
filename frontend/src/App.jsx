import { useState } from 'react'
import LogSheetList from './components/LogSheetList.jsx'
import RouteMap from './components/RouteMap.jsx'
import StopsList from './components/StopsList.jsx'
import TripForm from './components/TripForm.jsx'
import TripSummary from './components/TripSummary.jsx'
import { usePlanTrip } from './hooks/usePlanTrip.js'

export default function App() {
  const { plan, data, error, isLoading } = usePlanTrip()
  const [tab, setTab] = useState('map')

  async function handleSubmit(payload) {
    try {
      const result = await plan(payload)
      if (result) setTab('map')
    } catch {
      // handled via hook's error state
    }
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <div className="brand__mark">ELD</div>
          <div>
            <div className="brand__name">Spotter ELD Trip Planner</div>
            <span className="brand__tag">FMCSA · 70-hr/8-day</span>
          </div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
          Routes via{' '}
          <a href="https://project-osrm.org" target="_blank" rel="noreferrer">
            OSRM
          </a>{' '}
          · Maps ©{' '}
          <a
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noreferrer"
          >
            OpenStreetMap
          </a>
        </div>
      </header>

      <div className="app__main">
        <aside className="sidebar">
          <h1 style={{ marginBottom: 4 }}>Plan a trip</h1>
          <p style={{ color: 'var(--text-3)', marginBottom: 20 }}>
            We'll route current → pickup → drop-off and auto-generate
            HOS-compliant daily logs.
          </p>
          <TripForm onSubmit={handleSubmit} isLoading={isLoading} />

          {error ? (
            <div className="banner banner--error" style={{ marginTop: 20 }}>
              <strong>Couldn't plan that trip.</strong>
              <div>{error.message}</div>
            </div>
          ) : null}

          <div style={{ marginTop: 24, fontSize: 12, color: 'var(--text-3)' }}>
            <h4 style={{ marginBottom: 8 }}>Assumptions</h4>
            <ul style={{ paddingLeft: 18, margin: 0, lineHeight: 1.7 }}>
              <li>Property-carrying CMV, 70-hr / 8-day cycle</li>
              <li>11-hr drive limit · 14-hr window</li>
              <li>30-min break after 8 cumulative drive hours</li>
              <li>10-hr off-duty resets the daily clocks</li>
              <li>34-hr restart resets the cycle</li>
              <li>1 hr each for pickup and drop-off</li>
              <li>Fuel stop at least every 1,000 miles</li>
              <li>No adverse driving conditions</li>
            </ul>
          </div>
        </aside>

        <main className="workspace">
          {!data ? (
            <EmptyState />
          ) : (
            <>
              <TripSummary
                summary={data.plan?.summary}
                route={data.route}
                inputs={data.inputs}
              />

              <div className="card">
                <div className="card__body card__body--flush">
                  <div className="tabs">
                    <button
                      className={`tab ${tab === 'map' ? 'tab--active' : ''}`}
                      onClick={() => setTab('map')}
                    >
                      Route map
                    </button>
                    <button
                      className={`tab ${tab === 'stops' ? 'tab--active' : ''}`}
                      onClick={() => setTab('stops')}
                    >
                      Stops & schedule
                    </button>
                    <button
                      className={`tab ${tab === 'logs' ? 'tab--active' : ''}`}
                      onClick={() => setTab('logs')}
                    >
                      Daily logs
                    </button>
                  </div>

                  <div style={{ padding: 20 }}>
                    {tab === 'map' ? (
                      <RouteMap
                        geometry={data.route?.full_geometry || []}
                        stops={data.plan?.stops || []}
                      />
                    ) : null}
                    {tab === 'stops' ? (
                      <StopsList stops={data.plan?.stops || []} />
                    ) : null}
                    {tab === 'logs' ? (
                      <LogSheetList
                        days={data.plan?.days || []}
                        inputs={data.inputs}
                      />
                    ) : null}
                  </div>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="card">
      <div className="card__body">
        <div className="empty">
          <div style={{ fontSize: 36, marginBottom: 12 }}>🛣️</div>
          <div className="empty__title">No trip planned yet</div>
          <div>
            Fill the form on the left, or hit <span className="kbd">Try a sample trip</span> to see a
            cross-country example with HOS-compliant logs.
          </div>
        </div>
      </div>
    </div>
  )
}
