import { useState } from 'react'
import LocationInput from './LocationInput.jsx'

const EMPTY_LOCATION = { query: '', label: '', latitude: undefined, longitude: undefined }

export default function TripForm({ onSubmit, isLoading, defaultValues }) {
  const [currentLocation, setCurrentLocation] = useState(
    defaultValues?.currentLocation ?? EMPTY_LOCATION,
  )
  const [pickupLocation, setPickupLocation] = useState(
    defaultValues?.pickupLocation ?? EMPTY_LOCATION,
  )
  const [dropoffLocation, setDropoffLocation] = useState(
    defaultValues?.dropoffLocation ?? EMPTY_LOCATION,
  )
  const [cycleHours, setCycleHours] = useState(defaultValues?.cycleHours ?? '0')
  const [departureAt, setDepartureAt] = useState(defaultValues?.departureAt ?? '')
  const [errors, setErrors] = useState({})

  function validate() {
    const e = {}
    if (!currentLocation.query.trim()) e.currentLocation = 'Required.'
    if (!pickupLocation.query.trim()) e.pickupLocation = 'Required.'
    if (!dropoffLocation.query.trim()) e.dropoffLocation = 'Required.'

    const n = Number(cycleHours)
    if (Number.isNaN(n) || n < 0 || n > 70) {
      e.cycleHours = 'Enter a number between 0 and 70.'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function handleSubmit(ev) {
    ev.preventDefault()
    if (!validate()) return
    const payload = {
      current_location: locationToPayload(currentLocation),
      pickup_location: locationToPayload(pickupLocation),
      dropoff_location: locationToPayload(dropoffLocation),
      current_cycle_hours: Number(cycleHours),
    }
    if (departureAt) {
      payload.departure_at = new Date(departureAt).toISOString()
    }
    onSubmit(payload)
  }

  function loadSample() {
    setCurrentLocation({
      query: 'Phoenix, Arizona, United States',
      label: 'Phoenix, Arizona, United States',
      latitude: 33.4483771,
      longitude: -112.0740373,
    })
    setPickupLocation({
      query: 'Los Angeles, California, United States',
      label: 'Los Angeles, California, United States',
      latitude: 34.0536909,
      longitude: -118.242766,
    })
    setDropoffLocation({
      query: 'Dallas, Texas, United States',
      label: 'Dallas, Texas, United States',
      latitude: 32.7762719,
      longitude: -96.7968559,
    })
    setCycleHours('12')
    setErrors({})
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <LocationInput
        id="current-location"
        label="Current location"
        placeholder="e.g. Phoenix, Arizona"
        value={currentLocation}
        onChange={setCurrentLocation}
        error={errors.currentLocation}
      />
      <LocationInput
        id="pickup-location"
        label="Pickup location"
        placeholder="Where you're loading"
        value={pickupLocation}
        onChange={setPickupLocation}
        error={errors.pickupLocation}
      />
      <LocationInput
        id="dropoff-location"
        label="Drop-off location"
        placeholder="Where you're delivering"
        value={dropoffLocation}
        onChange={setDropoffLocation}
        error={errors.dropoffLocation}
      />

      <div className="field">
        <label htmlFor="cycle-hours" className="field__label">
          Current cycle used (hours)
        </label>
        <input
          id="cycle-hours"
          className="input"
          type="number"
          min="0"
          max="70"
          step="0.25"
          value={cycleHours}
          onChange={(e) => setCycleHours(e.target.value)}
          aria-invalid={!!errors.cycleHours}
        />
        <div className="field__hint">
          Hours already on duty in the rolling 70-hour / 8-day cycle.
        </div>
        {errors.cycleHours ? <div className="field__error">{errors.cycleHours}</div> : null}
      </div>

      <div className="field">
        <label htmlFor="departure-at" className="field__label">
          Departure (optional)
        </label>
        <input
          id="departure-at"
          className="input"
          type="datetime-local"
          value={departureAt}
          onChange={(e) => setDepartureAt(e.target.value)}
        />
        <div className="field__hint">
          Defaults to now if left blank. Used as the clock-start for the HOS plan.
        </div>
      </div>

      <button
        type="submit"
        className="btn btn--primary btn--block"
        disabled={isLoading}
        aria-disabled={isLoading}
      >
        {isLoading ? (
          <>
            <span className="spinner" /> Planning…
          </>
        ) : (
          'Plan trip'
        )}
      </button>

      <button
        type="button"
        className="btn btn--ghost btn--block"
        onClick={loadSample}
        disabled={isLoading}
      >
        Try a sample trip
      </button>
    </form>
  )
}

function locationToPayload(loc) {
  if (loc.latitude != null && loc.longitude != null) {
    return {
      label: loc.label || loc.query,
      latitude: loc.latitude,
      longitude: loc.longitude,
    }
  }
  return { query: loc.query }
}
