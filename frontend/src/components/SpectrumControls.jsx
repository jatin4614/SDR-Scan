import { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  TextField,
  Slider,
  Button,
  ButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Collapse,
  IconButton,
  Tooltip,
  Chip,
  Divider,
  InputAdornment,
} from '@mui/material'
import {
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Tune as TuneIcon,
  Speed as SpeedIcon,
  Straighten as RulerIcon,
  AutoGraph as AutoIcon,
} from '@mui/icons-material'

// Preset frequency configurations
const frequencyPresets = [
  { label: 'FM Radio', center: 98e6, span: 20e6 },
  { label: 'VHF Air', center: 125e6, span: 20e6 },
  { label: 'Marine VHF', center: 160e6, span: 8e6 },
  { label: '433 ISM', center: 433.92e6, span: 2e6 },
  { label: '868 ISM', center: 868e6, span: 4e6 },
  { label: '915 ISM', center: 915e6, span: 26e6 },
  { label: 'WiFi 2.4G', center: 2.45e9, span: 100e6 },
]

// Resolution bandwidth options
const rbwOptions = [
  { label: '1 kHz', value: 1000 },
  { label: '3 kHz', value: 3000 },
  { label: '10 kHz', value: 10000 },
  { label: '30 kHz', value: 30000 },
  { label: '100 kHz', value: 100000 },
  { label: '300 kHz', value: 300000 },
  { label: '1 MHz', value: 1000000 },
]

// Update rate options
const updateRates = [
  { label: 'Fast (100ms)', value: 0.1 },
  { label: 'Normal (250ms)', value: 0.25 },
  { label: 'Medium (500ms)', value: 0.5 },
  { label: 'Slow (1s)', value: 1.0 },
  { label: 'Very Slow (2s)', value: 2.0 },
]

