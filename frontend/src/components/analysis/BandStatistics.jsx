import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  IconButton,
  Tooltip,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Collapse,
  Alert,
  AlertTitle,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import {
  Analytics as AnalyticsIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  SignalCellular4Bar as SignalIcon,
  Speed as OccupancyIcon,
  TrendingUp as PeakIcon,
  Refresh as RefreshIcon,
  BarChart as ChartIcon,
} from '@mui/icons-material'
import Plot from 'react-plotly.js'
import { useStore } from '../../store/useStore'

// Predefined frequency bands for analysis
const frequencyBands = [
  { id: 'hf', name: 'HF', start: 3e6, end: 30e6, color: '#9c27b0' },
  { id: 'vhf-low', name: 'VHF Low', start: 30e6, end: 88e6, color: '#673ab7' },
  { id: 'fm', name: 'FM Broadcast', start: 88e6, end: 108e6, color: '#2196f3' },
  { id: 'air', name: 'Air Band', start: 108e6, end: 137e6, color: '#00bcd4' },
  { id: 'vhf-high', name: 'VHF High', start: 137e6, end: 174e6, color: '#009688' },
  { id: 'vhf-tv', name: 'VHF TV', start: 174e6, end: 216e6, color: '#4caf50' },
  { id: 'uhf-low', name: 'UHF Low', start: 216e6, end: 450e6, color: '#8bc34a' },
  { id: 'uhf-tv', name: 'UHF TV', start: 470e6, end: 698e6, color: '#cddc39' },
  { id: 'cell-700', name: 'Cellular 700', start: 698e6, end: 806e6, color: '#ffeb3b' },
  { id: 'cell-850', name: 'Cellular 850', start: 824e6, end: 894e6, color: '#ffc107' },
  { id: 'ism-915', name: 'ISM 915', start: 902e6, end: 928e6, color: '#ff9800' },
  { id: 'cell-1900', name: 'Cellular 1900', start: 1850e6, end: 1990e6, color: '#ff5722' },
  { id: 'wifi-2g', name: 'WiFi 2.4G', start: 2400e6, end: 2483.5e6, color: '#e91e63' },
  { id: 'wifi-5g', name: 'WiFi 5G', start: 5150e6, end: 5850e6, color: '#f44336' },
]

/**
 * Format frequency for display
 */
function formatFrequency(hz) {
  if (hz >= 1e9) return `${(hz / 1e9).toFixed(2)} GHz`
  if (hz >= 1e6) return `${(hz / 1e6).toFixed(1)} MHz`
  if (hz >= 1e3) return `${(hz / 1e3).toFixed(1)} kHz`
  return `${hz} Hz`
}

/**
 * Calculate occupancy for a frequency band
 * Occupancy is the percentage of measurements above a threshold
 */
function calculateOccupancy(powers, threshold = -90) {
  if (!powers || powers.length === 0) return 0
  const aboveThreshold = powers.filter(p => p > threshold).length
  return (aboveThreshold / powers.length) * 100
}

/**
 * Calculate band statistics from spectrum data
 */
function calculateBandStats(frequencies, powers, band, noiseThreshold = -100) {
  if (!frequencies || !powers || frequencies.length === 0) {
    return null
  }

  // Find indices within this band
  const bandIndices = []
  frequencies.forEach((freq, idx) => {
    if (freq >= band.start && freq <= band.end) {
      bandIndices.push(idx)
    }
  })

  if (bandIndices.length === 0) return null

  const bandPowers = bandIndices.map(i => powers[i])
  const bandFreqs = bandIndices.map(i => frequencies[i])

  // Calculate statistics
  const min = Math.min(...bandPowers)
  const max = Math.max(...bandPowers)
  const mean = bandPowers.reduce((a, b) => a + b, 0) / bandPowers.length
  const occupancy = calculateOccupancy(bandPowers)

  // Find peak frequency
  const maxIdx = bandPowers.indexOf(max)
  const peakFreq = bandFreqs[maxIdx]

  // Count active channels (above noise + 10dB)
  const activeThreshold = noiseThreshold + 10
  const activeChannels = bandPowers.filter(p => p > activeThreshold).length

  // Calculate noise floor estimate (lower quartile)
  const sorted = [...bandPowers].sort((a, b) => a - b)
  const noiseFloor = sorted[Math.floor(sorted.length * 0.25)] || min

  return {
    band,
    sampleCount: bandPowers.length,
    min,
    max,
    mean,
    peakFreq,
    peakPower: max,
    occupancy,
    activeChannels,
    noiseFloor,
    bandwidth: band.end - band.start,
  }
}

