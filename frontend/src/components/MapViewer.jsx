import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Drawer,
  IconButton,
  Tooltip,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Menu as MenuIcon,
  ChevronLeft as CloseIcon,
} from '@mui/icons-material'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import { useStore } from '../store/useStore'
import { api } from '../services/api'
import {
  HeatmapLayer,
  measurementsToHeatmapPoints,
  MeasurementCluster,
  PowerLegend,
  TrackViewer,
  TrackPlaybackControls,
  MapControls,
  mapTileProviders,
} from './map'
import 'leaflet/dist/leaflet.css'

const DRAWER_WIDTH = 320

/**
 * Map controller component for programmatic map control
 */
function MapController({ center, bounds, onMapReady }) {
  const map = useMap()

  useEffect(() => {
    onMapReady?.(map)
  }, [map, onMapReady])

  useEffect(() => {
    if (bounds && bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] })
    } else if (center) {
      map.setView(center, map.getZoom())
    }
  }, [center, bounds, map])

  return null
}

function MapViewer() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  const { surveys, measurements, setMeasurements, measurementFilters, setMeasurementFilters } = useStore()

  // UI State
  const [drawerOpen, setDrawerOpen] = useState(!isMobile)
  const [mapRef, setMapRef] = useState(null)
  const [loading, setLoading] = useState(false)

  // Layer visibility
  const [layers, setLayers] = useState({
    markers: true,
    heatmap: false,
    tracks: true,
    clusters: true,
  })

  // Display settings
  const [settings, setSettings] = useState({
    mapTileProvider: 'CartoDB Dark',
    markerSize: 8,
    heatmapRadius: 25,
    heatmapBlur: 15,
    clusterRadius: 80,
    trackWidth: 4,
  })

  // Filters
  const [filters, setFilters] = useState({
    frequencyBand: 'All',
    customFreqStart: null,
    customFreqEnd: null,
    powerRange: [-120, -20],
    surveyId: null,
    timeRange: null,
  })

  // Track playback state
  const [tracks, setTracks] = useState([])
  const [selectedTrackId, setSelectedTrackId] = useState(null)
  const [trackPlayback, setTrackPlayback] = useState({
    currentIndex: 0,
    isPlaying: false,
    speed: 1,
    colorMode: 'power',
  })

  // Load measurements based on filters
  useEffect(() => {
    async function loadMeasurements() {
      setLoading(true)
      try {
        const params = { limit: 5000 }

        if (filters.surveyId) {
          params.survey_id = filters.surveyId
        }
        if (filters.customFreqStart) {
          params.start_freq = filters.customFreqStart
        }
        if (filters.customFreqEnd) {
          params.end_freq = filters.customFreqEnd
        }

        const response = await api.getMeasurements(params)
        setMeasurements(response.measurements || [])
      } catch (error) {
        console.error('Failed to load measurements:', error)
      } finally {
        setLoading(false)
      }
    }

    loadMeasurements()
  }, [filters.surveyId, filters.customFreqStart, filters.customFreqEnd, setMeasurements])

  // Load tracks for selected survey
  useEffect(() => {
    if (!filters.surveyId) {
      setTracks([])
      return
    }

    // Group measurements by time to create track
    const sortedMeasurements = [...measurements]
      .filter(m => m.latitude && m.longitude)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

    if (sortedMeasurements.length > 0) {
      setTracks([{
        id: `survey-${filters.surveyId}`,
        name: surveys.find(s => s.id === filters.surveyId)?.name || 'Survey Track',
        points: sortedMeasurements,
      }])
    }
  }, [filters.surveyId, measurements, surveys])

  // Filter measurements by power range
  const filteredMeasurements = useMemo(() => {
    return measurements.filter(m =>
      m.power_dbm >= filters.powerRange[0] &&
      m.power_dbm <= filters.powerRange[1]
    )
  }, [measurements, filters.powerRange])

  // Convert to heatmap points
  const heatmapPoints = useMemo(() => {
    if (!layers.heatmap) return []
    return measurementsToHeatmapPoints(filteredMeasurements, {
      minPower: filters.powerRange[0],
      maxPower: filters.powerRange[1],
    })
  }, [filteredMeasurements, layers.heatmap, filters.powerRange])

  // Calculate bounds for fit
  const measurementBounds = useMemo(() => {
    const validPoints = filteredMeasurements.filter(m => m.latitude && m.longitude)
    if (validPoints.length === 0) return null
    return validPoints.map(m => [m.latitude, m.longitude])
  }, [filteredMeasurements])

  // Get current tile provider
  const tileProvider = useMemo(() =>
    mapTileProviders.find(p => p.name === settings.mapTileProvider) || mapTileProviders[0],
    [settings.mapTileProvider]
  )

  // Handle fit to bounds
  const handleFitBounds = useCallback(() => {
    if (mapRef && measurementBounds && measurementBounds.length > 0) {
      mapRef.fitBounds(measurementBounds, { padding: [50, 50] })
    }
  }, [mapRef, measurementBounds])

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: 5000 }
      if (filters.surveyId) params.survey_id = filters.surveyId
      const response = await api.getMeasurements(params)
      setMeasurements(response.measurements || [])
    } catch (error) {
      console.error('Refresh failed:', error)
    } finally {
      setLoading(false)
    }
  }, [filters.surveyId, setMeasurements])

  // Handle measurement click
  const handleMeasurementClick = useCallback((measurement) => {
    console.log('Measurement clicked:', measurement)
  }, [])

  // Selected track points
  const selectedTrackPoints = useMemo(() => {
    const track = tracks.find(t => t.id === selectedTrackId)
    return track?.points || []
  }, [tracks, selectedTrackId])

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 128px)' }}>
      {/* Controls Drawer */}
      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          width: drawerOpen ? DRAWER_WIDTH : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            position: 'relative',
            height: '100%',
          },
        }}
      >
        <Box sx={{ p: 1, height: '100%', overflow: 'auto' }}>
          <MapControls
            layers={layers}
            onLayerChange={setLayers}
            filters={filters}
            onFilterChange={setFilters}
            settings={settings}
            onSettingsChange={setSettings}
            surveys={surveys}
            totalMeasurements={measurements.length}
            filteredMeasurements={filteredMeasurements.length}
            onRefresh={handleRefresh}
            onFitBounds={handleFitBounds}
          />

          {/* Track Playback Controls */}
          {layers.tracks && tracks.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <TrackPlaybackControls
                tracks={tracks}
                selectedTrackId={selectedTrackId}
                onTrackSelect={setSelectedTrackId}
                trackPoints={selectedTrackPoints}
                currentIndex={trackPlayback.currentIndex}
                onIndexChange={(idx) => setTrackPlayback(p => ({ ...p, currentIndex: idx }))}
                isPlaying={trackPlayback.isPlaying}
                onPlayPause={() => setTrackPlayback(p => ({ ...p, isPlaying: !p.isPlaying }))}
                playbackSpeed={trackPlayback.speed}
                onSpeedChange={(speed) => setTrackPlayback(p => ({ ...p, speed }))}
                colorMode={trackPlayback.colorMode}
                onColorModeChange={(mode) => setTrackPlayback(p => ({ ...p, colorMode: mode }))}
              />
            </Box>
          )}
        </Box>
      </Drawer>

      {/* Map Container */}
      <Box sx={{ flexGrow: 1, position: 'relative' }}>
        {/* Toggle Button */}
        {!drawerOpen && (
          <Tooltip title="Show Controls">
            <IconButton
              onClick={() => setDrawerOpen(true)}
              sx={{
                position: 'absolute',
                top: 10,
                left: 10,
                zIndex: 1000,
                bgcolor: 'background.paper',
                '&:hover': { bgcolor: 'background.paper' },
              }}
            >
              <MenuIcon />
            </IconButton>
          </Tooltip>
        )}

        {/* Loading Indicator */}
        {loading && (
          <Box sx={{
            position: 'absolute',
            top: 10,
            right: 10,
            zIndex: 1000,
            bgcolor: 'primary.main',
            color: 'white',
            px: 2,
            py: 0.5,
            borderRadius: 1,
          }}>
            Loading...
          </Box>
        )}

        {/* Power Legend */}
        <PowerLegend
          style={{
            position: 'absolute',
            bottom: 30,
            right: 10,
            zIndex: 1000,
          }}
        />

        {/* Leaflet Map */}
        <MapContainer
          center={[40.7128, -74.0060]}
          zoom={10}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution={tileProvider.attribution}
            url={tileProvider.url}
          />

          <MapController
            bounds={measurementBounds}
            onMapReady={setMapRef}
          />

          {/* Heatmap Layer */}
          {layers.heatmap && heatmapPoints.length > 0 && (
            <HeatmapLayer
              points={heatmapPoints}
              options={{
                radius: settings.heatmapRadius,
                blur: settings.heatmapBlur,
                maxZoom: 17,
              }}
              visible={layers.heatmap}
            />
          )}

          {/* Marker Clusters */}
          {layers.markers && layers.clusters && (
            <MeasurementCluster
              measurements={filteredMeasurements}
              onMeasurementClick={handleMeasurementClick}
              maxClusterRadius={settings.clusterRadius}
            />
          )}

          {/* Individual Markers (non-clustered) */}
          {layers.markers && !layers.clusters && filteredMeasurements.length < 1000 && (
            <MeasurementCluster
              measurements={filteredMeasurements}
              onMeasurementClick={handleMeasurementClick}
              maxClusterRadius={0}
              disableClusteringAtZoom={1}
            />
          )}

          {/* Track Viewer */}
          {layers.tracks && tracks.length > 0 && (
            <TrackViewer
              tracks={tracks}
              selectedTrackId={selectedTrackId}
              onTrackSelect={setSelectedTrackId}
              colorMode={trackPlayback.colorMode}
            />
          )}
        </MapContainer>
      </Box>
    </Box>
  )
}

export default MapViewer
