import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import {
  Snackbar,
  Alert,
  AlertTitle,
  Slide,
  IconButton,
  Box,
  Typography,
  LinearProgress,
} from '@mui/material'
import {
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useStore } from '../../store/useStore'

/**
 * Slide transition for snackbar
 */
function SlideTransition(props) {
  return <Slide {...props} direction="up" />
}

/**
 * Get icon for notification type
 */
function getNotificationIcon(type) {
  switch (type) {
    case 'success':
      return <SuccessIcon />
    case 'error':
      return <ErrorIcon />
    case 'warning':
      return <WarningIcon />
    case 'info':
    default:
      return <InfoIcon />
  }
}

/**
 * Single Notification component
 */
function Notification({
  notification,
  onClose,
  autoHideDuration = 6000,
}) {
  const [progress, setProgress] = useState(100)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (paused || !autoHideDuration) return

    const startTime = Date.now()
    const endTime = startTime + autoHideDuration

    const timer = setInterval(() => {
      const now = Date.now()
      const remaining = Math.max(0, endTime - now)
      const newProgress = (remaining / autoHideDuration) * 100

      setProgress(newProgress)

      if (remaining <= 0) {
        clearInterval(timer)
        onClose()
      }
    }, 100)

    return () => clearInterval(timer)
  }, [autoHideDuration, onClose, paused])

  const handleMouseEnter = () => setPaused(true)
  const handleMouseLeave = () => setPaused(false)

  return (
    <Snackbar
      open={true}
      TransitionComponent={SlideTransition}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Alert
        severity={notification.type || 'info'}
        icon={getNotificationIcon(notification.type)}
        action={
          <IconButton
            size="small"
            color="inherit"
            onClick={onClose}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        }
        sx={{
          minWidth: 300,
          maxWidth: 450,
          boxShadow: 3,
        }}
      >
        {notification.title && (
          <AlertTitle>{notification.title}</AlertTitle>
        )}
        <Typography variant="body2">
          {notification.message}
        </Typography>
        {autoHideDuration > 0 && (
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              mt: 1,
              height: 2,
              borderRadius: 1,
              bgcolor: 'rgba(255,255,255,0.2)',
              '& .MuiLinearProgress-bar': {
                bgcolor: 'rgba(255,255,255,0.5)',
              },
            }}
          />
        )}
      </Alert>
    </Snackbar>
  )
}

/**
 * Notification Stack component
 *
 * Displays multiple notifications stacked vertically
 */
function NotificationStack({ notifications, onClose }) {
  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 2000,
        display: 'flex',
        flexDirection: 'column-reverse',
        gap: 1,
      }}
    >
      {notifications.slice(-5).map((notification, index) => (
        <Alert
          key={notification.id}
          severity={notification.type || 'info'}
          icon={getNotificationIcon(notification.type)}
          onClose={() => onClose(notification.id)}
          sx={{
            minWidth: 300,
            maxWidth: 450,
            boxShadow: 3,
            animation: 'slideIn 0.3s ease-out',
            '@keyframes slideIn': {
              from: {
                transform: 'translateX(100%)',
                opacity: 0,
              },
              to: {
                transform: 'translateX(0)',
                opacity: 1,
              },
            },
          }}
        >
          {notification.title && (
            <AlertTitle>{notification.title}</AlertTitle>
          )}
          {notification.message}
        </Alert>
      ))}
    </Box>
  )
}

/**
 * NotificationProvider component
 *
 * Provides notification functionality and displays notifications from the store
 */
function NotificationProvider({ children }) {
  const { notifications, removeNotification } = useStore()
  const [localNotifications, setLocalNotifications] = useState([])

  // Sync store notifications to local state
  useEffect(() => {
    setLocalNotifications(notifications)
  }, [notifications])

  // Auto-dismiss notifications after timeout
  useEffect(() => {
    const timers = localNotifications.map(notification => {
      const duration = notification.duration || 6000
      if (duration > 0) {
        return setTimeout(() => {
          removeNotification(notification.id)
        }, duration)
      }
      return null
    })

    return () => {
      timers.forEach(timer => timer && clearTimeout(timer))
    }
  }, [localNotifications, removeNotification])

  const handleClose = useCallback((id) => {
    removeNotification(id)
  }, [removeNotification])

  return (
    <>
      {children}
      <NotificationStack
        notifications={localNotifications}
        onClose={handleClose}
      />
    </>
  )
}

/**
 * Notification context for imperative notifications
 */
const NotificationContext = createContext(null)

export function useNotification() {
  const context = useContext(NotificationContext)
  const { addNotification } = useStore()

  return {
    success: (message, title) => addNotification({ type: 'success', message, title }),
    error: (message, title) => addNotification({ type: 'error', message, title }),
    warning: (message, title) => addNotification({ type: 'warning', message, title }),
    info: (message, title) => addNotification({ type: 'info', message, title }),
  }
}

export default NotificationProvider
