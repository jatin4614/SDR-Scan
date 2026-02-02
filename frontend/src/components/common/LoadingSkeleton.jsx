import {
  Box,
  Skeleton,
  Card,
  CardContent,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material'

/**
 * Generic card skeleton
 */
export function CardSkeleton({ height = 150 }) {
  return (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="60%" height={28} />
        <Skeleton variant="text" width="40%" height={20} sx={{ mb: 2 }} />
        <Skeleton variant="rectangular" height={height - 80} />
      </CardContent>
    </Card>
  )
}

/**
 * Chart/plot skeleton
 */
export function ChartSkeleton({ height = 300 }) {
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Skeleton variant="text" width={150} height={28} />
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Skeleton variant="circular" width={32} height={32} />
          <Skeleton variant="circular" width={32} height={32} />
        </Box>
      </Box>
      <Skeleton variant="rectangular" height={height} sx={{ borderRadius: 1 }} />
    </Paper>
  )
}

/**
 * Table skeleton
 */
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <Paper>
      <Table>
        <TableHead>
          <TableRow>
            {Array.from({ length: columns }).map((_, i) => (
              <TableCell key={i}>
                <Skeleton variant="text" width="80%" />
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {Array.from({ length: rows }).map((_, rowIdx) => (
            <TableRow key={rowIdx}>
              {Array.from({ length: columns }).map((_, colIdx) => (
                <TableCell key={colIdx}>
                  <Skeleton variant="text" width={`${60 + Math.random() * 30}%`} />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  )
}

/**
 * List skeleton
 */
export function ListSkeleton({ items = 5, hasAvatar = false, hasSecondary = true }) {
  return (
    <Paper sx={{ p: 1 }}>
      {Array.from({ length: items }).map((_, i) => (
        <Box
          key={i}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            p: 1.5,
            borderBottom: i < items - 1 ? 1 : 0,
            borderColor: 'divider',
          }}
        >
          {hasAvatar && (
            <Skeleton variant="circular" width={40} height={40} />
          )}
          <Box sx={{ flexGrow: 1 }}>
            <Skeleton variant="text" width={`${50 + Math.random() * 30}%`} height={24} />
            {hasSecondary && (
              <Skeleton variant="text" width={`${30 + Math.random() * 40}%`} height={18} />
            )}
          </Box>
          <Skeleton variant="circular" width={24} height={24} />
        </Box>
      ))}
    </Paper>
  )
}

/**
 * Form skeleton
 */
export function FormSkeleton({ fields = 4 }) {
  return (
    <Paper sx={{ p: 3 }}>
      <Skeleton variant="text" width={200} height={32} sx={{ mb: 3 }} />
      <Grid container spacing={2}>
        {Array.from({ length: fields }).map((_, i) => (
          <Grid item xs={12} sm={i < 2 ? 6 : 12} key={i}>
            <Skeleton variant="text" width={100} height={20} sx={{ mb: 0.5 }} />
            <Skeleton variant="rectangular" height={40} sx={{ borderRadius: 1 }} />
          </Grid>
        ))}
      </Grid>
      <Box sx={{ display: 'flex', gap: 2, mt: 3, justifyContent: 'flex-end' }}>
        <Skeleton variant="rectangular" width={80} height={36} sx={{ borderRadius: 1 }} />
        <Skeleton variant="rectangular" width={100} height={36} sx={{ borderRadius: 1 }} />
      </Box>
    </Paper>
  )
}

/**
 * Spectrum viewer skeleton
 */
export function SpectrumSkeleton() {
  return (
    <Box>
      {/* Controls bar */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" width={120} height={40} sx={{ borderRadius: 1 }} />
          ))}
        </Box>
      </Paper>

      {/* Main spectrum plot */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Skeleton variant="rectangular" height={350} sx={{ borderRadius: 1 }} />
      </Paper>

      {/* Waterfall */}
      <Paper sx={{ p: 2 }}>
        <Skeleton variant="text" width={150} height={28} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 1 }} />
      </Paper>
    </Box>
  )
}

/**
 * Map viewer skeleton
 */
export function MapSkeleton() {
  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 128px)' }}>
      {/* Sidebar */}
      <Box sx={{ width: 320, p: 2 }}>
        <Skeleton variant="text" width={150} height={28} sx={{ mb: 2 }} />
        {Array.from({ length: 4 }).map((_, i) => (
          <Box key={i} sx={{ mb: 2 }}>
            <Skeleton variant="text" width={100} height={20} sx={{ mb: 1 }} />
            <Skeleton variant="rectangular" height={40} sx={{ borderRadius: 1 }} />
          </Box>
        ))}
      </Box>

      {/* Map area */}
      <Box sx={{ flexGrow: 1, bgcolor: 'background.default', position: 'relative' }}>
        <Skeleton
          variant="rectangular"
          height="100%"
          sx={{ position: 'absolute', inset: 0 }}
        />
        {/* Legend skeleton */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 30,
            right: 10,
            width: 150,
            height: 200,
          }}
        >
          <Skeleton variant="rectangular" height="100%" sx={{ borderRadius: 1 }} />
        </Box>
      </Box>
    </Box>
  )
}

/**
 * Device config skeleton
 */
export function DeviceConfigSkeleton() {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 3 }}>
          <Skeleton variant="text" width={180} height={32} sx={{ mb: 2 }} />
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Skeleton variant="rectangular" height={56} sx={{ borderRadius: 1 }} />
            <Skeleton variant="rectangular" height={56} sx={{ borderRadius: 1 }} />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Skeleton variant="rectangular" height={36} width={100} sx={{ borderRadius: 1 }} />
              <Skeleton variant="rectangular" height={36} width={100} sx={{ borderRadius: 1 }} />
            </Box>
          </Box>
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 3 }}>
          <Skeleton variant="text" width={150} height={32} sx={{ mb: 2 }} />
          <ListSkeleton items={3} hasAvatar />
        </Paper>
      </Grid>
    </Grid>
  )
}

/**
 * Survey manager skeleton
 */
export function SurveyManagerSkeleton() {
  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Skeleton variant="text" width={200} height={32} />
          <Skeleton variant="rectangular" width={120} height={36} sx={{ borderRadius: 1 }} />
        </Box>
      </Paper>
      <Grid container spacing={2}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Grid item xs={12} sm={6} md={4} key={i}>
            <CardSkeleton height={180} />
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

/**
 * Main loading skeleton component
 * Renders appropriate skeleton based on 'type' prop
 */
function LoadingSkeleton({ type = 'card', ...props }) {
  switch (type) {
    case 'card':
      return <CardSkeleton {...props} />
    case 'chart':
      return <ChartSkeleton {...props} />
    case 'table':
      return <TableSkeleton {...props} />
    case 'list':
      return <ListSkeleton {...props} />
    case 'form':
      return <FormSkeleton {...props} />
    case 'spectrum':
      return <SpectrumSkeleton {...props} />
    case 'map':
      return <MapSkeleton {...props} />
    case 'device':
      return <DeviceConfigSkeleton {...props} />
    case 'survey':
      return <SurveyManagerSkeleton {...props} />
    default:
      return <CardSkeleton {...props} />
  }
}

export default LoadingSkeleton
