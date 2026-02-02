import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tab,
  Divider,
} from '@mui/material'
import {
  Add as AddIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  LocationOn as LocationIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { useStore } from '../store/useStore'
import { api } from '../services/api'
import { useSurveyWebSocket } from '../hooks/useWebSocket'

// Common frequency bands
const frequencyBands = [
  { name: 'FM Broadcast', start: 88e6, stop: 108e6 },
  { name: 'VHF Low (TV)', start: 54e6, stop: 88e6 },
  { name: 'VHF High (TV)', start: 174e6, stop: 216e6 },
  { name: 'UHF (TV)', start: 470e6, stop: 806e6 },
  { name: 'ISM 433 MHz', start: 433e6, stop: 435e6 },
  { name: 'ISM 915 MHz', start: 902e6, stop: 928e6 },
  { name: 'Cellular 700 MHz', start: 698e6, stop: 806e6 },
  { name: 'Cellular 850 MHz', start: 824e6, stop: 894e6 },
  { name: 'WiFi 2.4 GHz', start: 2.4e9, stop: 2.5e9 },
  { name: 'Custom', start: 0, stop: 0 },
]

function SurveyManager() {
  const {
    surveys,
    setSurveys,
    addSurvey,
    updateSurvey,
    removeSurvey,
    activeSurvey,
    setActiveSurvey,
    surveyProgress,
    devices,
    loading,
    setLoading,
  } = useStore()

  const [tabValue, setTabValue] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [selectedSurveyDetail, setSelectedSurveyDetail] = useState(null)
  const [error, setError] = useState(null)
  const [activeStep, setActiveStep] = useState(0)

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    survey_type: 'fixed',
    device_id: '',
    start_frequency: 88e6,
    stop_frequency: 108e6,
    step_size: 100000,
    bandwidth: 200000,
    integration_time: 0.1,
    locations: [],
    location: {
      latitude: '',
      longitude: '',
      name: '',
    },
    gps_mode: 'manual',
  })

  // WebSocket for active survey progress
  const { isConnected: wsConnected } = useSurveyWebSocket(
    activeSurvey?.id,
    { autoConnect: !!activeSurvey }
  )

  // Load surveys on mount
  useEffect(() => {
    async function loadSurveys() {
      try {
        setLoading('surveys', true)
        const response = await api.getSurveys()
        setSurveys(response.surveys || [])

        // Check for active surveys
        const active = await api.getActiveSurveys()
        if (active.length > 0) {
          setActiveSurvey(active[0])
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading('surveys', false)
      }
    }
    loadSurveys()
  }, [setSurveys, setActiveSurvey, setLoading])

  // Poll for progress when survey is active
  useEffect(() => {
    if (!activeSurvey) return

    const interval = setInterval(async () => {
      try {
        const progress = await api.getSurveyProgress(activeSurvey.id)
        if (progress.status === 'completed' || progress.status === 'failed') {
          setActiveSurvey(null)
          // Refresh surveys list
          const response = await api.getSurveys()
          setSurveys(response.surveys || [])
        }
      } catch (err) {
        console.error('Failed to get progress:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [activeSurvey, setActiveSurvey, setSurveys])

  const handleCreateSurvey = async () => {
    try {
      setError(null)
      const surveyData = {
        name: formData.name,
        description: formData.description,
        survey_type: formData.survey_type,
        device_id: formData.device_id || null,
        start_frequency: formData.start_frequency,
        stop_frequency: formData.stop_frequency,
        step_size: formData.step_size,
        bandwidth: formData.bandwidth,
        integration_time: formData.integration_time,
      }

      if (formData.survey_type === 'multi_location' && formData.locations.length > 0) {
        surveyData.locations = formData.locations
      }

      const created = await api.createSurvey(surveyData)
      addSurvey(created)
      setDialogOpen(false)
      resetForm()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleStartSurvey = async (survey) => {
    try {
      setError(null)
      const startParams = {
        device_id: survey.device_id || devices[0]?.id,
        gps_mode: formData.gps_mode,
      }

      if (formData.location.latitude && formData.location.longitude) {
        startParams.location = {
          latitude: parseFloat(formData.location.latitude),
          longitude: parseFloat(formData.location.longitude),
          name: formData.location.name || 'Survey Location',
        }
      }

      const updated = await api.startSurvey(survey.id, startParams)
      updateSurvey(survey.id, updated)
      setActiveSurvey(updated)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleStopSurvey = async (survey) => {
    try {
      const updated = await api.stopSurvey(survey.id)
      updateSurvey(survey.id, updated)
      setActiveSurvey(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteSurvey = async (id) => {
    if (!window.confirm('Delete this survey and all its data?')) return

    try {
      await api.deleteSurvey(id)
      removeSurvey(id)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleViewDetails = async (survey) => {
    try {
      const details = await api.getSurvey(survey.id)
      setSelectedSurveyDetail(details)
      setDetailDialogOpen(true)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleBandSelect = (band) => {
    if (band.name !== 'Custom') {
      setFormData(f => ({
        ...f,
        start_frequency: band.start,
        stop_frequency: band.stop,
      }))
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      survey_type: 'fixed',
      device_id: '',
      start_frequency: 88e6,
      stop_frequency: 108e6,
      step_size: 100000,
      bandwidth: 200000,
      integration_time: 0.1,
      locations: [],
      location: { latitude: '', longitude: '', name: '' },
      gps_mode: 'manual',
    })
    setActiveStep(0)
  }

  const getStatusChip = (status) => {
    const colors = {
      planned: 'default',
      running: 'primary',
      paused: 'warning',
      completed: 'success',
      failed: 'error',
    }
    return <Chip size="small" label={status} color={colors[status] || 'default'} />
  }

  const steps = ['Basic Info', 'Frequency Range', 'Location']

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Header */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Survey Management</Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  startIcon={<RefreshIcon />}
                  onClick={async () => {
                    const response = await api.getSurveys()
                    setSurveys(response.surveys || [])
                  }}
                >
                  Refresh
                </Button>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => setDialogOpen(true)}
                >
                  New Survey
                </Button>
              </Box>
            </Box>
            {loading.surveys && <LinearProgress sx={{ mt: 2 }} />}
            {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>{error}</Alert>}
          </Paper>
        </Grid>

        {/* Active Survey Progress */}
        {activeSurvey && surveyProgress && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2, borderLeft: 4, borderColor: 'primary.main' }}>
              <Typography variant="subtitle1" gutterBottom>
                Active Survey: {activeSurvey.name}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ flexGrow: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={surveyProgress.progress || 0}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
                <Typography variant="body2">
                  {(surveyProgress.progress || 0).toFixed(1)}%
                </Typography>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<StopIcon />}
                  onClick={() => handleStopSurvey(activeSurvey)}
                >
                  Stop
                </Button>
              </Box>
              <Typography variant="caption" color="text.secondary">
                Measurements: {surveyProgress.measurements_collected || 0}
                {surveyProgress.current_frequency && ` | Current: ${(surveyProgress.current_frequency / 1e6).toFixed(2)} MHz`}
              </Typography>
            </Paper>
          </Grid>
        )}

        {/* Tabs */}
        <Grid item xs={12}>
          <Paper>
            <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
              <Tab label="All Surveys" />
              <Tab label="Running" />
              <Tab label="Completed" />
            </Tabs>
          </Paper>
        </Grid>

        {/* Survey List */}
        <Grid item xs={12}>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Frequency Range</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Progress</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {surveys
                  .filter(s => {
                    if (tabValue === 1) return s.status === 'running'
                    if (tabValue === 2) return s.status === 'completed'
                    return true
                  })
                  .map((survey) => (
                    <TableRow key={survey.id}>
                      <TableCell>
                        <Typography variant="body2">{survey.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {survey.description}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={survey.survey_type} variant="outlined" />
                      </TableCell>
                      <TableCell>{survey.frequency_range_mhz}</TableCell>
                      <TableCell>{getStatusChip(survey.status)}</TableCell>
                      <TableCell>
                        <Box sx={{ width: 100 }}>
                          <LinearProgress
                            variant="determinate"
                            value={survey.progress || 0}
                          />
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleViewDetails(survey)}
                        >
                          <ViewIcon />
                        </IconButton>
                        {survey.status === 'planned' && (
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleStartSurvey(survey)}
                            disabled={!!activeSurvey}
                          >
                            <StartIcon />
                          </IconButton>
                        )}
                        {survey.status === 'running' && (
                          <IconButton
                            size="small"
                            color="warning"
                            onClick={() => handleStopSurvey(survey)}
                          >
                            <StopIcon />
                          </IconButton>
                        )}
                        {survey.status !== 'running' && (
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteSurvey(survey.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                {surveys.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary" sx={{ py: 4 }}>
                        No surveys yet. Create one to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>

      {/* Create Survey Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Survey</DialogTitle>
        <DialogContent>
          <Stepper activeStep={activeStep} sx={{ py: 3 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {activeStep === 0 && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <TextField
                  label="Survey Name"
                  fullWidth
                  required
                  value={formData.name}
                  onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Description"
                  fullWidth
                  multiline
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData(f => ({ ...f, description: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Survey Type</InputLabel>
                  <Select
                    value={formData.survey_type}
                    label="Survey Type"
                    onChange={(e) => setFormData(f => ({ ...f, survey_type: e.target.value }))}
                  >
                    <MenuItem value="fixed">Fixed Location</MenuItem>
                    <MenuItem value="multi_location">Multi-Location</MenuItem>
                    <MenuItem value="mobile">Mobile (GPS Tracking)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Device</InputLabel>
                  <Select
                    value={formData.device_id}
                    label="Device"
                    onChange={(e) => setFormData(f => ({ ...f, device_id: e.target.value }))}
                  >
                    {devices.map(d => (
                      <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          )}

          {activeStep === 1 && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>Quick Select Band</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {frequencyBands.map(band => (
                    <Chip
                      key={band.name}
                      label={band.name}
                      onClick={() => handleBandSelect(band)}
                      variant={
                        formData.start_frequency === band.start &&
                        formData.stop_frequency === band.stop
                          ? 'filled' : 'outlined'
                      }
                      color="primary"
                    />
                  ))}
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Start Frequency (MHz)"
                  type="number"
                  fullWidth
                  value={formData.start_frequency / 1e6}
                  onChange={(e) => setFormData(f => ({ ...f, start_frequency: parseFloat(e.target.value) * 1e6 }))}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Stop Frequency (MHz)"
                  type="number"
                  fullWidth
                  value={formData.stop_frequency / 1e6}
                  onChange={(e) => setFormData(f => ({ ...f, stop_frequency: parseFloat(e.target.value) * 1e6 }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Step Size (kHz)"
                  type="number"
                  fullWidth
                  value={formData.step_size / 1e3}
                  onChange={(e) => setFormData(f => ({ ...f, step_size: parseFloat(e.target.value) * 1e3 }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Bandwidth (kHz)"
                  type="number"
                  fullWidth
                  value={formData.bandwidth / 1e3}
                  onChange={(e) => setFormData(f => ({ ...f, bandwidth: parseFloat(e.target.value) * 1e3 }))}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Integration Time (s)"
                  type="number"
                  fullWidth
                  value={formData.integration_time}
                  onChange={(e) => setFormData(f => ({ ...f, integration_time: parseFloat(e.target.value) }))}
                  inputProps={{ step: 0.1, min: 0.01, max: 10 }}
                />
              </Grid>
            </Grid>
          )}

          {activeStep === 2 && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>GPS Mode</InputLabel>
                  <Select
                    value={formData.gps_mode}
                    label="GPS Mode"
                    onChange={(e) => setFormData(f => ({ ...f, gps_mode: e.target.value }))}
                  >
                    <MenuItem value="manual">Manual Entry</MenuItem>
                    <MenuItem value="gpsd">GPS Daemon (GPSD)</MenuItem>
                    <MenuItem value="mock">Mock GPS (Testing)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {formData.gps_mode === 'manual' && (
                <>
                  <Grid item xs={12}>
                    <Divider>
                      <Chip icon={<LocationIcon />} label="Starting Location" />
                    </Divider>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Latitude"
                      type="number"
                      fullWidth
                      value={formData.location.latitude}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        location: { ...f.location, latitude: e.target.value }
                      }))}
                      inputProps={{ step: 0.000001, min: -90, max: 90 }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Longitude"
                      type="number"
                      fullWidth
                      value={formData.location.longitude}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        location: { ...f.location, longitude: e.target.value }
                      }))}
                      inputProps={{ step: 0.000001, min: -180, max: 180 }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Location Name"
                      fullWidth
                      value={formData.location.name}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        location: { ...f.location, name: e.target.value }
                      }))}
                    />
                  </Grid>
                </>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          {activeStep > 0 && (
            <Button onClick={() => setActiveStep(s => s - 1)}>Back</Button>
          )}
          {activeStep < steps.length - 1 ? (
            <Button
              variant="contained"
              onClick={() => setActiveStep(s => s + 1)}
              disabled={activeStep === 0 && !formData.name}
            >
              Next
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={handleCreateSurvey}
              disabled={!formData.name}
            >
              Create Survey
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Survey Details Dialog */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Survey Details</DialogTitle>
        <DialogContent>
          {selectedSurveyDetail && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Name</Typography>
                <Typography>{selectedSurveyDetail.name}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Status</Typography>
                <Typography>{getStatusChip(selectedSurveyDetail.status)}</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">Description</Typography>
                <Typography>{selectedSurveyDetail.description || 'N/A'}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Frequency Range</Typography>
                <Typography>{selectedSurveyDetail.frequency_range_mhz}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Type</Typography>
                <Typography>{selectedSurveyDetail.survey_type}</Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Measurements</Typography>
                <Typography variant="h6">{selectedSurveyDetail.measurement_count || 0}</Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Locations</Typography>
                <Typography variant="h6">{selectedSurveyDetail.locations?.length || 0}</Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Signals Found</Typography>
                <Typography variant="h6">{selectedSurveyDetail.signal_count || 0}</Typography>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default SurveyManager
