import { useState, useMemo } from 'react'
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Tooltip,
  Collapse,
  Badge,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as ShowIcon,
  VisibilityOff as HideIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Label as LabelIcon,
  Radio as SignalIcon,
} from '@mui/icons-material'

// Known frequency allocations
const knownBands = [
  { name: 'FM Broadcast', start: 88e6, end: 108e6, color: '#4caf50' },
  { name: 'VHF TV Low', start: 54e6, end: 88e6, color: '#2196f3' },
  { name: 'VHF TV High', start: 174e6, end: 216e6, color: '#2196f3' },
  { name: 'UHF TV', start: 470e6, end: 608e6, color: '#9c27b0' },
  { name: 'Cellular 700', start: 698e6, end: 806e6, color: '#ff9800' },
  { name: 'Cellular 850', start: 824e6, end: 894e6, color: '#ff9800' },
  { name: 'ISM 433', start: 433.05e6, end: 434.79e6, color: '#e91e63' },
  { name: 'ISM 915', start: 902e6, end: 928e6, color: '#e91e63' },
  { name: 'WiFi 2.4', start: 2.4e9, end: 2.5e9, color: '#00bcd4' },
  { name: 'GPS L1', start: 1575.42e6 - 10e6, end: 1575.42e6 + 10e6, color: '#795548' },
]

// Signal type options
const signalTypes = [
  'Unknown',
  'FM Broadcast',
  'AM Broadcast',
  'TV Analog',
  'TV Digital',
  'Cellular',
  'WiFi',
  'Bluetooth',
  'ISM Device',
  'Amateur Radio',
  'Aviation',
  'Marine',
  'Public Safety',
  'Pager',
  'Radar',
  'Satellite',
  'Other',
]

