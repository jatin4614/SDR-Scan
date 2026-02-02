import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import DeviceConfig from './components/DeviceConfig'
import SurveyManager from './components/SurveyManager'
import SpectrumViewer from './components/SpectrumViewer'
import MapViewer from './components/MapViewer'
import ExportManager from './components/ExportManager'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />}>
        <Route index element={<Navigate to="/spectrum" replace />} />
        <Route path="spectrum" element={<SpectrumViewer />} />
        <Route path="surveys" element={<SurveyManager />} />
        <Route path="devices" element={<DeviceConfig />} />
        <Route path="map" element={<MapViewer />} />
        <Route path="export" element={<ExportManager />} />
      </Route>
    </Routes>
  )
}

export default App
