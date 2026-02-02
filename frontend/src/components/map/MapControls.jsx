import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  FormGroup,
  Chip,
  Divider,
  Collapse,
  IconButton,
  TextField,
  Grid,
  Tooltip,
  Button,
} from '@mui/material'
import {
  Layers as LayersIcon,
  FilterList as FilterIcon,
  Tune as TuneIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Refresh as RefreshIcon,
  Map as MapIcon,
} from '@mui/icons-material'

// Predefined frequency bands for filtering
const frequencyBands = [
  { name: 'All', start: 0, end: 10e9 },
  { name: 'HF (3-30 MHz)', start: 3e6, end: 30e6 },
  { name: 'VHF (30-300 MHz)', start: 30e6, end: 300e6 },
  { name: 'UHF (300-3000 MHz)', start: 300e6, end: 3000e6 },
  { name: 'FM Broadcast', start: 88e6, end: 108e6 },
  { name: 'VHF TV', start: 54e6, end: 216e6 },
  { name: 'UHF TV', start: 470e6, end: 806e6 },
  { name: 'Cellular', start: 698e6, end: 960e6 },
  { name: 'ISM 433', start: 433e6, end: 435e6 },
  { name: 'ISM 915', start: 902e6, end: 928e6 },
  { name: 'WiFi 2.4', start: 2.4e9, end: 2.5e9 },
]

