import { useState, useEffect, useMemo, useCallback } from 'react'
import { Polyline, CircleMarker, Popup, useMap } from 'react-leaflet'
import {
  Box,
  Paper,
  Typography,
  Slider,
  IconButton,
  Tooltip,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  SkipPrevious as PrevIcon,
  SkipNext as NextIcon,
  MyLocation as LocationIcon,
} from '@mui/icons-material'

/**
 * Get color for track segment based on signal strength or speed
 */
function getTrackColor(value, mode = 'power', options = {}) {
  const { minPower = -120, maxPower = -20, maxSpeed = 30 } = options

  let normalized
  if (mode === 'power') {
    normalized = Math.max(0, Math.min(1, (value - minPower) / (maxPower - minPower)))
  } else if (mode === 'speed') {
    normalized = Math.max(0, Math.min(1, value / maxSpeed))
  } else {
    normalized = 0.5
  }

  // Color gradient: blue -> cyan -> green -> yellow -> red
  if (normalized < 0.25) {
    return '#2196f3' // Blue
  } else if (normalized < 0.5) {
    return '#00bcd4' // Cyan
  } else if (normalized < 0.75) {
    return '#4caf50' // Green
  } else if (normalized < 0.9) {
    return '#ffeb3b' // Yellow
  }
  return '#f44336' // Red
}

/**
 * TrackLine Component
 *
 * Renders a GPS track as a polyline with color-coded segments
 */
