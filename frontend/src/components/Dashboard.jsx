import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Chip,
  Tooltip,
} from '@mui/material'
import {
  Menu as MenuIcon,
  ShowChart as SpectrumIcon,
  Assignment as SurveyIcon,
  Router as DeviceIcon,
  Map as MapIcon,
  FileDownload as ExportIcon,
  Settings as SettingsIcon,
  Circle as StatusIcon,
} from '@mui/icons-material'
import { useStore } from '../store/useStore'

const drawerWidth = 240

const navItems = [
  { path: '/spectrum', label: 'Live Spectrum', icon: <SpectrumIcon /> },
  { path: '/surveys', label: 'Surveys', icon: <SurveyIcon /> },
  { path: '/devices', label: 'Devices', icon: <DeviceIcon /> },
  { path: '/map', label: 'Map View', icon: <MapIcon /> },
  { path: '/export', label: 'Export', icon: <ExportIcon /> },
]

function Dashboard() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const { connectionStatus, activeSurvey } = useStore()

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'success'
      case 'connecting':
        return 'warning'
      case 'disconnected':
        return 'error'
      default:
        return 'default'
    }
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
          RF Monitor
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {navItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => {
                navigate(item.path)
                setMobileOpen(false)
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? 'primary.main' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
          System Status
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <StatusIcon
            sx={{
              fontSize: 12,
              color: getStatusColor() === 'success' ? 'success.main' :
                     getStatusColor() === 'warning' ? 'warning.main' : 'error.main'
            }}
          />
          <Typography variant="body2">
            {connectionStatus === 'connected' ? 'Connected' :
             connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </Typography>
        </Box>
        {activeSurvey && (
          <Chip
            size="small"
            color="primary"
            label={`Survey: ${activeSurvey.name}`}
            sx={{ mt: 1 }}
          />
        )}
      </Box>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {navItems.find(item => item.path === location.pathname)?.label || 'RF Spectrum Monitor'}
          </Typography>
          <Tooltip title="Settings">
            <IconButton color="inherit">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: 'background.default',
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}

export default Dashboard
