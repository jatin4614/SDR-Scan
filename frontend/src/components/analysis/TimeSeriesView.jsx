import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  IconButton,
  Tooltip,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Alert,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
} from '@mui/material'
import {
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  DateRange as DateRangeIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material'
import Plot from 'react-plotly.js'
import { useStore } from '../../store/useStore'
import { api } from '../../services/api'

/**
 * Format frequency for display
 */
function formatFrequency(hz) {
  if (hz >= 1e9) return `${(hz / 1e9).toFixed(3)} GHz`
  if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`
  if (hz >= 1e3) return `${(hz / 1e3).toFixed(3)} kHz`
  return `${hz} Hz`
}

/**
 * Calculate statistics for a data series
 */
function calculateStats(values) {
  if (!values || values.length === 0) return null

  const sorted = [...values].sort((a, b) => a - b)
  const n = values.length

  const sum = values.reduce((a, b) => a + b, 0)
  const mean = sum / n

  const squareDiffs = values.map(v => Math.pow(v - mean, 2))
  const variance = squareDiffs.reduce((a, b) => a + b, 0) / n
  const stdDev = Math.sqrt(variance)

  const min = sorted[0]
  const max = sorted[n - 1]
  const median = n % 2 === 0
    ? (sorted[n / 2 - 1] + sorted[n / 2]) / 2
    : sorted[Math.floor(n / 2)]

  const p25 = sorted[Math.floor(n * 0.25)]
  const p75 = sorted[Math.floor(n * 0.75)]

  // Calculate trend (simple linear regression)
  const xMean = (n - 1) / 2
  let numerator = 0
  let denominator = 0
  values.forEach((y, x) => {
    numerator += (x - xMean) * (y - mean)
    denominator += Math.pow(x - xMean, 2)
  })
  const slope = denominator !== 0 ? numerator / denominator : 0

  return {
    count: n,
    mean,
    stdDev,
    min,
    max,
    median,
    p25,
    p75,
    slope,
    trend: slope > 0.1 ? 'up' : slope < -0.1 ? 'down' : 'flat',
  }
}

/**
 * Time window presets
 */
const timeWindows = [
  { label: '1 min', seconds: 60 },
  { label: '5 min', seconds: 300 },
  { label: '15 min', seconds: 900 },
  { label: '1 hour', seconds: 3600 },
  { label: '6 hours', seconds: 21600 },
  { label: '24 hours', seconds: 86400 },
]

/**
 * Statistics Card
 */
function StatCard({ label, value, unit, trend, color }) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return <TrendingUpIcon fontSize="small" color="success" />
      case 'down': return <TrendingDownIcon fontSize="small" color="error" />
      default: return <TrendingFlatIcon fontSize="small" color="disabled" />
    }
  }

  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 1, px: 2 }}>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" sx={{ color }}>
            {typeof value === 'number' ? value.toFixed(1) : value}
            {unit && <Typography component="span" variant="caption"> {unit}</Typography>}
          </Typography>
          {trend && getTrendIcon()}
        </Box>
      </CardContent>
    </Card>
  )
}

/**
 * TimeSeriesView Component
 *
 * Displays power measurements over time for selected frequencies
 */
function TimeSeriesView({
  spectrumHistory = [],
  selectedFrequencies = [],
  onFrequencyAdd,
  onFrequencyRemove,
}) {
  const { measurements, measurementFilters } = useStore()

  const [timeWindow, setTimeWindow] = useState(300) // 5 minutes default
  const [isLive, setIsLive] = useState(true)
  const [customFreq, setCustomFreq] = useState('')
  const [trackedFreqs, setTrackedFreqs] = useState([])
  const [loading, setLoading] = useState(false)
  const [historicalData, setHistoricalData] = useState({})

  // Initialize with any selected frequencies passed as props
  useEffect(() => {
    if (selectedFrequencies.length > 0) {
      setTrackedFreqs(prev => {
        const newFreqs = selectedFrequencies.filter(f => !prev.includes(f))
        return [...prev, ...newFreqs]
      })
    }
  }, [selectedFrequencies])

  // Extract time series data from spectrum history
  const liveTimeSeriesData = useMemo(() => {
    const data = {}

    trackedFreqs.forEach(freq => {
      data[freq] = {
        timestamps: [],
        powers: [],
      }
    })

    // Process spectrum history to extract power at tracked frequencies
    spectrumHistory.forEach((spectrum, idx) => {
      if (!spectrum?.frequencies || !spectrum?.powers) return

      const timestamp = spectrum.timestamp || new Date(Date.now() - (spectrumHistory.length - idx) * 500).toISOString()

      trackedFreqs.forEach(targetFreq => {
        // Find closest frequency bin
        let closestIdx = 0
        let minDiff = Infinity

        spectrum.frequencies.forEach((f, i) => {
          const diff = Math.abs(f - targetFreq)
          if (diff < minDiff) {
            minDiff = diff
            closestIdx = i
          }
        })

        // Only add if within 1% of target frequency
        if (minDiff / targetFreq < 0.01) {
          data[targetFreq].timestamps.push(timestamp)
          data[targetFreq].powers.push(spectrum.powers[closestIdx])
        }
      })
    })

    return data
  }, [spectrumHistory, trackedFreqs])

  // Load historical data for a frequency
  const loadHistoricalData = useCallback(async (freq) => {
    setLoading(true)
    try {
      const endTime = new Date()
      const startTime = new Date(endTime.getTime() - timeWindow * 1000)

      const response = await api.getMeasurements({
        start_freq: freq - 50000,
        end_freq: freq + 50000,
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        limit: 1000,
      })

      const data = {
        timestamps: [],
        powers: [],
      }

      if (response.measurements) {
        response.measurements.forEach(m => {
          data.timestamps.push(m.timestamp)
          data.powers.push(m.power_dbm)
        })
      }

      setHistoricalData(prev => ({
        ...prev,
        [freq]: data,
      }))
    } catch (error) {
      console.error('Failed to load historical data:', error)
    } finally {
      setLoading(false)
    }
  }, [timeWindow])

  // Add frequency to track
  const handleAddFrequency = useCallback(() => {
    const freq = parseFloat(customFreq) * 1e6
    if (freq > 0 && !trackedFreqs.includes(freq)) {
      setTrackedFreqs(prev => [...prev, freq])
      setCustomFreq('')
      onFrequencyAdd?.(freq)
    }
  }, [customFreq, trackedFreqs, onFrequencyAdd])

  // Remove frequency from tracking
  const handleRemoveFrequency = useCallback((freq) => {
    setTrackedFreqs(prev => prev.filter(f => f !== freq))
    setHistoricalData(prev => {
      const next = { ...prev }
      delete next[freq]
      return next
    })
    onFrequencyRemove?.(freq)
  }, [onFrequencyRemove])

  // Generate color for each frequency
  const getFrequencyColor = (freq, index) => {
    const colors = [
      '#2196f3', '#4caf50', '#ff9800', '#e91e63', '#9c27b0',
      '#00bcd4', '#ff5722', '#607d8b', '#8bc34a', '#ffeb3b',
    ]
    return colors[index % colors.length]
  }

  // Prepare plot data
  const plotData = useMemo(() => {
    return trackedFreqs.map((freq, idx) => {
      const data = isLive ? liveTimeSeriesData[freq] : (historicalData[freq] || { timestamps: [], powers: [] })

      return {
        x: data.timestamps.map(t => new Date(t)),
        y: data.powers,
        type: 'scatter',
        mode: 'lines+markers',
        name: formatFrequency(freq),
        line: { color: getFrequencyColor(freq, idx), width: 2 },
        marker: { size: 4 },
      }
    })
  }, [trackedFreqs, liveTimeSeriesData, historicalData, isLive])

  // Calculate statistics for each tracked frequency
  const statistics = useMemo(() => {
    const stats = {}
    trackedFreqs.forEach(freq => {
      const data = isLive ? liveTimeSeriesData[freq] : (historicalData[freq] || { powers: [] })
      stats[freq] = calculateStats(data.powers)
    })
    return stats
  }, [trackedFreqs, liveTimeSeriesData, historicalData, isLive])

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TimelineIcon color="primary" />
            <Typography variant="h6">Time Series Analysis</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <ToggleButtonGroup
              value={isLive ? 'live' : 'historical'}
              exclusive
              onChange={(e, v) => v && setIsLive(v === 'live')}
              size="small"
            >
              <ToggleButton value="live">
                <Tooltip title="Live data">
                  <PlayIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="historical">
                <Tooltip title="Historical data">
                  <DateRangeIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>

        {/* Frequency Input */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <TextField
            label="Add Frequency (MHz)"
            type="number"
            size="small"
            value={customFreq}
            onChange={(e) => setCustomFreq(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddFrequency()}
            sx={{ width: 180 }}
          />
          <Button
            variant="outlined"
            onClick={handleAddFrequency}
            disabled={!customFreq}
          >
            Track
          </Button>

          {!isLive && (
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Time Window</InputLabel>
              <Select
                value={timeWindow}
                label="Time Window"
                onChange={(e) => setTimeWindow(e.target.value)}
              >
                {timeWindows.map(tw => (
                  <MenuItem key={tw.seconds} value={tw.seconds}>
                    {tw.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>

        {/* Tracked Frequencies */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          {trackedFreqs.map((freq, idx) => (
            <Chip
              key={freq}
              label={formatFrequency(freq)}
              onDelete={() => handleRemoveFrequency(freq)}
              sx={{
                bgcolor: getFrequencyColor(freq, idx),
                color: 'white',
                '& .MuiChip-deleteIcon': { color: 'white' },
              }}
            />
          ))}
          {trackedFreqs.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              Enter a frequency above to start tracking
            </Typography>
          )}
        </Box>

        {/* Time Series Plot */}
        {trackedFreqs.length > 0 && (
          <Box sx={{ height: 350, mb: 2 }}>
            <Plot
              data={plotData}
              layout={{
                autosize: true,
                margin: { l: 50, r: 30, t: 30, b: 50 },
                xaxis: {
                  title: 'Time',
                  type: 'date',
                  gridcolor: '#333',
                },
                yaxis: {
                  title: 'Power (dBm)',
                  gridcolor: '#333',
                  range: [-120, 0],
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#fff' },
                legend: {
                  orientation: 'h',
                  y: -0.2,
                },
                showlegend: true,
              }}
              config={{
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                displaylogo: false,
              }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </Box>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress />
          </Box>
        )}
      </Paper>

      {/* Statistics Cards */}
      {trackedFreqs.length > 0 && (
        <Grid container spacing={2}>
          {trackedFreqs.map((freq, idx) => {
            const stats = statistics[freq]
            if (!stats) return null

            return (
              <Grid item xs={12} md={6} lg={4} key={freq}>
                <Paper sx={{ p: 2 }}>
                  <Typography
                    variant="subtitle1"
                    gutterBottom
                    sx={{ color: getFrequencyColor(freq, idx), fontWeight: 600 }}
                  >
                    {formatFrequency(freq)}
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid item xs={4}>
                      <StatCard
                        label="Mean"
                        value={stats.mean}
                        unit="dBm"
                        trend={stats.trend}
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <StatCard
                        label="Min"
                        value={stats.min}
                        unit="dBm"
                        color="success.main"
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <StatCard
                        label="Max"
                        value={stats.max}
                        unit="dBm"
                        color="error.main"
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <StatCard
                        label="Std Dev"
                        value={stats.stdDev}
                        unit="dB"
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <StatCard
                        label="Samples"
                        value={stats.count}
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <StatCard
                        label="Median"
                        value={stats.median}
                        unit="dBm"
                      />
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            )
          })}
        </Grid>
      )}

      {trackedFreqs.length === 0 && (
        <Alert severity="info">
          Add frequencies to track their power levels over time.
          You can enter frequencies manually or click on peaks in the Signal Analyzer.
        </Alert>
      )}
    </Box>
  )
}

export default TimeSeriesView