function TrackLine({
  points = [],
  colorMode = 'power',
  weight = 4,
  opacity = 0.8,
  showMarkers = false,
  markerInterval = 10,
}) {
  // Create colored segments
  const segments = useMemo(() => {
    if (points.length < 2) return []

    const result = []
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]

      // Get value for coloring
      let value
      if (colorMode === 'power') {
        value = (start.power_dbm + end.power_dbm) / 2
      } else if (colorMode === 'speed') {
        value = start.speed || 0
      } else {
        value = 0
      }

      result.push({
        positions: [[start.latitude, start.longitude], [end.latitude, end.longitude]],
        color: getTrackColor(value, colorMode),
        index: i,
      })
    }
    return result
  }, [points, colorMode])

  // Marker points (every N points)
  const markerPoints = useMemo(() => {
    if (!showMarkers) return []
    return points.filter((_, i) => i % markerInterval === 0)
  }, [points, showMarkers, markerInterval])

  return (
    <>
      {segments.map((segment, idx) => (
        <Polyline
          key={idx}
          positions={segment.positions}
          pathOptions={{
            color: segment.color,
            weight,
            opacity,
            lineCap: 'round',
            lineJoin: 'round',
          }}
        />
      ))}

      {markerPoints.map((point, idx) => (
        <CircleMarker
          key={`marker-${idx}`}
          center={[point.latitude, point.longitude]}
          radius={4}
          pathOptions={{
            fillColor: '#ffffff',
            fillOpacity: 1,
            color: '#333',
            weight: 1,
          }}
        >
          <Popup>
            <div style={{ fontSize: 12 }}>
              <div><strong>Point {idx * markerInterval + 1}</strong></div>
              <div>Power: {point.power_dbm?.toFixed(1)} dBm</div>
              {point.speed && <div>Speed: {point.speed.toFixed(1)} m/s</div>}
              <div style={{ fontSize: 10, color: '#666' }}>
                {new Date(point.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

/**
 * TrackViewer Component
 *
 * Main component for viewing and playing back GPS tracks with measurements
 */
function TrackViewer({
  tracks = [],
  selectedTrackId,
  onTrackSelect,
  showControls = true,
  colorMode = 'power',
  onColorModeChange,
}) {
  const map = useMap()
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)

  // Get selected track points
  const selectedTrack = useMemo(() =>
    tracks.find(t => t.id === selectedTrackId),
    [tracks, selectedTrackId]
  )

  const trackPoints = selectedTrack?.points || []

  // Playback timer
  useEffect(() => {
    if (!isPlaying || trackPoints.length === 0) return

    const interval = setInterval(() => {
      setCurrentIndex(prev => {
        const next = prev + 1
        if (next >= trackPoints.length) {
          setIsPlaying(false)
          return prev
        }
        return next
      })
    }, 100 / playbackSpeed)

    return () => clearInterval(interval)
  }, [isPlaying, playbackSpeed, trackPoints.length])

  // Center map on current point during playback
  useEffect(() => {
    if (isPlaying && trackPoints[currentIndex]) {
      const point = trackPoints[currentIndex]
      map.panTo([point.latitude, point.longitude], { animate: true })
    }
  }, [currentIndex, isPlaying, trackPoints, map])

  // Fit map to track bounds when track changes
  useEffect(() => {
    if (trackPoints.length > 0) {
      const bounds = trackPoints.map(p => [p.latitude, p.longitude])
      map.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [selectedTrackId, trackPoints, map])

  const handlePlay = () => setIsPlaying(true)
  const handlePause = () => setIsPlaying(false)
  const handlePrev = () => setCurrentIndex(prev => Math.max(0, prev - 1))
  const handleNext = () => setCurrentIndex(prev => Math.min(trackPoints.length - 1, prev + 1))

  const handleCenterOnCurrent = useCallback(() => {
    if (trackPoints[currentIndex]) {
      const point = trackPoints[currentIndex]
      map.setView([point.latitude, point.longitude], 16)
    }
  }, [currentIndex, trackPoints, map])

  const currentPoint = trackPoints[currentIndex]

  return (
    <>
      {/* Render all tracks */}
      {tracks.map(track => (
        <TrackLine
          key={track.id}
          points={track.points}
          colorMode={colorMode}
          weight={track.id === selectedTrackId ? 5 : 3}
          opacity={track.id === selectedTrackId ? 1 : 0.5}
          showMarkers={track.id === selectedTrackId}
        />
      ))}

      {/* Current position marker during playback */}
      {currentPoint && selectedTrack && (
        <CircleMarker
          center={[currentPoint.latitude, currentPoint.longitude]}
          radius={10}
          pathOptions={{
            fillColor: '#ff5722',
            fillOpacity: 1,
            color: '#ffffff',
            weight: 3,
          }}
        >
          <Popup>
            <div>
              <strong>Current Position</strong>
              <div>Power: {currentPoint.power_dbm?.toFixed(1)} dBm</div>
              <div>Point: {currentIndex + 1} / {trackPoints.length}</div>
            </div>
          </Popup>
        </CircleMarker>
      )}
    </>
  )
}

/**
 * Track playback controls (separate component for use outside map)
 */
export function TrackPlaybackControls({
  tracks = [],
  selectedTrackId,
  onTrackSelect,
  trackPoints = [],
  currentIndex = 0,
  onIndexChange,
  isPlaying = false,
  onPlayPause,
  playbackSpeed = 1,
  onSpeedChange,
  colorMode = 'power',
  onColorModeChange,
}) {
  const currentPoint = trackPoints[currentIndex]

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <LocationIcon color="primary" />
        <Typography variant="subtitle1">Track Playback</Typography>
        {isPlaying && <Chip size="small" color="success" label="Playing" />}
      </Box>

      {/* Track Selection */}
      <FormControl size="small" fullWidth sx={{ mb: 2 }}>
        <InputLabel>Select Track</InputLabel>
        <Select
          value={selectedTrackId || ''}
          label="Select Track"
          onChange={(e) => onTrackSelect?.(e.target.value)}
        >
          {tracks.map(track => (
            <MenuItem key={track.id} value={track.id}>
              {track.name || `Track ${track.id}`} ({track.points?.length || 0} points)
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Color Mode */}
      <FormControl size="small" fullWidth sx={{ mb: 2 }}>
        <InputLabel>Color By</InputLabel>
        <Select
          value={colorMode}
          label="Color By"
          onChange={(e) => onColorModeChange?.(e.target.value)}
        >
          <MenuItem value="power">Signal Power</MenuItem>
          <MenuItem value="speed">Speed</MenuItem>
          <MenuItem value="time">Time</MenuItem>
        </Select>
      </FormControl>

      {/* Timeline Slider */}
      {trackPoints.length > 0 && (
        <>
          <Slider
            value={currentIndex}
            onChange={(e, v) => onIndexChange?.(v)}
            min={0}
            max={trackPoints.length - 1}
            size="small"
            sx={{ mb: 1 }}
          />

          {/* Playback Controls */}
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1 }}>
            <IconButton size="small" onClick={() => onIndexChange?.(0)}>
              <PrevIcon />
            </IconButton>

            <IconButton
              color="primary"
              onClick={onPlayPause}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>

            <IconButton
              size="small"
              onClick={() => onIndexChange?.(trackPoints.length - 1)}
            >
              <NextIcon />
            </IconButton>

            <Tooltip title="Speed">
              <Chip
                size="small"
                label={`${playbackSpeed}x`}
                onClick={() => onSpeedChange?.(playbackSpeed >= 4 ? 1 : playbackSpeed * 2)}
                sx={{ cursor: 'pointer' }}
              />
            </Tooltip>
          </Box>

          {/* Current Point Info */}
          {currentPoint && (
            <Box sx={{
              mt: 2,
              p: 1,
              bgcolor: 'background.default',
              borderRadius: 1,
              fontSize: 12,
            }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Point {currentIndex + 1} / {trackPoints.length}</span>
                <span>{currentPoint.power_dbm?.toFixed(1)} dBm</span>
              </Box>
              <Box sx={{ color: 'text.secondary', fontSize: 11 }}>
                {currentPoint.latitude?.toFixed(6)}, {currentPoint.longitude?.toFixed(6)}
              </Box>
              {currentPoint.timestamp && (
                <Box sx={{ color: 'text.secondary', fontSize: 11 }}>
                  {new Date(currentPoint.timestamp).toLocaleString()}
                </Box>
              )}
            </Box>
          )}
        </>
      )}

      {trackPoints.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
          Select a track to view playback controls
        </Typography>
      )}
    </Paper>
  )
}

export default TrackViewer