function SpectrumControls({
  settings = {},
  onSettingsChange,
  onApply,
  devices = [],
  selectedDevice,
  onDeviceChange,
  isStreaming = false,
  onStartStop,
  compact = false,
}) {
  const [expanded, setExpanded] = useState(!compact)

  // Local state for editing
  const [localSettings, setLocalSettings] = useState({
    centerFrequency: settings.centerFrequency || 100e6,
    span: settings.span || 2.4e6,
    rbw: settings.rbw || 100000,
    gain: settings.gain || 30,
    referenceLevel: settings.referenceLevel || -20,
    noiseFloor: settings.noiseFloor || -120,
    averaging: settings.averaging || 1,
    peakHold: settings.peakHold || false,
    autoScale: settings.autoScale || true,
    updateRate: settings.updateRate || 0.5,
    ...settings,
  })

  const updateLocal = useCallback((key, value) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleApply = useCallback(() => {
    if (onSettingsChange) {
      onSettingsChange(localSettings)
    }
    if (onApply) {
      onApply(localSettings)
    }
  }, [localSettings, onSettingsChange, onApply])

  const handlePresetSelect = useCallback((preset) => {
    setLocalSettings(prev => ({
      ...prev,
      centerFrequency: preset.center,
      span: preset.span,
    }))
  }, [])

  const formatFrequency = (hz) => {
    if (hz >= 1e9) return `${(hz / 1e9).toFixed(3)} GHz`
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`
    if (hz >= 1e3) return `${(hz / 1e3).toFixed(3)} kHz`
    return `${hz} Hz`
  }

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: compact ? 0 : 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TuneIcon color="primary" />
          <Typography variant="subtitle1">Spectrum Controls</Typography>
          {isStreaming && (
            <Chip size="small" color="success" label="LIVE" />
          )}
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            variant={isStreaming ? 'outlined' : 'contained'}
            color={isStreaming ? 'error' : 'primary'}
            size="small"
            onClick={onStartStop}
          >
            {isStreaming ? 'Stop' : 'Start'}
          </Button>
          {compact && (
            <IconButton size="small" onClick={() => setExpanded(!expanded)}>
              {expanded ? <CollapseIcon /> : <ExpandIcon />}
            </IconButton>
          )}
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Grid container spacing={2}>
          {/* Frequency Presets */}
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary" gutterBottom display="block">
              Quick Presets
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {frequencyPresets.map((preset) => (
                <Chip
                  key={preset.label}
                  label={preset.label}
                  size="small"
                  onClick={() => handlePresetSelect(preset)}
                  variant={
                    localSettings.centerFrequency === preset.center &&
                    localSettings.span === preset.span
                      ? 'filled' : 'outlined'
                  }
                  color="primary"
                />
              ))}
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Divider />
          </Grid>

          {/* Frequency Controls */}
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Center Frequency"
              type="number"
              size="small"
              fullWidth
              value={localSettings.centerFrequency / 1e6}
              onChange={(e) => updateLocal('centerFrequency', parseFloat(e.target.value) * 1e6 || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end">MHz</InputAdornment>,
              }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Span"
              type="number"
              size="small"
              fullWidth
              value={localSettings.span / 1e6}
              onChange={(e) => updateLocal('span', parseFloat(e.target.value) * 1e6 || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end">MHz</InputAdornment>,
              }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControl size="small" fullWidth>
              <InputLabel>RBW</InputLabel>
              <Select
                value={localSettings.rbw}
                label="RBW"
                onChange={(e) => updateLocal('rbw', e.target.value)}
              >
                {rbwOptions.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControl size="small" fullWidth>
              <InputLabel>Device</InputLabel>
              <Select
                value={selectedDevice?.id || ''}
                label="Device"
                onChange={(e) => onDeviceChange?.(devices.find(d => d.id === e.target.value))}
              >
                {devices.map((device) => (
                  <MenuItem key={device.id} value={device.id}>{device.name}</MenuItem>
                ))}
                {devices.length === 0 && (
                  <MenuItem value="" disabled>No devices</MenuItem>
                )}
              </Select>
            </FormControl>
          </Grid>

          {/* Display Range */}
          <Grid item xs={12} md={6}>
            <Typography variant="caption" color="text.secondary">
              <RulerIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
              Display Range: {localSettings.noiseFloor} to {localSettings.referenceLevel} dBm
            </Typography>
            <Slider
              value={[localSettings.noiseFloor, localSettings.referenceLevel]}
              onChange={(e, v) => {
                updateLocal('noiseFloor', v[0])
                updateLocal('referenceLevel', v[1])
              }}
              min={-140}
              max={0}
              valueLabelDisplay="auto"
              size="small"
            />
          </Grid>

          {/* Gain Control */}
          <Grid item xs={12} md={6}>
            <Typography variant="caption" color="text.secondary">
              <SpeedIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'middle' }} />
              Gain: {localSettings.gain} dB
            </Typography>
            <Slider
              value={localSettings.gain}
              onChange={(e, v) => updateLocal('gain', v)}
              min={0}
              max={50}
              valueLabelDisplay="auto"
              size="small"
            />
          </Grid>

          {/* Advanced Options */}
          <Grid item xs={12} sm={4}>
            <FormControl size="small" fullWidth>
              <InputLabel>Update Rate</InputLabel>
              <Select
                value={localSettings.updateRate}
                label="Update Rate"
                onChange={(e) => updateLocal('updateRate', e.target.value)}
              >
                {updateRates.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              label="Averaging"
              type="number"
              size="small"
              fullWidth
              value={localSettings.averaging}
              onChange={(e) => updateLocal('averaging', Math.max(1, parseInt(e.target.value) || 1))}
              inputProps={{ min: 1, max: 100 }}
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={localSettings.peakHold}
                    onChange={(e) => updateLocal('peakHold', e.target.checked)}
                  />
                }
                label="Peak Hold"
              />
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={localSettings.autoScale}
                    onChange={(e) => updateLocal('autoScale', e.target.checked)}
                  />
                }
                label={<><AutoIcon sx={{ fontSize: 16, mr: 0.5 }} />Auto</>}
              />
            </Box>
          </Grid>

          {/* Current Settings Summary */}
          <Grid item xs={12}>
            <Box sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              bgcolor: 'background.default',
              p: 1,
              borderRadius: 1,
            }}>
              <Typography variant="caption" color="text.secondary">
                Range: {formatFrequency(localSettings.centerFrequency - localSettings.span / 2)} —{' '}
                {formatFrequency(localSettings.centerFrequency + localSettings.span / 2)}
              </Typography>
              <Button
                variant="contained"
                size="small"
                onClick={handleApply}
              >
                Apply Settings
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Collapse>
    </Paper>
  )
}

export default SpectrumControls
