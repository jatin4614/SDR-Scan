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
  TableSortLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Alert,
  AlertTitle,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  LinearProgress,
  Collapse,
  Badge,
} from '@mui/material'
import {
  SignalCellular4Bar as SignalIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Info as InfoIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material'
import { useStore } from '../../store/useStore'
import { api } from '../../services/api'

// Known frequency allocations for identification
const knownFrequencies = [
  { name: 'FM Radio', start: 88e6, end: 108e6, type: 'broadcast' },
  { name: 'VHF TV Low', start: 54e6, end: 88e6, type: 'broadcast' },
  { name: 'VHF TV High', start: 174e6, end: 216e6, type: 'broadcast' },
  { name: 'UHF TV', start: 470e6, end: 806e6, type: 'broadcast' },
  { name: 'Air Band', start: 108e6, end: 137e6, type: 'aviation' },
  { name: 'Marine VHF', start: 156e6, end: 162e6, type: 'maritime' },
  { name: 'Public Safety', start: 138e6, end: 174e6, type: 'safety' },
  { name: 'Amateur 2m', start: 144e6, end: 148e6, type: 'amateur' },
  { name: 'Amateur 70cm', start: 420e6, end: 450e6, type: 'amateur' },
  { name: 'Cellular 700', start: 698e6, end: 806e6, type: 'cellular' },
  { name: 'Cellular 850', start: 824e6, end: 894e6, type: 'cellular' },
  { name: 'Cellular 1900', start: 1850e6, end: 1990e6, type: 'cellular' },
  { name: 'ISM 433', start: 433.05e6, end: 434.79e6, type: 'ism' },
  { name: 'ISM 915', start: 902e6, end: 928e6, type: 'ism' },
  { name: 'WiFi 2.4G', start: 2400e6, end: 2483.5e6, type: 'ism' },
  { name: 'WiFi 5G', start: 5150e6, end: 5850e6, type: 'ism' },
  { name: 'GPS L1', start: 1575.42e6 - 10e6, end: 1575.42e6 + 10e6, type: 'navigation' },
  { name: 'ADS-B', start: 1090e6 - 1e6, end: 1090e6 + 1e6, type: 'aviation' },
]

// Signal type colors
const typeColors = {
  broadcast: '#2196f3',
  aviation: '#00bcd4',
  maritime: '#009688',
  safety: '#ff5722',
  amateur: '#9c27b0',
  cellular: '#e91e63',
  ism: '#4caf50',
  navigation: '#ff9800',
  unknown: '#607d8b',
}

/**
 * Format frequency for display
 */
function formatFrequency(hz) {
  if (hz >= 1e9) return `${(hz / 1e9).toFixed(4)} GHz`
  if (hz >= 1e6) return `${(hz / 1e6).toFixed(4)} MHz`
  if (hz >= 1e3) return `${(hz / 1e3).toFixed(3)} kHz`
  return `${hz} Hz`
}

/**
 * Identify frequency band based on known allocations
 */
function identifyFrequency(freq) {
  for (const band of knownFrequencies) {
    if (freq >= band.start && freq <= band.end) {
      return band
    }
  }
  return null
}

/**
 * Simple peak detection algorithm
 */
function detectPeaks(frequencies, powers, options = {}) {
  const {
    threshold = -80,          // Minimum power threshold
    minProminence = 10,       // Minimum prominence above noise
    minDistance = 5,          // Minimum distance between peaks (in bins)
  } = options

  if (!frequencies || !powers || frequencies.length === 0) return []

  // Calculate noise floor estimate (median of bottom 25%)
  const sortedPowers = [...powers].sort((a, b) => a - b)
  const noiseFloorIdx = Math.floor(sortedPowers.length * 0.25)
  const noiseFloor = sortedPowers[noiseFloorIdx] || -120

  const peaks = []
  const n = powers.length

  for (let i = 1; i < n - 1; i++) {
    const power = powers[i]

    // Check if this is a local maximum
    if (power > powers[i - 1] && power > powers[i + 1]) {
      // Check threshold
      if (power < threshold) continue

      // Check prominence above noise
      const prominence = power - noiseFloor
      if (prominence < minProminence) continue

      // Check minimum distance from existing peaks
      const tooClose = peaks.some(p => Math.abs(p.binIndex - i) < minDistance)
      if (tooClose) continue

      const knownBand = identifyFrequency(frequencies[i])

      peaks.push({
        frequency: frequencies[i],
        power: power,
        binIndex: i,
        prominence: prominence,
        noiseFloor: noiseFloor,
        snr: prominence,
        knownBand: knownBand,
        type: knownBand?.type || 'unknown',
      })
    }
  }

  // Sort by power (strongest first)
  return peaks.sort((a, b) => b.power - a.power)
}

/**
 * Signal Tag Dialog
 */
function SignalTagDialog({ open, onClose, signal, onSave }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [modulation, setModulation] = useState('')
  const [tags, setTags] = useState('')

  useEffect(() => {
    if (signal) {
      setName(signal.name || signal.knownBand?.name || '')
      setDescription(signal.description || '')
      setModulation(signal.modulation || '')
      setTags(signal.tags?.join(', ') || '')
    }
  }, [signal])

  const handleSave = () => {
    onSave({
      ...signal,
      name,
      description,
      modulation,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean),
    })
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Tag Signal at {signal ? formatFrequency(signal.frequency) : ''}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Signal Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Local FM Station"
          />
          <TextField
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Additional notes about this signal..."
          />
          <FormControl fullWidth>
            <InputLabel>Modulation Type</InputLabel>
            <Select
              value={modulation}
              label="Modulation Type"
              onChange={(e) => setModulation(e.target.value)}
            >
              <MenuItem value="">Unknown</MenuItem>
              <MenuItem value="AM">AM</MenuItem>
              <MenuItem value="FM">FM</MenuItem>
              <MenuItem value="SSB">SSB (Single Sideband)</MenuItem>
              <MenuItem value="CW">CW (Morse Code)</MenuItem>
              <MenuItem value="FSK">FSK</MenuItem>
              <MenuItem value="PSK">PSK</MenuItem>
              <MenuItem value="QAM">QAM</MenuItem>
              <MenuItem value="OFDM">OFDM</MenuItem>
              <MenuItem value="Spread Spectrum">Spread Spectrum</MenuItem>
              <MenuItem value="Digital">Digital (Other)</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Tags"
            fullWidth
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Comma-separated tags: broadcast, local, interference"
            helperText="Add custom tags to categorize this signal"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>Save</Button>
      </DialogActions>
    </Dialog>
  )
}

