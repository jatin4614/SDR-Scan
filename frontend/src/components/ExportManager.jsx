import { useState, useEffect, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  Divider,
  Alert,
  AlertTitle,
  LinearProgress,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Collapse,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material'
import {
  FileDownload as DownloadIcon,
  Description as CSVIcon,
  Map as GeoPackageIcon,
  Refresh as RefreshIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  PlayArrow as ProcessingIcon,
  Settings as SettingsIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  FolderOpen as FolderIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useStore } from '../store/useStore'
import { api } from '../services/api'

// Frequency band presets for filtering
const frequencyBands = [
  { name: 'All Frequencies', start: 0, end: 10e9 },
  { name: 'HF (3-30 MHz)', start: 3e6, end: 30e6 },
  { name: 'VHF (30-300 MHz)', start: 30e6, end: 300e6 },
  { name: 'UHF (300-3000 MHz)', start: 300e6, end: 3000e6 },
  { name: 'FM Broadcast (88-108 MHz)', start: 88e6, end: 108e6 },
  { name: 'VHF TV (54-216 MHz)', start: 54e6, end: 216e6 },
  { name: 'Cellular (698-960 MHz)', start: 698e6, end: 960e6 },
  { name: 'ISM 915 MHz', start: 902e6, end: 928e6 },
  { name: 'WiFi 2.4 GHz', start: 2.4e9, end: 2.5e9 },
]

/**
 * Format frequency for display
 */
function formatFrequency(hz) {
  if (hz >= 1e9) return `${(hz / 1e9).toFixed(2)} GHz`
  if (hz >= 1e6) return `${(hz / 1e6).toFixed(2)} MHz`
  if (hz >= 1e3) return `${(hz / 1e3).toFixed(2)} kHz`
  return `${hz} Hz`
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`
  return `${bytes} B`
}

/**
 * Get status icon and color
 */
function getStatusDisplay(status) {
  switch (status) {
    case 'completed':
      return { icon: <CompleteIcon />, color: 'success', label: 'Completed' }
    case 'failed':
      return { icon: <ErrorIcon />, color: 'error', label: 'Failed' }
    case 'processing':
    case 'running':
      return { icon: <ProcessingIcon />, color: 'info', label: 'Processing' }
    case 'pending':
    default:
      return { icon: <PendingIcon />, color: 'warning', label: 'Pending' }
  }
}

/**
 * Export Options Dialog
 */
function ExportOptionsDialog({
  open,
  onClose,
  survey,
  onExport,
}) {
  const [format, setFormat] = useState('geopackage')
  const [frequencyBand, setFrequencyBand] = useState('All Frequencies')
  const [customFreqStart, setCustomFreqStart] = useState('')
  const [customFreqEnd, setCustomFreqEnd] = useState('')
  const [includeNoise, setIncludeNoise] = useState(true)
  const [includeSNR, setIncludeSNR] = useState(true)
  const [separateLayers, setSeparateLayers] = useState(true)
  const [generateHeatmap, setGenerateHeatmap] = useState(true)
  const [heatmapCellSize, setHeatmapCellSize] = useState(100)
  const [loading, setLoading] = useState(false)

  // Reset form when survey changes
  useEffect(() => {
    if (survey) {
      setFormat('geopackage')
      setFrequencyBand('All Frequencies')
      setCustomFreqStart('')
      setCustomFreqEnd('')
    }
  }, [survey])

  const handleFrequencyBandChange = (e) => {
    const bandName = e.target.value
    setFrequencyBand(bandName)
    if (bandName !== 'All Frequencies' && bandName !== 'Custom') {
      const band = frequencyBands.find(b => b.name === bandName)
      if (band) {
        setCustomFreqStart((band.start / 1e6).toString())
        setCustomFreqEnd((band.end / 1e6).toString())
      }
    } else if (bandName === 'All Frequencies') {
      setCustomFreqStart('')
      setCustomFreqEnd('')
    }
  }

  const handleExport = async () => {
    setLoading(true)
    try {
      const params = {
        survey_id: survey.id,
      }

      // Add frequency filters if specified
      if (customFreqStart) {
        params.start_freq = parseFloat(customFreqStart) * 1e6
      }
      if (customFreqEnd) {
        params.end_freq = parseFloat(customFreqEnd) * 1e6
      }

      if (format === 'geopackage') {
        params.include_noise_floor = includeNoise
        params.include_snr = includeSNR
        params.separate_layers = separateLayers
        params.interpolate = generateHeatmap
        if (generateHeatmap) {
          params.cell_size = heatmapCellSize
        }
      }

      await onExport(format, params)
      onClose()
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!survey) return null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Export Survey: {survey?.name}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          {/* Export Format */}
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Export Format</InputLabel>
            <Select
              value={format}
              label="Export Format"
              onChange={(e) => setFormat(e.target.value)}
            >
              <MenuItem value="geopackage">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <GeoPackageIcon color="primary" />
                  <Box>
                    <Typography>GeoPackage (.gpkg)</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Native QGIS format with spatial layers
                    </Typography>
                  </Box>
                </Box>
              </MenuItem>
              <MenuItem value="csv">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CSVIcon color="secondary" />
                  <Box>
                    <Typography>CSV (.csv)</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Delimited text for general use
                    </Typography>
                  </Box>
                </Box>
              </MenuItem>
            </Select>
          </FormControl>

          <Divider sx={{ my: 2 }} />

          {/* Frequency Filtering */}
          <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterIcon fontSize="small" />
            Frequency Filter
          </Typography>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Frequency Band</InputLabel>
            <Select
              value={frequencyBand}
              label="Frequency Band"
              onChange={handleFrequencyBandChange}
            >
              {frequencyBands.map(band => (
                <MenuItem key={band.name} value={band.name}>
                  {band.name}
                </MenuItem>
              ))}
              <MenuItem value="Custom">Custom Range</MenuItem>
            </Select>
          </FormControl>

          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}>
              <TextField
                label="Start Freq (MHz)"
                type="number"
                fullWidth
                value={customFreqStart}
                onChange={(e) => {
                  setCustomFreqStart(e.target.value)
                  if (e.target.value) setFrequencyBand('Custom')
                }}
                size="small"
                inputProps={{ min: 0 }}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                label="End Freq (MHz)"
                type="number"
                fullWidth
                value={customFreqEnd}
                onChange={(e) => {
                  setCustomFreqEnd(e.target.value)
                  if (e.target.value) setFrequencyBand('Custom')
                }}
                size="small"
                inputProps={{ min: 0 }}
              />
            </Grid>
          </Grid>

          {/* GeoPackage-specific options */}
          {format === 'geopackage' && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsIcon fontSize="small" />
                GeoPackage Options
              </Typography>

              <FormGroup>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={includeNoise}
                      onChange={(e) => setIncludeNoise(e.target.checked)}
                    />
                  }
                  label="Include noise floor measurements"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={includeSNR}
                      onChange={(e) => setIncludeSNR(e.target.checked)}
                    />
                  }
                  label="Include SNR calculations"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={separateLayers}
                      onChange={(e) => setSeparateLayers(e.target.checked)}
                    />
                  }
                  label="Create separate layers by frequency band"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={generateHeatmap}
                      onChange={(e) => setGenerateHeatmap(e.target.checked)}
                    />
                  }
                  label="Generate interpolated heatmap layer"
                />
              </FormGroup>

              {generateHeatmap && (
                <TextField
                  label="Heatmap Cell Size (meters)"
                  type="number"
                  fullWidth
                  value={heatmapCellSize}
                  onChange={(e) => setHeatmapCellSize(parseInt(e.target.value) || 100)}
                  size="small"
                  sx={{ mt: 2 }}
                  inputProps={{ min: 10, max: 1000 }}
                  helperText="Smaller values = higher resolution, larger file size"
                />
              )}
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleExport}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <DownloadIcon />}
        >
          {loading ? 'Exporting...' : 'Start Export'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

/**
 * Export Job Item
 */
function ExportJobItem({ job, onDownload, onRefresh }) {
  const statusDisplay = getStatusDisplay(job.status)

  return (
    <ListItem
      sx={{
        bgcolor: 'background.paper',
        borderRadius: 1,
        mb: 1,
        border: 1,
        borderColor: 'divider',
      }}
    >
      <ListItemIcon>
        {job.export_type === 'geopackage' ? (
          <GeoPackageIcon color="primary" />
        ) : (
          <CSVIcon color="secondary" />
        )}
      </ListItemIcon>
      <ListItemText
        primary={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2">
              {job.export_type === 'geopackage' ? 'GeoPackage' : 'CSV'} Export - Survey #{job.survey_id}
            </Typography>
            <Chip
              size="small"
              icon={statusDisplay.icon}
              label={statusDisplay.label}
              color={statusDisplay.color}
            />
          </Box>
        }
        secondary={
          <Box sx={{ mt: 0.5 }}>
            <Typography variant="caption" color="text.secondary" component="div">
              Created: {new Date(job.created_at).toLocaleString()}
            </Typography>
            {job.file_size && (
              <Typography variant="caption" color="text.secondary" component="div">
                Size: {formatFileSize(job.file_size)}
              </Typography>
            )}
            {(job.status === 'processing' || job.status === 'running') && (
              <LinearProgress sx={{ mt: 1 }} />
            )}
            {job.error_message && (
              <Typography variant="caption" color="error" component="div">
                Error: {job.error_message}
              </Typography>
            )}
          </Box>
        }
      />
      <ListItemSecondaryAction>
        {job.status === 'completed' && (
          <Tooltip title="Download">
            <IconButton
              edge="end"
              onClick={() => onDownload(job)}
              color="primary"
            >
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        )}
        {(job.status === 'processing' || job.status === 'running') && (
          <Tooltip title="Refresh Status">
            <IconButton
              edge="end"
              onClick={() => onRefresh(job.id)}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        )}
      </ListItemSecondaryAction>
    </ListItem>
  )
}

/**
 * Survey Export Card
 */
function SurveyExportCard({ survey, onExport }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" gutterBottom>
              {survey.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                size="small"
                label={survey.status}
                color={survey.status === 'completed' ? 'success' : 'default'}
              />
              <Chip
                size="small"
                label={survey.survey_type}
                variant="outlined"
              />
            </Box>
          </Box>
          <IconButton onClick={() => setExpanded(!expanded)} size="small">
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">Frequency Range</Typography>
                <Typography variant="body2">
                  {formatFrequency(survey.start_frequency)} - {formatFrequency(survey.stop_frequency)}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">Created</Typography>
                <Typography variant="body2">
                  {new Date(survey.created_at).toLocaleDateString()}
                </Typography>
              </Grid>
              {survey.description && (
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">Description</Typography>
                  <Typography variant="body2">{survey.description}</Typography>
                </Grid>
              )}
            </Grid>
          </Box>
        </Collapse>
      </CardContent>
      <CardActions sx={{ justifyContent: 'flex-end', px: 2, pb: 2 }}>
        <Button
          variant="outlined"
          size="small"
          startIcon={<CSVIcon />}
          onClick={() => onExport(survey, 'csv')}
        >
          CSV
        </Button>
        <Button
          variant="contained"
          size="small"
          startIcon={<GeoPackageIcon />}
          onClick={() => onExport(survey, 'geopackage')}
        >
          GeoPackage
        </Button>
      </CardActions>
    </Card>
  )
}

/**
 * Tab Panel Component
 */
function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  )
}

/**
 * ExportManager Component
 *
 * Main component for managing data exports to CSV and GeoPackage formats
 */
function ExportManager() {
  const { surveys, exportJobs, setExportJobs, addExportJob, addNotification, setLoading, loading } = useStore()
  const [selectedSurvey, setSelectedSurvey] = useState(null)
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState(0)

  // Load export jobs on mount and periodically
  useEffect(() => {
    loadExportJobs()
    const interval = setInterval(loadExportJobs, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const loadExportJobs = async () => {
    try {
      const response = await api.getExportJobs()
      setExportJobs(response.jobs || [])
    } catch (error) {
      console.error('Failed to load export jobs:', error)
    }
  }

  const handleExportClick = (survey, format) => {
    setSelectedSurvey({ ...survey, initialFormat: format })
    setExportDialogOpen(true)
  }

  const handleExport = async (format, params) => {
    try {
      let response
      if (format === 'geopackage') {
        response = await api.exportGeoPackage(params)
      } else {
        response = await api.exportCSV(params)
      }

      if (response.job || response) {
        addExportJob(response.job || response)
      }
      addNotification({
        type: 'success',
        message: `Export started: ${format.toUpperCase()} for survey ${params.survey_id}`,
      })

      // Switch to history tab to show the new job
      setActiveTab(1)
    } catch (error) {
      addNotification({
        type: 'error',
        message: `Export failed: ${error.message}`,
      })
      throw error
    }
  }

  const handleDownload = async (job) => {
    try {
      const blob = await api.downloadExport(job.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = job.file_path?.split('/').pop() || `export_${job.id}.${job.export_type === 'geopackage' ? 'gpkg' : 'csv'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      addNotification({
        type: 'success',
        message: 'Download started',
      })
    } catch (error) {
      addNotification({
        type: 'error',
        message: `Download failed: ${error.message}`,
      })
    }
  }

  const handleRefreshJob = async (jobId) => {
    setRefreshing(true)
    try {
      await loadExportJobs()
    } finally {
      setRefreshing(false)
    }
  }

  // Filter surveys that can be exported
  const exportableSurveys = surveys.filter(s =>
    s.status === 'completed' || s.status === 'stopped' || s.status === 'running'
  )

  // Group export jobs by status
  const activeJobs = exportJobs.filter(j => j.status === 'processing' || j.status === 'pending' || j.status === 'running')
  const completedJobs = exportJobs.filter(j => j.status === 'completed')
  const failedJobs = exportJobs.filter(j => j.status === 'failed')

  return (
    <Box>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h5" gutterBottom>
              Data Export
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Export survey data to CSV or GeoPackage for analysis in QGIS
            </Typography>
          </Box>
          <Tooltip title="Refresh export jobs">
            <IconButton onClick={loadExportJobs} disabled={refreshing}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Active Export Jobs Alert */}
        {activeJobs.length > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <AlertTitle>Active Exports ({activeJobs.length})</AlertTitle>
            {activeJobs.map(job => (
              <Box key={job.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2">
                  {job.export_type.toUpperCase()} - Survey #{job.survey_id}
                </Typography>
                <CircularProgress size={16} />
              </Box>
            ))}
          </Alert>
        )}

        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={`Surveys (${exportableSurveys.length})`} />
          <Tab label={`Export History (${exportJobs.length})`} />
          <Tab label="Help" icon={<InfoIcon />} iconPosition="end" />
        </Tabs>

        {/* Surveys Tab */}
        <TabPanel value={activeTab} index={0}>
          {exportableSurveys.length === 0 ? (
            <Alert severity="info">
              No surveys available for export. Complete a survey first to export data.
            </Alert>
          ) : (
            <Box>
              {exportableSurveys.map(survey => (
                <SurveyExportCard
                  key={survey.id}
                  survey={survey}
                  onExport={handleExportClick}
                />
              ))}
            </Box>
          )}
        </TabPanel>

        {/* History Tab */}
        <TabPanel value={activeTab} index={1}>
          {/* Completed Exports */}
          {completedJobs.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'success.main', display: 'flex', alignItems: 'center', gap: 1 }}>
                <CompleteIcon fontSize="small" />
                Completed ({completedJobs.length})
              </Typography>
              <List disablePadding>
                {completedJobs.slice(0, 10).map(job => (
                  <ExportJobItem
                    key={job.id}
                    job={job}
                    onDownload={handleDownload}
                    onRefresh={handleRefreshJob}
                  />
                ))}
              </List>
              {completedJobs.length > 10 && (
                <Typography variant="caption" color="text.secondary">
                  Showing 10 of {completedJobs.length} completed exports
                </Typography>
              )}
            </Box>
          )}

          {/* Failed Exports */}
          {failedJobs.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, color: 'error.main', display: 'flex', alignItems: 'center', gap: 1 }}>
                <ErrorIcon fontSize="small" />
                Failed ({failedJobs.length})
              </Typography>
              <List disablePadding>
                {failedJobs.slice(0, 5).map(job => (
                  <ExportJobItem
                    key={job.id}
                    job={job}
                    onDownload={handleDownload}
                    onRefresh={handleRefreshJob}
                  />
                ))}
              </List>
            </Box>
          )}

          {exportJobs.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
              No export history yet. Export a survey to see it here.
            </Typography>
          )}
        </TabPanel>

        {/* Help Tab */}
        <TabPanel value={activeTab} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <CSVIcon color="secondary" />
                    <Typography variant="h6">CSV Export</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Comma-separated values file containing all measurements.
                    Can be imported into QGIS as a delimited text layer, or opened in Excel/LibreOffice.
                  </Typography>
                  <Typography variant="subtitle2" gutterBottom>Columns included:</Typography>
                  <Typography variant="body2" component="ul" sx={{ pl: 2 }}>
                    <li>frequency (Hz)</li>
                    <li>power_dbm</li>
                    <li>latitude, longitude, altitude</li>
                    <li>timestamp</li>
                    <li>bandwidth, noise_floor_dbm, snr_db</li>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <GeoPackageIcon color="primary" />
                    <Typography variant="h6">GeoPackage Export</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Native QGIS spatial format with multiple layers. Best choice for GIS analysis and visualization.
                  </Typography>
                  <Typography variant="subtitle2" gutterBottom>Layers included:</Typography>
                  <Typography variant="body2" component="ul" sx={{ pl: 2 }}>
                    <li><strong>all_measurements</strong> - Point layer with all data</li>
                    <li><strong>Frequency bands</strong> - Separate layers by band (FM, VHF, UHF, etc.)</li>
                    <li><strong>Heatmap</strong> - Interpolated signal strength raster (optional)</li>
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Alert severity="info">
                <AlertTitle>QGIS Import Tips</AlertTitle>
                <Typography variant="body2">
                  <strong>GeoPackage:</strong> Drag the .gpkg file into QGIS or use Layer → Add Layer → Add Vector Layer.
                  All layers will be available in a single file.
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <strong>CSV:</strong> Use Layer → Add Layer → Add Delimited Text Layer. Set X field to "longitude"
                  and Y field to "latitude". Use EPSG:4326 (WGS84) as the CRS.
                </Typography>
              </Alert>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

      {/* Export Options Dialog */}
      <ExportOptionsDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        survey={selectedSurvey}
        onExport={handleExport}
      />
    </Box>
  )
}

export default ExportManager