function SignalAnnotation({
  annotations = [],
  onAnnotationAdd,
  onAnnotationUpdate,
  onAnnotationDelete,
  currentFrequency,
  frequencyRange = { start: 0, end: 1e9 },
  onAnnotationClick,
  showBands = true,
}) {
  const [expanded, setExpanded] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingAnnotation, setEditingAnnotation] = useState(null)
  const [showHidden, setShowHidden] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    frequency: 0,
    bandwidth: 200000,
    signalType: 'Unknown',
    description: '',
    color: '#00bcd4',
    visible: true,
  })

  // Filter bands visible in current frequency range
  const visibleBands = useMemo(() => {
    if (!showBands) return []
    return knownBands.filter(band =>
      band.end >= frequencyRange.start && band.start <= frequencyRange.end
    )
  }, [showBands, frequencyRange])

  // Filter annotations
  const visibleAnnotations = useMemo(() => {
    return annotations.filter(a => showHidden || a.visible)
  }, [annotations, showHidden])

  const handleOpenDialog = (annotation = null) => {
    if (annotation) {
      setEditingAnnotation(annotation)
      setFormData({
        name: annotation.name || '',
        frequency: annotation.frequency || currentFrequency || 0,
        bandwidth: annotation.bandwidth || 200000,
        signalType: annotation.signalType || 'Unknown',
        description: annotation.description || '',
        color: annotation.color || '#00bcd4',
        visible: annotation.visible !== false,
      })
    } else {
      setEditingAnnotation(null)
      setFormData({
        name: '',
        frequency: currentFrequency || frequencyRange.start,
        bandwidth: 200000,
        signalType: 'Unknown',
        description: '',
        color: '#00bcd4',
        visible: true,
      })
    }
    setDialogOpen(true)
  }

  const handleSave = () => {
    const annotation = {
      ...formData,
      id: editingAnnotation?.id || `ann_${Date.now()}`,
    }

    if (editingAnnotation) {
      onAnnotationUpdate?.(annotation)
    } else {
      onAnnotationAdd?.(annotation)
    }
    setDialogOpen(false)
  }

  const handleDelete = (id) => {
    if (window.confirm('Delete this annotation?')) {
      onAnnotationDelete?.(id)
    }
  }

  const toggleVisibility = (annotation) => {
    onAnnotationUpdate?.({
      ...annotation,
      visible: !annotation.visible,
    })
  }

  const formatFrequency = (hz) => {
    if (hz >= 1e9) return `${(hz / 1e9).toFixed(3)} GHz`
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`
    return `${(hz / 1e3).toFixed(3)} kHz`
  }

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LabelIcon color="primary" />
          <Typography variant="subtitle1">Signal Annotations</Typography>
          <Badge badgeContent={annotations.length} color="primary">
            <SignalIcon />
          </Badge>
        </Box>
        <Box>
          <Tooltip title="Add Annotation">
            <IconButton size="small" onClick={() => handleOpenDialog()}>
              <AddIcon />
            </IconButton>
          </Tooltip>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded}>
        {/* Known Bands */}
        {visibleBands.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" gutterBottom display="block">
              Known Frequency Bands
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {visibleBands.map((band) => (
                <Chip
                  key={band.name}
                  label={band.name}
                  size="small"
                  sx={{
                    bgcolor: band.color,
                    color: 'white',
                    opacity: 0.8,
                  }}
                  onClick={() => onAnnotationClick?.({
                    frequency: (band.start + band.end) / 2,
                    bandwidth: band.end - band.start,
                  })}
                />
              ))}
            </Box>
          </Box>
        )}

        {/* User Annotations */}
        {visibleAnnotations.length > 0 ? (
          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
            {visibleAnnotations.map((annotation) => (
              <ListItem
                key={annotation.id}
                sx={{
                  bgcolor: 'background.default',
                  mb: 0.5,
                  borderRadius: 1,
                  borderLeft: 3,
                  borderColor: annotation.color || 'primary.main',
                  opacity: annotation.visible ? 1 : 0.5,
                }}
                button
                onClick={() => onAnnotationClick?.(annotation)}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2">{annotation.name || 'Unnamed'}</Typography>
                      <Chip
                        size="small"
                        label={annotation.signalType}
                        variant="outlined"
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      {formatFrequency(annotation.frequency)}
                      {annotation.bandwidth && ` (BW: ${formatFrequency(annotation.bandwidth)})`}
                    </>
                  }
                />
                <ListItemSecondaryAction>
                  <Tooltip title={annotation.visible ? 'Hide' : 'Show'}>
                    <IconButton size="small" onClick={() => toggleVisibility(annotation)}>
                      {annotation.visible ? <ShowIcon fontSize="small" /> : <HideIcon fontSize="small" />}
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => handleOpenDialog(annotation)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" onClick={() => handleDelete(annotation.id)} color="error">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
            No annotations yet. Click "+" to add one.
          </Typography>
        )}

        {/* Show Hidden Toggle */}
        {annotations.some(a => !a.visible) && (
          <Button
            size="small"
            onClick={() => setShowHidden(!showHidden)}
            startIcon={showHidden ? <HideIcon /> : <ShowIcon />}
            sx={{ mt: 1 }}
          >
            {showHidden ? 'Hide Hidden' : 'Show Hidden'}
          </Button>
        )}
      </Collapse>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingAnnotation ? 'Edit Annotation' : 'Add Annotation'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                label="Name"
                fullWidth
                value={formData.name}
                onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Frequency (MHz)"
                type="number"
                fullWidth
                value={formData.frequency / 1e6}
                onChange={(e) => setFormData(f => ({ ...f, frequency: parseFloat(e.target.value) * 1e6 || 0 }))}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Bandwidth (kHz)"
                type="number"
                fullWidth
                value={formData.bandwidth / 1e3}
                onChange={(e) => setFormData(f => ({ ...f, bandwidth: parseFloat(e.target.value) * 1e3 || 0 }))}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Signal Type</InputLabel>
                <Select
                  value={formData.signalType}
                  label="Signal Type"
                  onChange={(e) => setFormData(f => ({ ...f, signalType: e.target.value }))}
                >
                  {signalTypes.map((type) => (
                    <MenuItem key={type} value={type}>{type}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Color"
                type="color"
                fullWidth
                value={formData.color}
                onChange={(e) => setFormData(f => ({ ...f, color: e.target.value }))}
                InputProps={{
                  startAdornment: (
                    <Box
                      sx={{
                        width: 24,
                        height: 24,
                        borderRadius: 1,
                        bgcolor: formData.color,
                        mr: 1,
                      }}
                    />
                  ),
                }}
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
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}>
            {editingAnnotation ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  )
}

export default SignalAnnotation
