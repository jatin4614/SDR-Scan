import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Slider,
  IconButton,
  Button,
  ButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Tooltip,
  Chip,
  LinearProgress,
  Card,
  CardContent,
} from '@mui/material'
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  SkipPrevious as PrevIcon,
  SkipNext as NextIcon,
  FastRewind as RewindIcon,
  FastForward as ForwardIcon,
  Replay as ReplayIcon,
  Timeline as TimelineIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material'
import { api } from '../services/api'
import { useStore } from '../store/useStore'

function MeasurementHistory({
  surveyId,
  onMeasurementSelect,
  onPlaybackData,
}) {
  const { surveys } = useStore()

  const [measurements, setMeasurements] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedSurvey, setSelectedSurvey] = useState(surveyId || '')

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)

  // Time range filter
  const [timeRange, setTimeRange] = useState({ start: null, end: null })

  // Group measurements by time for playback
  const groupedMeasurements = useMemo(() => {
    if (!measurements.length) return []

    // Group by timestamp (rounded to seconds)
    const groups = new Map()
    measurements.forEach(m => {
      const timestamp = new Date(m.timestamp).toISOString().slice(0, 19)
      if (!groups.has(timestamp)) {
        groups.set(timestamp, [])
      }
      groups.get(timestamp).push(m)
    })

    return Array.from(groups.entries())
      .map(([timestamp, data]) => ({ timestamp, data }))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  }, [measurements])

  // Load measurements
  useEffect(() => {
    if (!selectedSurvey) {
      setMeasurements([])
      return
    }

    async function loadMeasurements() {
      setLoading(true)
      try {
        const params = {
          survey_id: selectedSurvey,
          limit: 10000,
        }
        if (timeRange.start) params.start_time = timeRange.start
        if (timeRange.end) params.end_time = timeRange.end

        const response = await api.getMeasurements(params)
        setMeasurements(response.measurements || [])
        setCurrentIndex(0)
      } catch (error) {
        console.error('Failed to load measurements:', error)
      } finally {
        setLoading(false)
      }
    }

    loadMeasurements()
  }, [selectedSurvey, timeRange])

  // Playback timer
  useEffect(() => {
    if (!isPlaying || groupedMeasurements.length === 0) return

    const interval = setInterval(() => {
      setCurrentIndex(prev => {
        const next = prev + 1
        if (next >= groupedMeasurements.length) {
          setIsPlaying(false)
          return prev
        }
        return next
      })
    }, 1000 / playbackSpeed)

    return () => clearInterval(interval)
  }, [isPlaying, playbackSpeed, groupedMeasurements.length])

  // Notify parent of current playback data
  useEffect(() => {
    if (groupedMeasurements.length > 0 && currentIndex < groupedMeasurements.length) {
      const current = groupedMeasurements[currentIndex]
      onPlaybackData?.(current.data)
      onMeasurementSelect?.(current)
    }
  }, [currentIndex, groupedMeasurements, onPlaybackData, onMeasurementSelect])

  const handlePlay = () => setIsPlaying(true)
  const handlePause = () => setIsPlaying(false)
  const handleRestart = () => {
    setCurrentIndex(0)
    setIsPlaying(true)
  }

  const handlePrev = () => {
    setCurrentIndex(prev => Math.max(0, prev - 1))
  }

  const handleNext = () => {
    setCurrentIndex(prev => Math.min(groupedMeasurements.length - 1, prev + 1))
  }

  const handleSkipBackward = () => {
    setCurrentIndex(prev => Math.max(0, prev - 10))
  }

  const handleSkipForward = () => {
    setCurrentIndex(prev => Math.min(groupedMeasurements.length - 1, prev + 10))
  }

  const handleSliderChange = (_, value) => {
    setCurrentIndex(value)
  }

  const currentGroup = groupedMeasurements[currentIndex]
  const progress = groupedMeasurements.length > 0
    ? ((currentIndex + 1) / groupedMeasurements.length) * 100
    : 0

  // Statistics
  const stats = useMemo(() => {
    if (!measurements.length) return null

    const powers = measurements.map(m => m.power_dbm)
    const frequencies = measurements.map(m => m.frequency)

    return {
      count: measurements.length,
      timeSpan: groupedMeasurements.length,
      minPower: Math.min(...powers).toFixed(1),
      maxPower: Math.max(...powers).toFixed(1),
      avgPower: (powers.reduce((a, b) => a + b, 0) / powers.length).toFixed(1),
      freqRange: `${(Math.min(...frequencies) / 1e6).toFixed(2)} - ${(Math.max(...frequencies) / 1e6).toFixed(2)} MHz`,
    }
  }, [measurements, groupedMeasurements])

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <TimelineIcon color="primary" />
        <Typography variant="subtitle1">Measurement History</Typography>
        {loading && <LinearProgress sx={{ flexGrow: 1, ml: 2 }} />}
      </Box>

      <Grid container spacing={2}>
        {/* Survey Selection */}
        <Grid item xs={12} sm={6}>
          <FormControl size="small" fullWidth>
            <InputLabel>Survey</InputLabel>
            <Select
              value={selectedSurvey}
              label="Survey"
              onChange={(e) => setSelectedSurvey(e.target.value)}
            >
              <MenuItem value="">Select a survey...</MenuItem>
              {surveys
                .filter(s => s.status === 'completed' || s.measurement_count > 0)
                .map(survey => (
                  <MenuItem key={survey.id} value={survey.id}>
                    {survey.name}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
        </Grid>

        {/* Playback Speed */}
        <Grid item xs={12} sm={6}>
          <FormControl size="small" fullWidth>
            <InputLabel>Playback Speed</InputLabel>
            <Select
              value={playbackSpeed}
              label="Playback Speed"
              onChange={(e) => setPlaybackSpeed(e.target.value)}
            >
              <MenuItem value={0.25}>0.25x (Slow)</MenuItem>
              <MenuItem value={0.5}>0.5x</MenuItem>
              <MenuItem value={1}>1x (Normal)</MenuItem>
              <MenuItem value={2}>2x</MenuItem>
              <MenuItem value={4}>4x (Fast)</MenuItem>
              <MenuItem value={10}>10x (Very Fast)</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        {/* Statistics Cards */}
        {stats && (
          <>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Measurements
                  </Typography>
                  <Typography variant="h6">{stats.count.toLocaleString()}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Time Points
                  </Typography>
                  <Typography variant="h6">{stats.timeSpan}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Power Range
                  </Typography>
                  <Typography variant="body2">
                    {stats.minPower} to {stats.maxPower} dBm
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                  <Typography variant="caption" color="text.secondary">
                    Freq Range
                  </Typography>
                  <Typography variant="body2" noWrap>
                    {stats.freqRange}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {/* Timeline Slider */}
        <Grid item xs={12}>
          <Box sx={{ px: 1 }}>
            <Slider
              value={currentIndex}
              onChange={handleSliderChange}
              min={0}
              max={Math.max(0, groupedMeasurements.length - 1)}
              disabled={groupedMeasurements.length === 0}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => {
                const group = groupedMeasurements[value]
                return group ? new Date(group.timestamp).toLocaleTimeString() : ''
              }}
            />
          </Box>
        </Grid>

        {/* Playback Controls */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1 }}>
            <Tooltip title="Restart">
              <IconButton onClick={handleRestart} disabled={groupedMeasurements.length === 0}>
                <ReplayIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Skip Back 10">
              <IconButton onClick={handleSkipBackward} disabled={currentIndex === 0}>
                <RewindIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Previous">
              <IconButton onClick={handlePrev} disabled={currentIndex === 0}>
                <PrevIcon />
              </IconButton>
            </Tooltip>

            {isPlaying ? (
              <Tooltip title="Pause">
                <IconButton onClick={handlePause} color="primary" size="large">
                  <PauseIcon fontSize="large" />
                </IconButton>
              </Tooltip>
            ) : (
              <Tooltip title="Play">
                <IconButton
                  onClick={handlePlay}
                  color="primary"
                  size="large"
                  disabled={groupedMeasurements.length === 0}
                >
                  <PlayIcon fontSize="large" />
                </IconButton>
              </Tooltip>
            )}

            <Tooltip title="Next">
              <IconButton
                onClick={handleNext}
                disabled={currentIndex >= groupedMeasurements.length - 1}
              >
                <NextIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Skip Forward 10">
              <IconButton
                onClick={handleSkipForward}
                disabled={currentIndex >= groupedMeasurements.length - 1}
              >
                <ForwardIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Grid>

        {/* Current Position Info */}
        <Grid item xs={12}>
          <Box sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            bgcolor: 'background.default',
            p: 1,
            borderRadius: 1,
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CalendarIcon fontSize="small" color="action" />
              <Typography variant="body2">
                {currentGroup
                  ? new Date(currentGroup.timestamp).toLocaleString()
                  : 'No data'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                size="small"
                label={`${currentIndex + 1} / ${groupedMeasurements.length}`}
              />
              <Chip
                size="small"
                label={`${currentGroup?.data?.length || 0} points`}
                color="primary"
                variant="outlined"
              />
            </Box>

            <Typography variant="body2" color="text.secondary">
              {progress.toFixed(0)}%
            </Typography>
          </Box>
        </Grid>

        {/* Empty State */}
        {!selectedSurvey && (
          <Grid item xs={12}>
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <TimelineIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography color="text.secondary">
                Select a survey to browse measurement history
              </Typography>
            </Box>
          </Grid>
        )}

        {selectedSurvey && !loading && measurements.length === 0 && (
          <Grid item xs={12}>
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                No measurements found for this survey
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  )
}

export default MeasurementHistory
