import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet'
import { formatDateTime, formatMiles, STOP_COLORS, STOP_GLYPHS } from '../lib/format.js'

const STOP_PRIORITY = {
  origin: 0,
  pickup: 1,
  fuel: 2,
  break: 3,
  rest: 4,
  restart: 5,
  dropoff: 6,
}

function makeIcon(kind) {
  const color = STOP_COLORS[kind] || STOP_COLORS.origin
  const glyph = STOP_GLYPHS[kind] || '•'
  // Inline SVG keeps things crisp without an extra image fetch.
  const svg = `
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 40' width='30' height='38'>
      <path d='M16 0 a16 16 0 0 1 16 16 c0 12 -16 24 -16 24 s-16 -12 -16 -24 a16 16 0 0 1 16 -16 z'
            fill='${color}' stroke='white' stroke-width='2' />
      <circle cx='16' cy='15' r='9' fill='white' />
      <text x='16' y='19' text-anchor='middle' font-family='Inter, system-ui, sans-serif'
            font-weight='700' font-size='12' fill='${color}'>${glyph}</text>
    </svg>`
  return L.divIcon({
    className: 'stop-leaflet-icon',
    html: svg,
    iconSize: [30, 38],
    iconAnchor: [15, 38],
    popupAnchor: [0, -32],
  })
}

function FitBounds({ bounds }) {
  const map = useMap()
  useEffect(() => {
    if (!bounds) return
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 })
  }, [bounds, map])
  return null
}

export default function RouteMap({ geometry = [], stops = [] }) {
  // OSRM geometry is [[lon, lat], ...]; Leaflet expects [[lat, lon], ...].
  const polyline = useMemo(() => geometry.map(([lon, lat]) => [lat, lon]), [geometry])

  const sortedStops = useMemo(
    () =>
      [...stops].sort(
        (a, b) =>
          (STOP_PRIORITY[a.kind] ?? 99) - (STOP_PRIORITY[b.kind] ?? 99),
      ),
    [stops],
  )

  const bounds = useMemo(() => {
    if (polyline.length === 0) return null
    let minLat = Infinity,
      minLon = Infinity,
      maxLat = -Infinity,
      maxLon = -Infinity
    for (const [lat, lon] of polyline) {
      if (lat < minLat) minLat = lat
      if (lon < minLon) minLon = lon
      if (lat > maxLat) maxLat = lat
      if (lon > maxLon) maxLon = lon
    }
    return [
      [minLat, minLon],
      [maxLat, maxLon],
    ]
  }, [polyline])

  const center = polyline.length > 0 ? polyline[Math.floor(polyline.length / 2)] : [39.5, -98.35]

  const iconCache = useRef({})
  function iconFor(kind) {
    if (!iconCache.current[kind]) iconCache.current[kind] = makeIcon(kind)
    return iconCache.current[kind]
  }

  return (
    <div className="map">
      <MapContainer
        center={center}
        zoom={5}
        scrollWheelZoom
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        {polyline.length > 1 ? (
          <>
            <Polyline
              positions={polyline}
              pathOptions={{ color: '#0f172a', weight: 7, opacity: 0.18 }}
            />
            <Polyline
              positions={polyline}
              pathOptions={{ color: '#f97316', weight: 4, opacity: 0.9 }}
            />
          </>
        ) : null}
        {sortedStops.map((stop, idx) => (
          <Marker
            key={`${stop.kind}-${idx}-${stop.lat}-${stop.lon}`}
            position={[stop.lat, stop.lon]}
            icon={iconFor(stop.kind)}
          >
            <Popup>
              <div style={{ minWidth: 200 }}>
                <strong style={{ display: 'block', marginBottom: 4 }}>
                  {stop.label}
                </strong>
                <div style={{ color: '#64748b', fontSize: 12 }}>
                  {formatDateTime(stop.arrival)}
                  {stop.duration_minutes > 0
                    ? ` · ${Math.round(stop.duration_minutes)} min`
                    : ''}
                </div>
                {stop.distance_from_origin_miles > 0 ? (
                  <div style={{ color: '#94a3b8', fontSize: 12 }}>
                    {formatMiles(stop.distance_from_origin_miles)} from origin
                  </div>
                ) : null}
              </div>
            </Popup>
          </Marker>
        ))}
        <FitBounds bounds={bounds} />
      </MapContainer>
    </div>
  )
}
