const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

function url(path) {
  if (!path.startsWith('/')) path = `/${path}`
  return `${BASE_URL}${path}`
}

async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url(path), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  const text = await response.text()
  const data = text ? safeParseJSON(text) : null

  if (!response.ok) {
    const message =
      (data && (data.detail || data.error)) ||
      `Request failed (${response.status})`
    const err = new Error(message)
    err.status = response.status
    err.data = data
    throw err
  }
  return data
}

function safeParseJSON(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export const api = {
  planTrip(payload, { signal } = {}) {
    return request('/api/trips/plan/', { method: 'POST', body: payload, signal })
  },
  searchPlaces(query, { signal } = {}) {
    const q = encodeURIComponent(query)
    return request(`/api/geocode/?q=${q}`, { signal })
  },
  listTrips({ signal } = {}) {
    return request('/api/trips/', { signal })
  },
  getTrip(id, { signal } = {}) {
    return request(`/api/trips/${id}/`, { signal })
  },
}