// Map tile providers
const mapTileProviders = [
  {
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
  },
  {
    name: 'CartoDB Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CARTO',
  },
  {
    name: 'CartoDB Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CARTO',
  },
  {
    name: 'Esri Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
  {
    name: 'Esri Topo',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
]

/**
 * MapControls Component
 *
 * Provides layer controls, filtering options, and display settings for the map
 */
function MapControls({
  // Layer visibility
  layers = {
    markers: true,
    heatmap: false,
    tracks: true,
    clusters: true,
  },
  onLayerChange,

  // Filters
  filters = {
    frequencyBand: 'All',
    customFreqStart: null,
    customFreqEnd: null,
    powerRange: [-120, -20],
    surveyId: null,
    timeRange: null,
  },
  onFilterChange,

  // Display settings
  settings = {
    mapTileProvider: 'OpenStreetMap',
    markerSize: 8,
    heatmapRadius: 25,
    heatmapBlur: 15,
    clusterRadius: 80,
    trackWidth: 4,
  },
  onSettingsChange,

  // Data
  surveys = [],
  totalMeasurements = 0,
  filteredMeasurements = 0,

  // Actions
  onRefresh,
  onFitBounds,
}) {
  const [expandedSections, setExpandedSections] = useState({
    layers: true,
    filters: true,
    display: false,
  })

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const handleLayerToggle = (layer) => {
    onLayerChange?.({ ...layers, [layer]: !layers[layer] })
  }

  const handleFilterUpdate = (key, value) => {
    onFilterChange?.({ ...filters, [key]: value })
  }

  const handleSettingsUpdate = (key, value) => {
    onSettingsChange?.({ ...settings, [key]: value })
  }

  const formatFrequency = (hz) => {
    if (hz >= 1e9) return `${(hz / 1e9).toFixed(1)} GHz`
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(1)} MHz`
    return `${(hz / 1e3).toFixed(1)} kHz`
  }

  return (
    <Paper sx={{ p: 2, maxHeight: '80vh', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <MapIcon color="primary" />
          <Typography variant="subtitle1">Map Controls</Typography>
        </Box>
        <Box>
          <Tooltip title="Fit to Data">
            <IconButton size="small" onClick={onFitBounds}>
              <MapIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={onRefresh}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Data Summary */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Chip
          size="small"
          label={`${filteredMeasurements.toLocaleString()} points`}
          color="primary"
        />
        {totalMeasurements !== filteredMeasurements && (
          <Chip
            size="small"
            label={`of ${totalMeasurements.toLocaleString()}`}
            variant="outlined"
          />
        )}
      </Box>

      {/* Layers Section */}
      <Box sx={{ mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            py: 1,
          }}
          onClick={() => toggleSection('layers')}
        >
          <LayersIcon sx={{ mr: 1, fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>Layers</Typography>
          {expandedSections.layers ? <CollapseIcon /> : <ExpandIcon />}
        </Box>
        <Collapse in={expandedSections.layers}>
          <FormGroup sx={{ pl: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={layers.markers}
                  onChange={() => handleLayerToggle('markers')}
                />
              }
              label="Markers"
            />
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={layers.clusters}
                  onChange={() => handleLayerToggle('clusters')}
                />
              }
              label="Clustering"
            />
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={layers.heatmap}
                  onChange={() => handleLayerToggle('heatmap')}
                />
              }
              label="Heatmap"
            />
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={layers.tracks}
                  onChange={() => handleLayerToggle('tracks')}
                />
              }
              label="GPS Tracks"
            />
          </FormGroup>
        </Collapse>
      </Box>

      <Divider sx={{ my: 1 }} />

      {/* Filters Section */}
      <Box sx={{ mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            py: 1,
          }}
          onClick={() => toggleSection('filters')}
        >
          <FilterIcon sx={{ mr: 1, fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>Filters</Typography>
          {expandedSections.filters ? <CollapseIcon /> : <ExpandIcon />}
        </Box>
        <Collapse in={expandedSections.filters}>
          <Box sx={{ pl: 1 }}>
            {/* Survey Filter */}
            <FormControl size="small" fullWidth sx={{ mb: 2 }}>
              <InputLabel>Survey</InputLabel>
              <Select
                value={filters.surveyId || ''}
                label="Survey"
                onChange={(e) => handleFilterUpdate('surveyId', e.target.value || null)}
              >
                <MenuItem value="">All Surveys</MenuItem>
                {surveys.map(survey => (
                  <MenuItem key={survey.id} value={survey.id}>
                    {survey.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Frequency Band Filter */}
            <FormControl size="small" fullWidth sx={{ mb: 2 }}>
              <InputLabel>Frequency Band</InputLabel>
              <Select
                value={filters.frequencyBand}
                label="Frequency Band"
                onChange={(e) => {
                  const band = frequencyBands.find(b => b.name === e.target.value)
                  handleFilterUpdate('frequencyBand', e.target.value)
                  if (band && band.name !== 'All') {
                    handleFilterUpdate('customFreqStart', band.start)
                    handleFilterUpdate('customFreqEnd', band.end)
                  }
                }}
              >
                {frequencyBands.map(band => (
                  <MenuItem key={band.name} value={band.name}>
                    {band.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Custom Frequency Range */}
            {filters.frequencyBand === 'All' && (
              <Grid container spacing={1} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <TextField
                    label="Min Freq (MHz)"
                    type="number"
                    size="small"
                    fullWidth
                    value={filters.customFreqStart ? filters.customFreqStart / 1e6 : ''}
                    onChange={(e) => handleFilterUpdate('customFreqStart',
                      e.target.value ? parseFloat(e.target.value) * 1e6 : null
                    )}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    label="Max Freq (MHz)"
                    type="number"
                    size="small"
                    fullWidth
                    value={filters.customFreqEnd ? filters.customFreqEnd / 1e6 : ''}
                    onChange={(e) => handleFilterUpdate('customFreqEnd',
                      e.target.value ? parseFloat(e.target.value) * 1e6 : null
                    )}
                  />
                </Grid>
              </Grid>
            )}

            {/* Power Range Filter */}
            <Typography variant="caption" color="text.secondary">
              Power Range: {filters.powerRange[0]} to {filters.powerRange[1]} dBm
            </Typography>
            <Slider
              value={filters.powerRange}
              onChange={(e, v) => handleFilterUpdate('powerRange', v)}
              min={-140}
              max={0}
              size="small"
              valueLabelDisplay="auto"
            />
          </Box>
        </Collapse>
      </Box>

      <Divider sx={{ my: 1 }} />

      {/* Display Settings Section */}
      <Box>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            py: 1,
          }}
          onClick={() => toggleSection('display')}
        >
          <TuneIcon sx={{ mr: 1, fontSize: 20 }} />
          <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>Display Settings</Typography>
          {expandedSections.display ? <CollapseIcon /> : <ExpandIcon />}
        </Box>
        <Collapse in={expandedSections.display}>
          <Box sx={{ pl: 1 }}>
            {/* Map Tile Provider */}
            <FormControl size="small" fullWidth sx={{ mb: 2 }}>
              <InputLabel>Map Style</InputLabel>
              <Select
                value={settings.mapTileProvider}
                label="Map Style"
                onChange={(e) => handleSettingsUpdate('mapTileProvider', e.target.value)}
              >
                {mapTileProviders.map(provider => (
                  <MenuItem key={provider.name} value={provider.name}>
                    {provider.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Marker Size */}
            <Typography variant="caption" color="text.secondary">
              Marker Size: {settings.markerSize}px
            </Typography>
            <Slider
              value={settings.markerSize}
              onChange={(e, v) => handleSettingsUpdate('markerSize', v)}
              min={4}
              max={20}
              size="small"
            />

            {/* Heatmap Settings */}
            {layers.heatmap && (
              <>
                <Typography variant="caption" color="text.secondary">
                  Heatmap Radius: {settings.heatmapRadius}px
                </Typography>
                <Slider
                  value={settings.heatmapRadius}
                  onChange={(e, v) => handleSettingsUpdate('heatmapRadius', v)}
                  min={10}
                  max={50}
                  size="small"
                />

                <Typography variant="caption" color="text.secondary">
                  Heatmap Blur: {settings.heatmapBlur}px
                </Typography>
                <Slider
                  value={settings.heatmapBlur}
                  onChange={(e, v) => handleSettingsUpdate('heatmapBlur', v)}
                  min={5}
                  max={30}
                  size="small"
                />
              </>
            )}

            {/* Cluster Settings */}
            {layers.clusters && (
              <>
                <Typography variant="caption" color="text.secondary">
                  Cluster Radius: {settings.clusterRadius}px
                </Typography>
                <Slider
                  value={settings.clusterRadius}
                  onChange={(e, v) => handleSettingsUpdate('clusterRadius', v)}
                  min={20}
                  max={150}
                  size="small"
                />
              </>
            )}

            {/* Track Settings */}
            {layers.tracks && (
              <>
                <Typography variant="caption" color="text.secondary">
                  Track Width: {settings.trackWidth}px
                </Typography>
                <Slider
                  value={settings.trackWidth}
                  onChange={(e, v) => handleSettingsUpdate('trackWidth', v)}
                  min={1}
                  max={10}
                  size="small"
                />
              </>
            )}
          </Box>
        </Collapse>
      </Box>

      {/* Reset Button */}
      <Box sx={{ mt: 2, textAlign: 'center' }}>
        <Button
          size="small"
          onClick={() => {
            onFilterChange?.({
              frequencyBand: 'All',
              customFreqStart: null,
              customFreqEnd: null,
              powerRange: [-120, -20],
              surveyId: null,
              timeRange: null,
            })
          }}
        >
          Reset Filters
        </Button>
      </Box>
    </Paper>
  )
}

export { mapTileProviders, frequencyBands }
export default MapControls
