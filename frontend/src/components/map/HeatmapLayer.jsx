import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

/**
 * HeatmapLayer Component
 *
 * Renders a heatmap overlay on the Leaflet map using leaflet.heat.
 * Useful for visualizing signal strength distribution across an area.
 */
function HeatmapLayer({
  points = [],
  options = {},
  visible = true,
}) {
  const map = useMap()

  useEffect(() => {
    if (!visible || points.length === 0) {
      return
    }

    // Default heatmap options
    const heatmapOptions = {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      max: 1.0,
      minOpacity: 0.3,
      gradient: {
        0.0: '#0000ff',  // Blue - weak signal
        0.25: '#00ffff', // Cyan
        0.5: '#00ff00',  // Green
        0.75: '#ffff00', // Yellow
        1.0: '#ff0000',  // Red - strong signal
      },
      ...options,
    }

    // Create heat layer
    const heatLayer = L.heatLayer(points, heatmapOptions)
    heatLayer.addTo(map)

    // Cleanup on unmount or when points change
    return () => {
      map.removeLayer(heatLayer)
    }
  }, [map, points, options, visible])

  return null
}

/**
 * Convert measurements to heatmap points
 *
 * @param {Array} measurements - Array of measurement objects
 * @param {Object} options - Conversion options
 * @param {number} options.minPower - Minimum power in dBm (maps to 0)
 * @param {number} options.maxPower - Maximum power in dBm (maps to 1)
 * @returns {Array} Array of [lat, lng, intensity] points
 */
export function measurementsToHeatmapPoints(measurements, options = {}) {
  const {
    minPower = -120,
    maxPower = -20,
  } = options

  const powerRange = maxPower - minPower

  return measurements
    .filter(m => m.latitude && m.longitude && m.power_dbm !== undefined)
    .map(m => {
      // Normalize power to 0-1 range
      const normalizedPower = Math.max(0, Math.min(1,
        (m.power_dbm - minPower) / powerRange
      ))
      return [m.latitude, m.longitude, normalizedPower]
    })
}

/**
 * Aggregate measurements by location for better heatmap visualization
 *
 * @param {Array} measurements - Array of measurements
 * @param {number} precision - Coordinate rounding precision (decimal places)
 * @returns {Array} Aggregated heatmap points
 */
export function aggregateMeasurements(measurements, precision = 5) {
  const grid = new Map()

  measurements.forEach(m => {
    if (!m.latitude || !m.longitude) return

    // Round coordinates to create grid cells
    const lat = m.latitude.toFixed(precision)
    const lng = m.longitude.toFixed(precision)
    const key = `${lat},${lng}`

    if (!grid.has(key)) {
      grid.set(key, {
        lat: parseFloat(lat),
        lng: parseFloat(lng),
        powers: [],
        count: 0,
      })
    }

    const cell = grid.get(key)
    cell.powers.push(m.power_dbm)
    cell.count++
  })

  // Calculate average power for each cell
  return Array.from(grid.values()).map(cell => ({
    latitude: cell.lat,
    longitude: cell.lng,
    power_dbm: cell.powers.reduce((a, b) => a + b, 0) / cell.powers.length,
    count: cell.count,
  }))
}

/**
 * Create frequency-specific heatmap layers
 *
 * @param {Array} measurements - Array of measurements
 * @param {Array} frequencyBands - Array of {name, start, end} objects
 * @returns {Object} Map of band name to heatmap points
 */
export function createFrequencyBandLayers(measurements, frequencyBands) {
  const layers = {}

  frequencyBands.forEach(band => {
    const bandMeasurements = measurements.filter(
      m => m.frequency >= band.start && m.frequency <= band.end
    )
    layers[band.name] = measurementsToHeatmapPoints(bandMeasurements)
  })

  return layers
}

export default HeatmapLayer