/**
 * Occupancy Bar
 */
function OccupancyBar({ value, color }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ flexGrow: 1 }}>
        <LinearProgress
          variant="determinate"
          value={Math.min(100, value)}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'background.paper',
            '& .MuiLinearProgress-bar': {
              bgcolor: color,
              borderRadius: 4,
            },
          }}
        />
      </Box>
      <Typography variant="caption" sx={{ minWidth: 40, textAlign: 'right' }}>
        {value.toFixed(1)}%
      </Typography>
    </Box>
  )
}

/**
 * Band Detail Card
 */
function BandDetailCard({ stats, onSelect }) {
  const [expanded, setExpanded] = useState(false)

  if (!stats) return null

  const getOccupancyColor = (occ) => {
    if (occ >= 80) return 'error.main'
    if (occ >= 50) return 'warning.main'
    if (occ >= 20) return 'success.main'
    return 'info.main'
  }

  return (
    <Card
      variant="outlined"
      sx={{
        borderLeft: 4,
        borderLeftColor: stats.band.color,
        cursor: 'pointer',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <CardContent sx={{ py: 1.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {stats.band.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatFrequency(stats.band.start)} - {formatFrequency(stats.band.end)}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              size="small"
              label={`${stats.occupancy.toFixed(0)}%`}
              sx={{
                bgcolor: getOccupancyColor(stats.occupancy),
                color: 'white',
              }}
            />
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </Box>
        </Box>

        <Collapse in={expanded}>
          <Grid container spacing={1} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Peak Power</Typography>
              <Typography variant="body2">{stats.peakPower.toFixed(1)} dBm</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Peak Frequency</Typography>
              <Typography variant="body2">{formatFrequency(stats.peakFreq)}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Mean Power</Typography>
              <Typography variant="body2">{stats.mean.toFixed(1)} dBm</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Noise Floor</Typography>
              <Typography variant="body2">{stats.noiseFloor.toFixed(1)} dBm</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Active Channels</Typography>
              <Typography variant="body2">{stats.activeChannels}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Samples</Typography>
              <Typography variant="body2">{stats.sampleCount}</Typography>
            </Grid>
          </Grid>
        </Collapse>
      </CardContent>
    </Card>
  )
}

/**
 * BandStatistics Component
 *
 * Displays occupancy statistics and activity for frequency bands
 */
function BandStatistics({ spectrumData, spectrumHistory = [] }) {
  const [viewMode, setViewMode] = useState('cards') // 'cards', 'table', 'chart'
  const [sortBy, setSortBy] = useState('occupancy') // 'name', 'occupancy', 'peakPower'
  const [sortOrder, setSortOrder] = useState('desc')
  const [noiseThreshold, setNoiseThreshold] = useState(-100)

  // Calculate statistics for all bands
  const bandStats = useMemo(() => {
    if (!spectrumData?.frequencies || !spectrumData?.powers) {
      return []
    }

    const stats = frequencyBands
      .map(band => calculateBandStats(
        spectrumData.frequencies,
        spectrumData.powers,
        band,
        noiseThreshold
      ))
      .filter(Boolean)

    // Sort
    stats.sort((a, b) => {
      let aVal, bVal
      switch (sortBy) {
        case 'name':
          aVal = a.band.name
          bVal = b.band.name
          break
        case 'peakPower':
          aVal = a.peakPower
          bVal = b.peakPower
          break
        case 'occupancy':
        default:
          aVal = a.occupancy
          bVal = b.occupancy
      }

      if (typeof aVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })

    return stats
  }, [spectrumData, noiseThreshold, sortBy, sortOrder])

  // Aggregate statistics
  const aggregateStats = useMemo(() => {
    if (bandStats.length === 0) return null

    const totalOccupancy = bandStats.reduce((sum, s) => sum + s.occupancy, 0) / bandStats.length
    const maxPeak = Math.max(...bandStats.map(s => s.peakPower))
    const maxPeakBand = bandStats.find(s => s.peakPower === maxPeak)
    const mostActive = bandStats.reduce((max, s) => s.occupancy > max.occupancy ? s : max, bandStats[0])

    return {
      totalBands: bandStats.length,
      avgOccupancy: totalOccupancy,
      maxPeakPower: maxPeak,
      maxPeakBand,
      mostActiveBand: mostActive,
    }
  }, [bandStats])

  // Prepare chart data
  const chartData = useMemo(() => {
    if (bandStats.length === 0) return []

    return [{
      x: bandStats.map(s => s.band.name),
      y: bandStats.map(s => s.occupancy),
      type: 'bar',
      marker: {
        color: bandStats.map(s => s.band.color),
      },
      text: bandStats.map(s => `${s.occupancy.toFixed(1)}%`),
      textposition: 'outside',
    }]
  }, [bandStats])

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AnalyticsIcon color="primary" />
            <Typography variant="h6">Band Statistics</Typography>
            <Chip size="small" label={`${bandStats.length} bands`} />
          </Box>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(e, v) => v && setViewMode(v)}
            size="small"
          >
            <ToggleButton value="cards">
              <Tooltip title="Card View">
                <OccupancyIcon fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="table">
              <Tooltip title="Table View">
                <ChartIcon fontSize="small" />
              </Tooltip>
            </ToggleButton>
            <ToggleButton value="chart">
              <Tooltip title="Chart View">
                <PeakIcon fontSize="small" />
              </Tooltip>
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Aggregate Statistics */}
        {aggregateStats && (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Avg Occupancy</Typography>
                  <Typography variant="h6">{aggregateStats.avgOccupancy.toFixed(1)}%</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Max Peak</Typography>
                  <Typography variant="h6">{aggregateStats.maxPeakPower.toFixed(1)} dBm</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Peak Band</Typography>
                  <Typography variant="body2" noWrap>
                    {aggregateStats.maxPeakBand?.band.name || '-'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Most Active</Typography>
                  <Typography variant="body2" noWrap>
                    {aggregateStats.mostActiveBand?.band.name || '-'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* No data warning */}
        {!spectrumData && (
          <Alert severity="info">
            <AlertTitle>No Spectrum Data</AlertTitle>
            Start a spectrum scan to see band statistics.
          </Alert>
        )}

        {/* Card View */}
        {viewMode === 'cards' && bandStats.length > 0 && (
          <Grid container spacing={2}>
            {bandStats.map(stats => (
              <Grid item xs={12} sm={6} md={4} key={stats.band.id}>
                <BandDetailCard stats={stats} />
              </Grid>
            ))}
          </Grid>
        )}

        {/* Table View */}
        {viewMode === 'table' && bandStats.length > 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleSort('name')}
                  >
                    Band {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </TableCell>
                  <TableCell>Range</TableCell>
                  <TableCell
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleSort('occupancy')}
                  >
                    Occupancy {sortBy === 'occupancy' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </TableCell>
                  <TableCell
                    sx={{ cursor: 'pointer' }}
                    onClick={() => handleSort('peakPower')}
                  >
                    Peak {sortBy === 'peakPower' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </TableCell>
                  <TableCell>Mean</TableCell>
                  <TableCell>Noise Floor</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bandStats.map(stats => (
                  <TableRow key={stats.band.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box
                          sx={{
                            width: 12,
                            height: 12,
                            borderRadius: '50%',
                            bgcolor: stats.band.color,
                          }}
                        />
                        <Typography variant="body2">{stats.band.name}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {formatFrequency(stats.band.start)} - {formatFrequency(stats.band.end)}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ width: 150 }}>
                      <OccupancyBar value={stats.occupancy} color={stats.band.color} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{stats.peakPower.toFixed(1)} dBm</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{stats.mean.toFixed(1)} dBm</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{stats.noiseFloor.toFixed(1)} dBm</Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Chart View */}
        {viewMode === 'chart' && bandStats.length > 0 && (
          <Box sx={{ height: 400 }}>
            <Plot
              data={chartData}
              layout={{
                autosize: true,
                margin: { l: 50, r: 30, t: 30, b: 100 },
                xaxis: {
                  title: 'Frequency Band',
                  tickangle: -45,
                  gridcolor: '#333',
                },
                yaxis: {
                  title: 'Occupancy (%)',
                  range: [0, 100],
                  gridcolor: '#333',
                },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#fff' },
                bargap: 0.3,
              }}
              config={{
                displayModeBar: false,
                displaylogo: false,
              }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </Box>
        )}
      </Paper>

      {/* Band Legend */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>Frequency Band Legend</Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {frequencyBands.map(band => (
            <Chip
              key={band.id}
              size="small"
              label={`${band.name}: ${formatFrequency(band.start)}-${formatFrequency(band.end)}`}
              sx={{
                bgcolor: band.color,
                color: 'white',
              }}
            />
          ))}
        </Box>
      </Paper>
    </Box>
  )
}

export default BandStatistics
