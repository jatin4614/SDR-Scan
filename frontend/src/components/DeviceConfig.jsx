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
  Slider,
  Switch,
  FormControlLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as TestIcon,
  Router as DeviceIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { useStore } from '../store/useStore'
import { api } from '../services/api'

function DeviceConfig() {
  const {
    devices,
    setDevices,
    addDevice,
    updateDevice,
    removeDevice,
    selectedDevice,
    setSelectedDevice,
    loading,
    setLoading,
  } = useStore()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingDevice, setEditingDevice] = useState(null)
  const [detectedDevices, setDetectedDevices] = useState([])
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)

  const [formData, setFormData] = useState({
    name: '',
    device_type: 'rtlsdr',
    serial_number: '',
    sample_rate: 2400000,
    gain: 30,
    calibration_offset: 0,
    is_active: true,
  })

  // Load devices on mount
  useEffect(() => {
    async function loadDevices() {
      try {
        setLoading('devices', true)
        const response = await api.getDevices()
        setDevices(response.devices || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading('devices', false)
      }
    }
    loadDevices()
  }, [setDevices, setLoading])

  const handleDetectDevices = async () => {
    try {
      setLoading('devices', true)
      setError(null)
      const response = await api.detectDevices()
      setDetectedDevices(response.devices || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('devices', false)
    }
  }

  const handleOpenDialog = (device = null) => {
    if (device) {
      setEditingDevice(device)
      setFormData({
        name: device.name,
        device_type: device.device_type,
        serial_number: device.serial_number || '',
        sample_rate: device.sample_rate,
        gain: device.gain,
        calibration_offset: device.calibration_offset || 0,
        is_active: device.is_active,
      })
    } else {
      setEditingDevice(null)
      setFormData({
        name: '',
        device_type: 'rtlsdr',
        serial_number: '',
        sample_rate: 2400000,
        gain: 30,
        calibration_offset: 0,
        is_active: true,
      })
    }
    setDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setDialogOpen(false)
    setEditingDevice(null)
    setTestResult(null)
  }

  const handleSaveDevice = async () => {
    try {
      setError(null)
      if (editingDevice) {
        const updated = await api.updateDevice(editingDevice.id, formData)
        updateDevice(editingDevice.id, updated)
      } else {
        const created = await api.createDevice(formData)
        addDevice(created)
      }
      handleCloseDialog()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteDevice = async (id) => {
    if (!window.confirm('Are you sure you want to delete this device?')) return

    try {
      await api.deleteDevice(id)
      removeDevice(id)
      if (selectedDevice?.id === id) {
        setSelectedDevice(null)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const handleTestDevice = async (id) => {
    try {
      setTestResult(null)
      const result = await api.testDevice(id)
      setTestResult(result)
    } catch (err) {
      setTestResult({ success: false, error: err.message })
    }
  }

  const handleAddDetectedDevice = (detected) => {
    setFormData({
      name: `${detected.device_type.toUpperCase()} - ${detected.serial_number || 'Unknown'}`,
      device_type: detected.device_type,
      serial_number: detected.serial_number || '',
      sample_rate: detected.sample_rate || 2400000,
      gain: 30,
      calibration_offset: 0,
      is_active: true,
    })
    setDialogOpen(true)
  }

  const getDeviceTypeColor = (type) => {
    switch (type) {
      case 'hackrf': return 'primary'
      case 'rtlsdr': return 'secondary'
      case 'mock': return 'default'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Header Actions */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                SDR Devices
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={handleDetectDevices}
                  disabled={loading.devices}
                >
                  Detect Devices
                </Button>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => handleOpenDialog()}
                >
                  Add Device
                </Button>
              </Box>
            </Box>
            {loading.devices && <LinearProgress sx={{ mt: 2 }} />}
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
          </Paper>
        </Grid>

        {/* Detected Devices */}
        {detectedDevices.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Detected Devices
              </Typography>
              <List>
                {detectedDevices.map((device, index) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={`${device.device_type.toUpperCase()} - ${device.serial_number || 'No Serial'}`}
                      secondary={`Sample Rate: ${(device.sample_rate / 1e6).toFixed(1)} MHz`}
                    />
                    <ListItemSecondaryAction>
                      <Button
                        size="small"
                        onClick={() => handleAddDetectedDevice(device)}
                      >
                        Add
                      </Button>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        )}

        {/* Device Cards */}
        {devices.length === 0 && !loading.devices && (
          <Grid item xs={12}>
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <DeviceIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography color="text.secondary">
                No devices configured. Click "Detect Devices" to find connected SDRs or "Add Device" to manually configure one.
              </Typography>
            </Paper>
          </Grid>
        )}

        {devices.map((device) => (
          <Grid item xs={12} sm={6} md={4} key={device.id}>
            <Card
              sx={{
                border: selectedDevice?.id === device.id ? 2 : 0,
                borderColor: 'primary.main',
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="h6" noWrap sx={{ maxWidth: '70%' }}>
                    {device.name}
                  </Typography>
                  <Chip
                    size="small"
                    label={device.device_type}
                    color={getDeviceTypeColor(device.device_type)}
                  />
                </Box>

                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Serial: {device.serial_number || 'N/A'}
                </Typography>

                <Divider sx={{ my: 1 }} />

                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Sample Rate
                    </Typography>
                    <Typography variant="body2">
                      {(device.sample_rate / 1e6).toFixed(1)} MHz
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Gain
                    </Typography>
                    <Typography variant="body2">
                      {device.gain} dB
                    </Typography>
                  </Grid>
                </Grid>

                <Box sx={{ mt: 1 }}>
                  <Chip
                    size="small"
                    icon={device.is_active ? <CheckIcon /> : <ErrorIcon />}
                    label={device.is_active ? 'Active' : 'Inactive'}
                    color={device.is_active ? 'success' : 'default'}
                  />
                </Box>
              </CardContent>

              <CardActions>
                <Button
                  size="small"
                  onClick={() => setSelectedDevice(device)}
                  disabled={selectedDevice?.id === device.id}
                >
                  {selectedDevice?.id === device.id ? 'Selected' : 'Select'}
                </Button>
                <IconButton size="small" onClick={() => handleTestDevice(device.id)}>
                  <TestIcon />
                </IconButton>
                <IconButton size="small" onClick={() => handleOpenDialog(device)}>
                  <EditIcon />
                </IconButton>
                <IconButton size="small" onClick={() => handleDeleteDevice(device.id)} color="error">
                  <DeleteIcon />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingDevice ? 'Edit Device' : 'Add Device'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                label="Device Name"
                fullWidth
                value={formData.name}
                onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Device Type</InputLabel>
                <Select
                  value={formData.device_type}
                  label="Device Type"
                  onChange={(e) => setFormData(f => ({ ...f, device_type: e.target.value }))}
                >
                  <MenuItem value="rtlsdr">RTL-SDR</MenuItem>
                  <MenuItem value="hackrf">HackRF</MenuItem>
                  <MenuItem value="mock">Mock (Testing)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Serial Number"
                fullWidth
                value={formData.serial_number}
                onChange={(e) => setFormData(f => ({ ...f, serial_number: e.target.value }))}
              />
            </Grid>

            <Grid item xs={12}>
              <Typography gutterBottom>
                Sample Rate: {(formData.sample_rate / 1e6).toFixed(1)} MHz
              </Typography>
              <Slider
                value={formData.sample_rate / 1e6}
                onChange={(e, v) => setFormData(f => ({ ...f, sample_rate: v * 1e6 }))}
                min={0.25}
                max={20}
                step={0.1}
                marks={[
                  { value: 0.25, label: '0.25' },
                  { value: 2.4, label: '2.4' },
                  { value: 10, label: '10' },
                  { value: 20, label: '20' },
                ]}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Typography gutterBottom>
                Gain: {formData.gain} dB
              </Typography>
              <Slider
                value={formData.gain}
                onChange={(e, v) => setFormData(f => ({ ...f, gain: v }))}
                min={0}
                max={50}
                step={1}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Calibration Offset (dB)"
                type="number"
                fullWidth
                value={formData.calibration_offset}
                onChange={(e) => setFormData(f => ({ ...f, calibration_offset: parseFloat(e.target.value) || 0 }))}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData(f => ({ ...f, is_active: e.target.checked }))}
                  />
                }
                label="Active"
              />
            </Grid>

            {testResult && (
              <Grid item xs={12}>
                <Alert severity={testResult.success ? 'success' : 'error'}>
                  {testResult.success ? 'Device test successful!' : `Test failed: ${testResult.error}`}
                </Alert>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveDevice}
            disabled={!formData.name}
          >
            {editingDevice ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DeviceConfig
