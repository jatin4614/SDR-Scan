import { useMemo } from 'react'
import { Marker, Popup } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'

/**
 * Get marker color based on signal power
 */
function getPowerColor(powerDbm) {
  if (powerDbm >= -40) return '#ff0000'  // Very strong - Red
  if (powerDbm >= -60) return '#ff9800'  // Strong - Orange
  if (powerDbm >= -80) return '#ffeb3b'  // Medium - Yellow
  if (powerDbm >= -100) return '#4caf50' // Weak - Green
  return '#2196f3'                        // Very weak - Blue
}

/**
 * Create a circular icon with color based on signal strength
 */
function createPowerIcon(powerDbm, size = 10) {
  const color = getPowerColor(powerDbm)
  return L.divIcon({
    className: 'measurement-marker',
    html: `<div style="
      background-color: ${color};
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 0 4px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

/**
 * Create custom cluster icon showing average power
 */
function createClusterCustomIcon(cluster) {
  const markers = cluster.getAllChildMarkers()
  const count = markers.length

  // Calculate average power of cluster
  let totalPower = 0
  let validCount = 0
  markers.forEach(marker => {
    const power = marker.options?.power_dbm
    if (power !== undefined) {
      totalPower += power
      validCount++
    }
  })
  const avgPower = validCount > 0 ? totalPower / validCount : -100
  const color = getPowerColor(avgPower)

  // Size based on count
  let size = 30
  if (count > 100) size = 50
  else if (count > 50) size = 45
  else if (count > 20) size = 40
  else if (count > 10) size = 35

  return L.divIcon({
    html: `<div style="
      background-color: ${color};
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: ${size > 40 ? 14 : 12}px;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    ">
      ${count}
    </div>`,
    className: 'measurement-cluster',
    iconSize: L.point(size, size),
  })
}

/**
 * MeasurementCluster Component
 *
 * Displays measurements as clustered markers on the map.
 * Clusters show count and average signal strength.
 */
function MeasurementCluster({
  measurements = [],
  onMeasurementClick,
  showPopups = true,
  maxClusterRadius = 80,
  disableClusteringAtZoom = 18,
}) {
  // Filter valid measurements
  const validMeasurements = useMemo(() =>
    measurements.filter(m => m.latitude && m.longitude),
    [measurements]
  )

  if (validMeasurements.length === 0) {
    return null
  }

  return (
    <MarkerClusterGroup
      chunkedLoading
      maxClusterRadius={maxClusterRadius}
      disableClusteringAtZoom={disableClusteringAtZoom}
      iconCreateFunction={createClusterCustomIcon}
      spiderfyOnMaxZoom
      showCoverageOnHover={false}
      animate
    >
      {validMeasurements.map((measurement, index) => (
        <Marker
          key={measurement.id || `m-${index}`}
          position={[measurement.latitude, measurement.longitude]}
          icon={createPowerIcon(measurement.power_dbm)}
          power_dbm={measurement.power_dbm}
          eventHandlers={{
            click: () => onMeasurementClick?.(measurement),
          }}
        >
          {showPopups && (
            <Popup>
              <MeasurementPopup measurement={measurement} />
            </Popup>
          )}
        </Marker>
      ))}
    </MarkerClusterGroup>
  )
}

/**
 * Popup content for a measurement marker
 */
function MeasurementPopup({ measurement }) {
  const formatFrequency = (hz) => {
    if (hz >= 1e9) return `${(hz / 1e9).toFixed(3)} GHz`
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`
    return `${(hz / 1e3).toFixed(3)} kHz`
  }

  return (
    <div style={{ minWidth: 180 }}>
      <div style={{
        fontWeight: 'bold',
        marginBottom: 8,
        paddingBottom: 8,
        borderBottom: '1px solid #eee',
        color: getPowerColor(measurement.power_dbm),
      }}>
        {measurement.power_dbm?.toFixed(1)} dBm
      </div>

      <table style={{ fontSize: 12, width: '100%' }}>
        <tbody>
          <tr>
            <td style={{ color: '#666', paddingRight: 8 }}>Frequency:</td>
            <td style={{ fontWeight: 500 }}>{formatFrequency(measurement.frequency)}</td>
          </tr>
          {measurement.bandwidth && (
            <tr>
              <td style={{ color: '#666', paddingRight: 8 }}>Bandwidth:</td>
              <td>{formatFrequency(measurement.bandwidth)}</td>
            </tr>
          )}
          {measurement.noise_floor_dbm && (
            <tr>
              <td style={{ color: '#666', paddingRight: 8 }}>Noise Floor:</td>
              <td>{measurement.noise_floor_dbm.toFixed(1)} dBm</td>
            </tr>
          )}
          {measurement.snr_db && (
            <tr>
              <td style={{ color: '#666', paddingRight: 8 }}>SNR:</td>
              <td>{measurement.snr_db.toFixed(1)} dB</td>
            </tr>
          )}
          <tr>
            <td style={{ color: '#666', paddingRight: 8 }}>Location:</td>
            <td style={{ fontSize: 11 }}>
              {measurement.latitude?.toFixed(6)}, {measurement.longitude?.toFixed(6)}
            </td>
          </tr>
          {measurement.timestamp && (
            <tr>
              <td style={{ color: '#666', paddingRight: 8 }}>Time:</td>
              <td style={{ fontSize: 11 }}>
                {new Date(measurement.timestamp).toLocaleString()}
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {measurement.survey_id && (
        <div style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: '1px solid #eee',
          fontSize: 11,
          color: '#666',
        }}>
          Survey ID: {measurement.survey_id}
        </div>
      )}
    </div>
  )
}

/**
 * Power level legend component
 */
export function PowerLegend({ style = {} }) {
  const levels = [
    { label: 'Very Strong', range: '> -40 dBm', color: '#ff0000' },
    { label: 'Strong', range: '-60 to -40 dBm', color: '#ff9800' },
    { label: 'Medium', range: '-80 to -60 dBm', color: '#ffeb3b' },
    { label: 'Weak', range: '-100 to -80 dBm', color: '#4caf50' },
    { label: 'Very Weak', range: '< -100 dBm', color: '#2196f3' },
  ]

  return (
    <div style={{
      background: 'white',
      padding: 10,
      borderRadius: 4,
      boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
      fontSize: 12,
      ...style,
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>Signal Strength</div>
      {levels.map(level => (
        <div key={level.label} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
          <div style={{
            width: 16,
            height: 16,
            borderRadius: '50%',
            backgroundColor: level.color,
            marginRight: 8,
            border: '1px solid #ccc',
          }} />
          <div>
            <div style={{ fontWeight: 500 }}>{level.label}</div>
            <div style={{ fontSize: 10, color: '#666' }}>{level.range}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default MeasurementCluster
