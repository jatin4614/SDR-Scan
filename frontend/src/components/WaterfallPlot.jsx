import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Grid,
  Chip,
} from '@mui/material'
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Fullscreen as FullscreenIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Delete as ClearIcon,
} from '@mui/icons-material'
import Plot from 'react-plotly.js'

// Color scales for waterfall display
const colorScales = {
  viridis: 'Viridis',
  plasma: 'Plasma',
  inferno: 'Inferno',
  magma: 'Magma',
  jet: 'Jet',
  hot: 'Hot',
  electric: 'Electric',
  blackbody: 'Blackbody',
}

function WaterfallPlot({
  data = [],
  frequencies = [],
  timeLabels = [],
  minPower = -120,
  maxPower = -20,
  height = 300,
  onFrequencySelect,
  onTimeSelect,
  title = 'Waterfall Display',
}) {
  const [colorScale, setColorScale] = useState('viridis')
  const [powerRange, setPowerRange] = useState([minPower, maxPower])
  const [isPaused, setIsPaused] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [displayData, setDisplayData] = useState([])
  const containerRef = useRef(null)

  // Buffer for paused state
  const pauseBufferRef = useRef([])

  // Update display data based on pause state
  useEffect(() => {
    if (!isPaused) {
      setDisplayData(data)
      pauseBufferRef.current = [...data]
    }
  }, [data, isPaused])

  // Memoized frequency labels (convert to MHz)
  const freqLabels = useMemo(() => {
    if (!frequencies.length) return []
    const step = Math.max(1, Math.floor(frequencies.length / 10))
    return frequencies.filter((_, i) => i % step === 0).map(f => (f / 1e6).toFixed(2))
  }, [frequencies])

  // Handle click on waterfall
  const handleClick = useCallback((event) => {
    if (!event.points || event.points.length === 0) return

    const point = event.points[0]
    const freqIndex = point.x
    const timeIndex = point.y

    if (onFrequencySelect && frequencies[freqIndex]) {
      onFrequencySelect(frequencies[freqIndex])
    }
    if (onTimeSelect && timeLabels[timeIndex]) {
      onTimeSelect(timeLabels[timeIndex])
    }
  }, [frequencies, timeLabels, onFrequencySelect, onTimeSelect])

  // Clear waterfall data
  const handleClear = useCallback(() => {
    setDisplayData([])
    pauseBufferRef.current = []
  }, [])

  // Zoom controls
  const handleZoomIn = () => setZoomLevel(z => Math.min(z * 1.5, 5))
  const handleZoomOut = () => setZoomLevel(z => Math.max(z / 1.5, 0.5))

  // Prepare heatmap data
  const plotData = useMemo(() => {
    if (!displayData.length) {
      return [{
        z: [[]],
        type: 'heatmap',
        colorscale: colorScale,
        showscale: true,
        colorbar: {
          title: 'dBm',
          titleside: 'right',
          thickness: 15,
          len: 0.9,
        },
        zmin: powerRange[0],
        zmax: powerRange[1],
      }]
    }

    return [{
      z: displayData,
      type: 'heatmap',
      colorscale: colorScale,
      showscale: true,
      colorbar: {
        title: 'dBm',
        titleside: 'right',
        thickness: 15,
        len: 0.9,
        tickfont: { color: '#ffffff' },
        titlefont: { color: '#ffffff' },
      },
      zmin: powerRange[0],
      zmax: powerRange[1],
      hoverongaps: false,
      hovertemplate:
        'Frequency: %{x}<br>' +
        'Time: %{y}<br>' +
        'Power: %{z:.1f} dBm<extra></extra>',
    }]
  }, [displayData, colorScale, powerRange])

  const layout = useMemo(() => ({
    autosize: true,
    height: height * zoomLevel,
    margin: { l: 60, r: 80, t: 40, b: 50 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(19, 47, 76, 0.5)',
    font: { color: '#ffffff', size: 11 },
    title: {
      text: title,
      font: { size: 14, color: '#ffffff' },
    },
    xaxis: {
      title: 'Frequency (MHz)',
      gridcolor: 'rgba(255,255,255,0.1)',
      tickvals: freqLabels.length > 0 ?
        freqLabels.map((_, i) => i * Math.floor(frequencies.length / freqLabels.length)) :
        undefined,
      ticktext: freqLabels.length > 0 ? freqLabels : undefined,
    },
    yaxis: {
      title: 'Time',
      gridcolor: 'rgba(255,255,255,0.1)',
      autorange: 'reversed', // Newest at top
    },
  }), [height, zoomLevel, title, freqLabels, frequencies.length])

  return (
    <Paper sx={{ p: 2 }} ref={containerRef}>
      {/* Header Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle1">{title}</Typography>
          {isPaused && <Chip size="small" label="PAUSED" color="warning" />}
          <Chip
            size="small"
            label={`${displayData.length} rows`}
            variant="outlined"
          />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title={isPaused ? 'Resume' : 'Pause'}>
            <IconButton size="small" onClick={() => setIsPaused(!isPaused)}>
              {isPaused ? <PlayIcon /> : <PauseIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear">
            <IconButton size="small" onClick={handleClear}>
              <ClearIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom In">
            <IconButton size="small" onClick={handleZoomIn}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton size="small" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Settings Row */}
      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={4}>
          <FormControl size="small" fullWidth>
            <InputLabel>Color Scale</InputLabel>
            <Select
              value={colorScale}
              label="Color Scale"
              onChange={(e) => setColorScale(e.target.value)}
            >
              {Object.entries(colorScales).map(([key, label]) => (
                <MenuItem key={key} value={key}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={8}>
          <Typography variant="caption" color="text.secondary">
            Power Range: {powerRange[0]} to {powerRange[1]} dBm
          </Typography>
          <Slider
            value={powerRange}
            onChange={(e, v) => setPowerRange(v)}
            min={-140}
            max={0}
            valueLabelDisplay="auto"
            size="small"
          />
        </Grid>
      </Grid>

      {/* Waterfall Plot */}
      <Box sx={{
        overflow: 'auto',
        maxHeight: height * zoomLevel + 50,
        '& .js-plotly-plot': { width: '100%' }
      }}>
        <Plot
          data={plotData}
          layout={layout}
          config={{
            responsive: true,
            displayModeBar: false,
            scrollZoom: true,
          }}
          onClick={handleClick}
          style={{ width: '100%' }}
        />
      </Box>

      {/* Empty State */}
      {displayData.length === 0 && (
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
        }}>
          <Typography color="text.secondary">
            No data yet. Start spectrum streaming to see the waterfall display.
          </Typography>
        </Box>
      )}
    </Paper>
  )
}

export default WaterfallPlot