/**
 * Peak Signal Row
 */
function PeakSignalRow({ peak, index, onTag, onBookmark, bookmarked }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <TableRow
        hover
        sx={{
          cursor: 'pointer',
          bgcolor: peak.knownBand ? 'action.hover' : 'inherit',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <TableCell>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              #{index + 1}
            </Typography>
            {expanded ? <CollapseIcon fontSize="small" /> : <ExpandIcon fontSize="small" />}
          </Box>
        </TableCell>
        <TableCell>
          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
            {formatFrequency(peak.frequency)}
          </Typography>
        </TableCell>
        <TableCell>
          <Chip
            size="small"
            label={`${peak.power.toFixed(1)} dBm`}
            sx={{
              bgcolor: peak.power >= -40 ? 'error.main' :
                       peak.power >= -60 ? 'warning.main' :
                       peak.power >= -80 ? 'success.main' : 'info.main',
              color: 'white',
            }}
          />
        </TableCell>
        <TableCell>
          <Typography variant="body2" color="text.secondary">
            {peak.snr.toFixed(1)} dB
          </Typography>
        </TableCell>
        <TableCell>
          {peak.knownBand ? (
            <Chip
              size="small"
              label={peak.knownBand.name}
              sx={{
                bgcolor: typeColors[peak.type] || typeColors.unknown,
                color: 'white',
              }}
            />
          ) : (
            <Typography variant="caption" color="text.secondary">
              Unknown
            </Typography>
          )}
        </TableCell>
        <TableCell align="right">
          <Tooltip title={bookmarked ? "Remove bookmark" : "Bookmark signal"}>
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); onBookmark(peak); }}>
              {bookmarked ? <BookmarkIcon color="primary" /> : <BookmarkBorderIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Tag signal">
            <IconButton size="small" onClick={(e) => { e.stopPropagation(); onTag(peak); }}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={6} sx={{ py: 0 }}>
          <Collapse in={expanded}>
            <Box sx={{ py: 2, px: 2, bgcolor: 'background.default' }}>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">Noise Floor</Typography>
                  <Typography variant="body2">{peak.noiseFloor.toFixed(1)} dBm</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">Prominence</Typography>
                  <Typography variant="body2">{peak.prominence.toFixed(1)} dB</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="caption" color="text.secondary">Type</Typography>
                  <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>{peak.type}</Typography>
                </Grid>
                {peak.knownBand && (
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.secondary">Band Range</Typography>
                    <Typography variant="body2">
                      {formatFrequency(peak.knownBand.start)} - {formatFrequency(peak.knownBand.end)}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  )
}

/**
 * SignalAnalyzer Component
 *
 * Analyzes spectrum data to detect and classify signals of interest
 */
function SignalAnalyzer({ spectrumData, onSignalSelect }) {
  const { signals, addSignal, addNotification } = useStore()
  const [detectionSettings, setDetectionSettings] = useState({
    threshold: -80,
    minProminence: 10,
    minDistance: 5,
    maxPeaks: 20,
  })
  const [detectedPeaks, setDetectedPeaks] = useState([])
  const [bookmarkedFreqs, setBookmarkedFreqs] = useState(new Set())
  const [tagDialogOpen, setTagDialogOpen] = useState(false)
  const [selectedSignal, setSelectedSignal] = useState(null)
  const [sortConfig, setSortConfig] = useState({ key: 'power', direction: 'desc' })
  const [showSettings, setShowSettings] = useState(false)

  // Detect peaks when spectrum data changes
  useEffect(() => {
    if (spectrumData?.frequencies && spectrumData?.powers) {
      const peaks = detectPeaks(
        spectrumData.frequencies,
        spectrumData.powers,
        {
          threshold: detectionSettings.threshold,
          minProminence: detectionSettings.minProminence,
          minDistance: detectionSettings.minDistance,
        }
      ).slice(0, detectionSettings.maxPeaks)

      setDetectedPeaks(peaks)
    }
  }, [spectrumData, detectionSettings])

  // Handle bookmark toggle
  const handleBookmark = useCallback((peak) => {
    setBookmarkedFreqs(prev => {
      const next = new Set(prev)
      if (next.has(peak.frequency)) {
        next.delete(peak.frequency)
      } else {
        next.add(peak.frequency)
      }
      return next
    })
  }, [])

  // Handle tagging
  const handleTag = useCallback((peak) => {
    setSelectedSignal(peak)
    setTagDialogOpen(true)
  }, [])

  // Save tagged signal
  const handleSaveSignal = useCallback(async (signal) => {
    try {
      const signalData = {
        center_frequency: signal.frequency,
        bandwidth: 100000, // Default 100kHz bandwidth estimate
        power_dbm: signal.power,
        modulation: signal.modulation,
        description: signal.description,
        tags: signal.tags,
      }

      const response = await api.createSignal(signalData)
      addSignal(response)
      addNotification({
        type: 'success',
        message: `Signal tagged: ${signal.name || formatFrequency(signal.frequency)}`,
      })
    } catch (error) {
      console.error('Failed to save signal:', error)
      addNotification({
        type: 'error',
        message: 'Failed to save signal',
      })
    }
  }, [addSignal, addNotification])

  // Sorting
  const sortedPeaks = useMemo(() => {
    const sorted = [...detectedPeaks]
    sorted.sort((a, b) => {
      let aVal = a[sortConfig.key]
      let bVal = b[sortConfig.key]

      if (sortConfig.key === 'type') {
        aVal = a.knownBand?.name || 'zzz'
        bVal = b.knownBand?.name || 'zzz'
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })
    return sorted
  }, [detectedPeaks, sortConfig])

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }))
  }

  // Statistics
  const stats = useMemo(() => {
    if (detectedPeaks.length === 0) return null

    const known = detectedPeaks.filter(p => p.knownBand)
    const unknown = detectedPeaks.filter(p => !p.knownBand)
    const avgPower = detectedPeaks.reduce((sum, p) => sum + p.power, 0) / detectedPeaks.length
    const maxPower = Math.max(...detectedPeaks.map(p => p.power))

    const typeCount = {}
    detectedPeaks.forEach(p => {
      const type = p.type || 'unknown'
      typeCount[type] = (typeCount[type] || 0) + 1
    })

    return { known, unknown, avgPower, maxPower, typeCount }
  }, [detectedPeaks])

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SignalIcon color="primary" />
            <Typography variant="h6">Signal Analyzer</Typography>
            <Badge badgeContent={detectedPeaks.length} color="primary">
              <Chip size="small" label="Peaks" />
            </Badge>
          </Box>
          <Box>
            <Tooltip title="Detection Settings">
              <IconButton onClick={() => setShowSettings(!showSettings)}>
                <SettingsIcon color={showSettings ? 'primary' : 'inherit'} />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Detection Settings */}
        <Collapse in={showSettings}>
          <Box sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>Detection Settings</Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Power Threshold: {detectionSettings.threshold} dBm
                </Typography>
                <Slider
                  value={detectionSettings.threshold}
                  onChange={(e, v) => setDetectionSettings(s => ({ ...s, threshold: v }))}
                  min={-120}
                  max={-20}
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Min Prominence: {detectionSettings.minProminence} dB
                </Typography>
                <Slider
                  value={detectionSettings.minProminence}
                  onChange={(e, v) => setDetectionSettings(s => ({ ...s, minProminence: v }))}
                  min={3}
                  max={30}
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Min Distance: {detectionSettings.minDistance} bins
                </Typography>
                <Slider
                  value={detectionSettings.minDistance}
                  onChange={(e, v) => setDetectionSettings(s => ({ ...s, minDistance: v }))}
                  min={1}
                  max={20}
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Max Peaks: {detectionSettings.maxPeaks}
                </Typography>
                <Slider
                  value={detectionSettings.maxPeaks}
                  onChange={(e, v) => setDetectionSettings(s => ({ ...s, maxPeaks: v }))}
                  min={5}
                  max={50}
                  size="small"
                />
              </Grid>
            </Grid>
          </Box>
        </Collapse>

        {/* Statistics */}
        {stats && (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Detected</Typography>
                  <Typography variant="h6">{detectedPeaks.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Identified</Typography>
                  <Typography variant="h6">{stats.known.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Max Power</Typography>
                  <Typography variant="h6">{stats.maxPower.toFixed(1)} dBm</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, px: 2 }}>
                  <Typography variant="caption" color="text.secondary">Unknown</Typography>
                  <Typography variant="h6" color="warning.main">{stats.unknown.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* No data warning */}
        {!spectrumData && (
          <Alert severity="info">
            <AlertTitle>No Spectrum Data</AlertTitle>
            Start a spectrum scan to detect signals in real-time.
          </Alert>
        )}

        {/* Peaks Table */}
        {sortedPeaks.length > 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell width={60}>#</TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortConfig.key === 'frequency'}
                      direction={sortConfig.key === 'frequency' ? sortConfig.direction : 'asc'}
                      onClick={() => handleSort('frequency')}
                    >
                      Frequency
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortConfig.key === 'power'}
                      direction={sortConfig.key === 'power' ? sortConfig.direction : 'asc'}
                      onClick={() => handleSort('power')}
                    >
                      Power
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortConfig.key === 'snr'}
                      direction={sortConfig.key === 'snr' ? sortConfig.direction : 'asc'}
                      onClick={() => handleSort('snr')}
                    >
                      SNR
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={sortConfig.key === 'type'}
                      direction={sortConfig.key === 'type' ? sortConfig.direction : 'asc'}
                      onClick={() => handleSort('type')}
                    >
                      Identification
                    </TableSortLabel>
                  </TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedPeaks.map((peak, index) => (
                  <PeakSignalRow
                    key={`${peak.frequency}-${index}`}
                    peak={peak}
                    index={index}
                    onTag={handleTag}
                    onBookmark={handleBookmark}
                    bookmarked={bookmarkedFreqs.has(peak.frequency)}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {spectrumData && sortedPeaks.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">
              No signals detected above threshold. Try adjusting detection settings.
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Type Legend */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>Signal Type Legend</Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {Object.entries(typeColors).map(([type, color]) => (
            <Chip
              key={type}
              size="small"
              label={type.charAt(0).toUpperCase() + type.slice(1)}
              sx={{ bgcolor: color, color: 'white' }}
            />
          ))}
        </Box>
      </Paper>

      {/* Signal Tag Dialog */}
      <SignalTagDialog
        open={tagDialogOpen}
        onClose={() => setTagDialogOpen(false)}
        signal={selectedSignal}
        onSave={handleSaveSignal}
      />
    </Box>
  )
}

export default SignalAnalyzer
