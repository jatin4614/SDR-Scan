import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Tabs,
  Tab,
  Divider,
} from '@mui/material'
import Plot from './Plot'
import { useStore } from '../store/useStore'
import { useSpectrumWebSocket } from '../hooks/useWebSocket'
import { api } from '../services/api'
import SpectrumControls from './SpectrumControls'
import WaterfallPlot from './WaterfallPlot'
import SignalAnnotation from './SignalAnnotation'
import MeasurementHistory from './MeasurementHistory'

function SpectrumViewer() {
  const {
    spectrumData,
    spectrumHistory,
    spectrumSettings,
    setSpectrumSettings,
    setSpectrumData,
    devices,
    setDevices,
    selectedDevice,
    setSelectedDevice,
    signals,
    setSignals,
  } = useStore()

  const [tabValue, setTabValue] = useState(0)
  const [annotations, setAnnotations] = useState([])
  const [peakHoldData, setPeakHoldData] = useState(null)
  const [playbackMode, setPlaybackMode] = useState(false)

  const { isConnected, sendMessage } = useSpectrumWebSocket(selectedDevice?.id)

  // Load devices on mount if the list is empty
  useEffect(() => {
    if (devices.length === 0) {
      api.getDevices().then(res => {
        const list = res.devices || []
        setDevices(list)
        if (!selectedDevice && list.length > 0) {
          setSelectedDevice(list[0])
        }
      }).catch(console.error)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Stop streaming when device changes
  const prevDeviceId = useRef(selectedDevice?.id)
  useEffect(() => {
    if (prevDeviceId.current !== selectedDevice?.id && spectrumSettings.isStreaming) {
      setSpectrumSettings({ isStreaming: false })
    }
    prevDeviceId.current = selectedDevice?.id
  }, [selectedDevice?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle settings change
  const handleSettingsChange = useCallback((newSettings) => {
    setSpectrumSettings({
      centerFrequency: newSettings.centerFrequency,
      bandwidth: newSettings.span,
      updateInterval: newSettings.updateRate,
    })
  }, [setSpectrumSettings])

  // Handle start/stop streaming
  const handleStartStop = useCallback(() => {
    if (spectrumSettings.isStreaming) {
      setSpectrumSettings({ isStreaming: false })
      sendMessage({ type: 'pause' })
    } else {
      if (!selectedDevice?.id || !isConnected) {
        console.warn('Cannot start streaming: no device selected or not connected')
        return
      }
      setSpectrumSettings({ isStreaming: true })
      sendMessage({
        type: 'config',
        device_id: selectedDevice?.id,
        center_freq: spectrumSettings.centerFrequency,
        bandwidth: spectrumSettings.bandwidth,
        interval: spectrumSettings.updateInterval,
      })
      sendMessage({ type: 'resume' })
    }
  }, [spectrumSettings, setSpectrumSettings, sendMessage, selectedDevice, isConnected])

  // Handle apply settings
  const handleApplySettings = useCallback((settings) => {
    if (spectrumSettings.isStreaming) {
      sendMessage({
        type: 'config',
        device_id: selectedDevice?.id,
        center_freq: settings.centerFrequency,
        bandwidth: settings.span,
        interval: settings.updateRate,
      })
    }
  }, [spectrumSettings.isStreaming, sendMessage, selectedDevice])

  // Update peak hold data
  useEffect(() => {
    if (!spectrumData?.power_dbm || !spectrumSettings.peakHold) return

    setPeakHoldData(prev => {
      if (!prev) return [...spectrumData.power_dbm]
      return spectrumData.power_dbm.map((val, i) =>
        Math.max(val, prev[i] || -200)
      )
    })
  }, [spectrumData, spectrumSettings.peakHold])

  // Clear peak hold when disabled
  useEffect(() => {
    if (!spectrumSettings.peakHold) {
      setPeakHoldData(null)
    }
  }, [spectrumSettings.peakHold])

  // Prepare spectrum plot data
  const spectrumPlotData = useMemo(() => {
    const data = []

    // Main spectrum trace
    if (spectrumData?.power_dbm) {
      data.push({
        x: spectrumData.frequencies?.map(f => f / 1e6) || [],
        y: spectrumData.power_dbm,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(0, 188, 212, 0.2)',
        line: { color: '#00bcd4', width: 1.5 },
        name: 'Power',
      })
    }

    // Peak hold trace
    if (peakHoldData && spectrumData?.frequencies) {
      data.push({
        x: spectrumData.frequencies.map(f => f / 1e6),
        y: peakHoldData,
        type: 'scatter',
        mode: 'lines',
        line: { color: '#ff5722', width: 1, dash: 'dot' },
        name: 'Peak Hold',
      })
    }

    // Detected peaks markers
    if (spectrumData?.peaks?.length > 0) {
      data.push({
        x: spectrumData.peaks.map(p => p.frequency / 1e6),
        y: spectrumData.peaks.map(p => p.power_dbm),
        type: 'scatter',
        mode: 'markers+text',
        marker: {
          color: '#ff9800',
          size: 10,
          symbol: 'triangle-down',
        },
        text: spectrumData.peaks.map(p => `${(p.frequency / 1e6).toFixed(2)}`),
        textposition: 'top center',
        textfont: { size: 10, color: '#ff9800' },
        name: 'Peaks',
      })
    }

    // Annotation markers
    const visibleAnnotations = annotations.filter(a => a.visible !== false)
    if (visibleAnnotations.length > 0) {
      data.push({
        x: visibleAnnotations.map(a => a.frequency / 1e6),
        y: visibleAnnotations.map(a => spectrumSettings.referenceLevel || -20),
        type: 'scatter',
        mode: 'markers',
        marker: {
          color: visibleAnnotations.map(a => a.color || '#9c27b0'),
          size: 12,
          symbol: 'diamond',
        },
        name: 'Annotations',
        hovertemplate: visibleAnnotations.map(a =>
          `${a.name}<br>${(a.frequency / 1e6).toFixed(3)} MHz<extra></extra>`
        ),
      })
    }

    return data
  }, [spectrumData, peakHoldData, annotations, spectrumSettings.referenceLevel])

  // Annotation shapes for frequency bands
  const annotationShapes = useMemo(() => {
    const shapes = []
    annotations.filter(a => a.visible !== false && a.bandwidth).forEach(ann => {
      shapes.push({
        type: 'rect',
        x0: (ann.frequency - ann.bandwidth / 2) / 1e6,
        x1: (ann.frequency + ann.bandwidth / 2) / 1e6,
        y0: spectrumSettings.noiseFloor || -120,
        y1: spectrumSettings.referenceLevel || -20,
        fillcolor: ann.color || '#9c27b0',
        opacity: 0.1,
        line: { width: 0 },
      })
    })
    return shapes
  }, [annotations, spectrumSettings.noiseFloor, spectrumSettings.referenceLevel])

  // Handle annotation click - center on frequency
  const handleAnnotationClick = useCallback((annotation) => {
    setSpectrumSettings({
      centerFrequency: annotation.frequency,
    })
    if (spectrumSettings.isStreaming) {
      sendMessage({
        type: 'config',
        device_id: selectedDevice?.id,
        center_freq: annotation.frequency,
      })
    }
  }, [setSpectrumSettings, spectrumSettings.isStreaming, sendMessage, selectedDevice])

  // Handle playback data from history component
  const handlePlaybackData = useCallback((measurements) => {
    if (!measurements?.length) return

    // Convert measurements to spectrum format
    const frequencies = measurements.map(m => m.frequency)
    const powers = measurements.map(m => m.power_dbm)

    setSpectrumData({
      frequencies,
      power_dbm: powers,
      timestamp: measurements[0].timestamp,
      peaks: [], // Could calculate peaks from data
    })
    setPlaybackMode(true)
  }, [setSpectrumData])

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Spectrum Controls */}
        <Grid item xs={12}>
          <SpectrumControls
            settings={{
              centerFrequency: spectrumSettings.centerFrequency,
              span: spectrumSettings.bandwidth,
              rbw: spectrumSettings.rbw || 100000,
              gain: spectrumSettings.gain || 30,
              referenceLevel: spectrumSettings.referenceLevel || -20,
              noiseFloor: spectrumSettings.noiseFloor || -120,
              averaging: spectrumSettings.averaging || 1,
              peakHold: spectrumSettings.peakHold || false,
              autoScale: spectrumSettings.autoScale || true,
              updateRate: spectrumSettings.updateInterval || 0.5,
            }}
            onSettingsChange={handleSettingsChange}
            onApply={handleApplySettings}
            devices={devices}
            selectedDevice={selectedDevice}
            onDeviceChange={setSelectedDevice}
            isStreaming={spectrumSettings.isStreaming}
            onStartStop={handleStartStop}
          />
        </Grid>

        {/* Main Spectrum Plot */}
        <Grid item xs={12} lg={9}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6">
                {playbackMode ? 'Playback' : 'Live'} Spectrum
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {spectrumSettings.isStreaming && (
                  <Chip size="small" color="success" label="LIVE" />
                )}
                {playbackMode && (
                  <Chip size="small" color="warning" label="PLAYBACK" />
                )}
                {spectrumSettings.peakHold && (
                  <Chip size="small" variant="outlined" label="Peak Hold" />
                )}
              </Box>
            </Box>
            <Plot
              data={spectrumPlotData}
              layout={{
                autosize: true,
                height: 400,
                margin: { l: 60, r: 30, t: 10, b: 50 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'rgba(19, 47, 76, 0.5)',
                font: { color: '#ffffff' },
                xaxis: {
                  title: 'Frequency (MHz)',
                  gridcolor: 'rgba(255,255,255,0.1)',
                  zerolinecolor: 'rgba(255,255,255,0.2)',
                },
                yaxis: {
                  title: 'Power (dBm)',
                  gridcolor: 'rgba(255,255,255,0.1)',
                  zerolinecolor: 'rgba(255,255,255,0.2)',
                  range: [
                    spectrumSettings.noiseFloor || -120,
                    spectrumSettings.referenceLevel || -20
                  ],
                },
                showlegend: true,
                legend: { x: 1, xanchor: 'right', y: 1, bgcolor: 'rgba(0,0,0,0.5)' },
                shapes: annotationShapes,
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%' }}
            />
          </Paper>
        </Grid>

        {/* Sidebar - Stats & Annotations */}
        <Grid item xs={12} lg={3}>
          <Grid container spacing={2}>
            {/* Stats Cards */}
            <Grid item xs={6} lg={12}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" variant="caption">
                    Noise Floor
                  </Typography>
                  <Typography variant="h5">
                    {spectrumData?.noise_floor?.toFixed(1) || '--'} dBm
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} lg={12}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" variant="caption">
                    Detected Peaks
                  </Typography>
                  <Typography variant="h5">
                    {spectrumData?.peaks?.length || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} lg={12}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" variant="caption">
                    Connection
                  </Typography>
                  <Chip
                    label={isConnected ? 'Connected' : 'Disconnected'}
                    color={isConnected ? 'success' : 'error'}
                    size="small"
                  />
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} lg={12}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" variant="caption">
                    Center Freq
                  </Typography>
                  <Typography variant="h6">
                    {(spectrumSettings.centerFrequency / 1e6).toFixed(2)} MHz
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Tabs for Waterfall / Annotations / History */}
        <Grid item xs={12}>
          <Paper sx={{ mb: 0 }}>
            <Tabs
              value={tabValue}
              onChange={(e, v) => setTabValue(v)}
              variant="fullWidth"
            >
              <Tab label="Waterfall" />
              <Tab label="Annotations" />
              <Tab label="History" />
            </Tabs>
          </Paper>
        </Grid>

        {/* Tab Content */}
        <Grid item xs={12}>
          {tabValue === 0 && (
            <WaterfallPlot
              data={spectrumHistory.map(h => h.power_dbm || [])}
              frequencies={spectrumData?.frequencies || []}
              timeLabels={spectrumHistory.map(h => h.timestamp)}
              minPower={spectrumSettings.noiseFloor || -120}
              maxPower={spectrumSettings.referenceLevel || -20}
              height={300}
              onFrequencySelect={(freq) => {
                setSpectrumSettings({ centerFrequency: freq })
              }}
            />
          )}

          {tabValue === 1 && (
            <SignalAnnotation
              annotations={annotations}
              onAnnotationAdd={(ann) => setAnnotations(prev => [...prev, ann])}
              onAnnotationUpdate={(ann) => setAnnotations(prev =>
                prev.map(a => a.id === ann.id ? ann : a)
              )}
              onAnnotationDelete={(id) => setAnnotations(prev =>
                prev.filter(a => a.id !== id)
              )}
              currentFrequency={spectrumSettings.centerFrequency}
              frequencyRange={{
                start: spectrumSettings.centerFrequency - spectrumSettings.bandwidth / 2,
                end: spectrumSettings.centerFrequency + spectrumSettings.bandwidth / 2,
              }}
              onAnnotationClick={handleAnnotationClick}
            />
          )}

          {tabValue === 2 && (
            <MeasurementHistory
              onPlaybackData={handlePlaybackData}
              onMeasurementSelect={(m) => {
                console.log('Selected measurement:', m)
              }}
            />
          )}
        </Grid>
      </Grid>
    </Box>
  )
}

export default SpectrumViewer
