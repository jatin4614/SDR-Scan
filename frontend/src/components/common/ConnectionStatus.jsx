import { useState, useEffect } from 'react'
import {
  Box,
  Chip,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import {
  Wifi as ConnectedIcon,
  WifiOff as DisconnectedIcon,
  Sync as ConnectingIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'
import { useStore } from '../../store/useStore'
import { api } from '../../services/api'

/**
 * ConnectionStatus Component
 *
 * Displays the current connection status and provides reconnection options
 */
function ConnectionStatus({ showDetails = false }) {
  const { connectionStatus, setConnectionStatus } = useStore()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [healthCheck, setHealthCheck] = useState(null)
  const [checking, setChecking] = useState(false)

  // Perform health check
  const performHealthCheck = async () => {
    setChecking(true)
    try {
      const result = await api.healthCheck()
      setHealthCheck({
        success: true,
        timestamp: new Date().toISOString(),
        ...result,
      })
      setConnectionStatus('connected')
    } catch (error) {
      setHealthCheck({
        success: false,
        timestamp: new Date().toISOString(),
        error: error.message,
      })
      setConnectionStatus('disconnected')
    } finally {
      setChecking(false)
    }
  }

  // Initial health check
  useEffect(() => {
    performHealthCheck()

    // Periodic health check every 30 seconds
    const interval = setInterval(performHealthCheck, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <ConnectedIcon sx={{ color: 'success.main' }} />
      case 'connecting':
        return <ConnectingIcon sx={{ color: 'warning.main', animation: 'spin 1s linear infinite' }} />
      case 'disconnected':
      default:
        return <DisconnectedIcon sx={{ color: 'error.main' }} />
    }
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'success'
      case 'connecting':
        return 'warning'
      case 'disconnected':
      default:
        return 'error'
    }
  }

  const getStatusLabel = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'disconnected':
      default:
        return 'Disconnected'
    }
  }

  if (!showDetails) {
    return (
      <Tooltip title={`Server: ${getStatusLabel()}`}>
        <Chip
          icon={getStatusIcon()}
          label={getStatusLabel()}
          size="small"
          color={getStatusColor()}
          variant="outlined"
          onClick={() => setDialogOpen(true)}
          sx={{ cursor: 'pointer' }}
        />
      </Tooltip>
    )
  }

  return (
    <>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          cursor: 'pointer',
        }}
        onClick={() => setDialogOpen(true)}
      >
        {getStatusIcon()}
        <Typography variant="body2">{getStatusLabel()}</Typography>
      </Box>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Connection Status
        </DialogTitle>
        <DialogContent>
          {checking && <LinearProgress sx={{ mb: 2 }} />}

          <Alert
            severity={connectionStatus === 'connected' ? 'success' : 'error'}
            sx={{ mb: 2 }}
          >
            {connectionStatus === 'connected'
              ? 'Successfully connected to the backend server.'
              : 'Unable to connect to the backend server.'
            }
          </Alert>

          {healthCheck && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Last Health Check
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    {healthCheck.success ? (
                      <CheckIcon color="success" />
                    ) : (
                      <ErrorIcon color="error" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary="API Server"
                    secondary={healthCheck.success ? 'Online' : healthCheck.error}
                  />
                </ListItem>
                {healthCheck.database_status !== undefined && (
                  <ListItem>
                    <ListItemIcon>
                      {healthCheck.database_status === 'ok' ? (
                        <CheckIcon color="success" />
                      ) : (
                        <WarningIcon color="warning" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary="Database"
                      secondary={healthCheck.database_status === 'ok' ? 'Connected' : 'Issues detected'}
                    />
                  </ListItem>
                )}
                {healthCheck.sdr_available !== undefined && (
                  <ListItem>
                    <ListItemIcon>
                      {healthCheck.sdr_available ? (
                        <CheckIcon color="success" />
                      ) : (
                        <WarningIcon color="warning" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary="SDR Device"
                      secondary={healthCheck.sdr_available ? 'Available' : 'Not detected'}
                    />
                  </ListItem>
                )}
                <ListItem>
                  <ListItemText
                    primary="Checked at"
                    secondary={new Date(healthCheck.timestamp).toLocaleString()}
                  />
                </ListItem>
              </List>
            </Box>
          )}

          {connectionStatus === 'disconnected' && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                Make sure the backend server is running on port 8000.
                Run <code>uvicorn api.main:app --reload</code> in the backend directory.
              </Typography>
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={performHealthCheck}
            disabled={checking}
          >
            {checking ? 'Checking...' : 'Check Connection'}
          </Button>
        </DialogActions>
      </Dialog>

      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
    </>
  )
}

export default ConnectionStatus
