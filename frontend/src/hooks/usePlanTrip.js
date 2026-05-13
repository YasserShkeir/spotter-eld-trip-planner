import { useCallback, useRef, useState } from 'react'
import { api } from '../api/client.js'

export function usePlanTrip() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef(null)

  const plan = useCallback(async (payload) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setError(null)
    setIsLoading(true)
    try {
      const response = await api.planTrip(payload, { signal: controller.signal })
      setData(response)
      return response
    } catch (err) {
      if (err.name !== 'AbortError') setError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
  }, [])

  return { plan, data, error, isLoading, reset }
}
