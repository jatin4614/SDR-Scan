import { Component } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Collapse,
  IconButton,
} from '@mui/material'
import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  BugReport as BugIcon,
} from '@mui/icons-material'

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    }
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo)

    // Update state with error details
    this.setState({ errorInfo })

    // You could also log to an error reporting service here
    // logErrorToService(error, errorInfo)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    })

    // Call optional onReset prop
    this.props.onReset?.()
  }

  handleReload = () => {
    window.location.reload()
  }

  toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }))
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: this.props.fullPage ? '100vh' : 300,
            p: 3,
          }}
        >
          <Paper
            sx={{
              p: 4,
              maxWidth: 600,
              width: '100%',
              textAlign: 'center',
            }}
          >
            <ErrorIcon
              sx={{ fontSize: 64, color: 'error.main', mb: 2 }}
            />

            <Typography variant="h5" gutterBottom>
              Something went wrong
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {this.props.message || 'An unexpected error occurred. Please try again or reload the page.'}
            </Typography>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mb: 3 }}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={this.handleReset}
              >
                Try Again
              </Button>
              <Button
                variant="outlined"
                onClick={this.handleReload}
              >
                Reload Page
              </Button>
            </Box>

            {/* Error Details (collapsible) */}
            {this.state.error && (
              <>
                <Button
                  size="small"
                  color="inherit"
                  onClick={this.toggleDetails}
                  endIcon={this.state.showDetails ? <CollapseIcon /> : <ExpandIcon />}
                  sx={{ mb: 1 }}
                >
                  {this.state.showDetails ? 'Hide' : 'Show'} Error Details
                </Button>

                <Collapse in={this.state.showDetails}>
                  <Alert
                    severity="error"
                    icon={<BugIcon />}
                    sx={{
                      textAlign: 'left',
                      '& .MuiAlert-message': { width: '100%' },
                    }}
                  >
                    <AlertTitle>Error Details</AlertTitle>
                    <Typography
                      variant="body2"
                      component="pre"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontFamily: 'monospace',
                        fontSize: 12,
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {this.state.error.toString()}
                      {this.state.errorInfo?.componentStack && (
                        <>
                          {'\n\nComponent Stack:'}
                          {this.state.errorInfo.componentStack}
                        </>
                      )}
                    </Typography>
                  </Alert>
                </Collapse>
              </>
            )}
          </Paper>
        </Box>
      )
    }

    return this.props.children
  }
}

/**
 * withErrorBoundary HOC
 *
 * Wraps a component with an error boundary
 */
export function withErrorBoundary(WrappedComponent, errorBoundaryProps = {}) {
  return function WithErrorBoundary(props) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    )
  }
}

export default ErrorBoundary
