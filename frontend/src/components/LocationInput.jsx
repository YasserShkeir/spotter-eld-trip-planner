import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { useDebounce } from '../hooks/useDebounce.js'

export default function LocationInput({
  id,
  label,
  hint,
  placeholder,
  value,
  onChange,
  error,
}) {
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState([])
  const [highlighted, setHighlighted] = useState(0)
  const [loading, setLoading] = useState(false)
  const wrapRef = useRef(null)
  const abortRef = useRef(null)

  const debounced = useDebounce(value?.query ?? '', 300)

  // Close on click outside
  useEffect(() => {
    function onDocClick(e) {
      if (!wrapRef.current) return
      if (!wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  // Fetch suggestions
  useEffect(() => {
    if (!debounced || debounced.length < 3 || value?.latitude != null) {
      setResults([])
      setLoading(false)
      return
    }
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    api
      .searchPlaces(debounced, { signal: controller.signal })
      .then((rows) => {
        setResults(rows || [])
        setHighlighted(0)
      })
      .catch(() => {
        // network errors here are non-fatal — user can still submit, server will geocode
        setResults([])
      })
      .finally(() => setLoading(false))
  }, [debounced, value?.latitude])

  const onInputChange = useCallback(
    (e) => {
      onChange({ query: e.target.value, label: '', latitude: undefined, longitude: undefined })
      setOpen(true)
    },
    [onChange],
  )

  const pick = useCallback(
    (row) => {
      onChange({
        query: row.label,
        label: row.label,
        latitude: row.latitude,
        longitude: row.longitude,
      })
      setOpen(false)
      setResults([])
    },
    [onChange],
  )

  const onKeyDown = useCallback(
    (e) => {
      if (!open || results.length === 0) return
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlighted((h) => Math.min(results.length - 1, h + 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlighted((h) => Math.max(0, h - 1))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        pick(results[highlighted])
      } else if (e.key === 'Escape') {
        setOpen(false)
      }
    },
    [open, results, highlighted, pick],
  )

  const showSuggest =
    open && (results.length > 0 || (loading && (debounced?.length ?? 0) >= 3))

  return (
    <div className="field" ref={wrapRef}>
      <label htmlFor={id} className="field__label">
        {label}
      </label>
      <input
        id={id}
        className="input"
        type="text"
        autoComplete="off"
        placeholder={placeholder}
        value={value?.query ?? ''}
        onChange={onInputChange}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        aria-invalid={!!error}
        aria-autocomplete="list"
        aria-expanded={showSuggest}
      />
      {hint && !error ? <div className="field__hint">{hint}</div> : null}
      {error ? <div className="field__error">{error}</div> : null}
      {showSuggest ? (
        <div className="suggest" role="listbox">
          {loading && results.length === 0 ? (
            <div className="suggest__empty">Searching…</div>
          ) : null}
          {results.map((row, idx) => (
            <div
              key={`${row.latitude}-${row.longitude}-${idx}`}
              role="option"
              aria-selected={idx === highlighted}
              className={`suggest__item ${
                idx === highlighted ? 'suggest__item--active' : ''
              }`}
              onMouseEnter={() => setHighlighted(idx)}
              onMouseDown={(e) => {
                e.preventDefault()
                pick(row)
              }}
            >
              {row.label}
            </div>
          ))}
          {!loading && results.length === 0 ? (
            <div className="suggest__empty">No matches. We'll still geocode on submit.</div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
