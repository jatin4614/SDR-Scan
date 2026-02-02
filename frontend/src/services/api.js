import axios from 'axios'

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// API methods
export const api = {
  // Health check
  async healthCheck() {
    const response = await apiClient.get('/health')
    return response.data
  },

  // ============ Devices ============

  async getDevices() {
    const response = await apiClient.get('/devices')
    return response.data
  },

  async getDevice(id) {
    const response = await apiClient.get(`/devices/${id}`)
    return response.data
  },

  async createDevice(device) {
    const response = await apiClient.post('/devices', device)
    return response.data
  },

  async updateDevice(id, updates) {
    const response = await apiClient.put(`/devices/${id}`, updates)
    return response.data
  },

  async deleteDevice(id) {
    const response = await apiClient.delete(`/devices/${id}`)
    return response.data
  },

  async detectDevices() {
    const response = await apiClient.get('/devices/detect')
    return response.data
  },

  async testDevice(id) {
    const response = await apiClient.post(`/devices/${id}/test`)
    return response.data
  },

  // ============ Surveys ============

  async getSurveys(params = {}) {
    const response = await apiClient.get('/surveys', { params })
    return response.data
  },

  async getSurvey(id) {
    const response = await apiClient.get(`/surveys/${id}`)
    return response.data
  },

  async createSurvey(survey) {
    const response = await apiClient.post('/surveys', survey)
    return response.data
  },

  async updateSurvey(id, updates) {
    const response = await apiClient.put(`/surveys/${id}`, updates)
    return response.data
  },

  async deleteSurvey(id) {
    const response = await apiClient.delete(`/surveys/${id}`)
    return response.data
  },

  async startSurvey(id, params = {}) {
    const response = await apiClient.post(`/surveys/${id}/start`, params)
    return response.data
  },

  async stopSurvey(id) {
    const response = await apiClient.post(`/surveys/${id}/stop`)
    return response.data
  },

  async pauseSurvey(id) {
    const response = await apiClient.post(`/surveys/${id}/pause`)
    return response.data
  },

  async resumeSurvey(id) {
    const response = await apiClient.post(`/surveys/${id}/resume`)
    return response.data
  },

  async getSurveyProgress(id) {
    const response = await apiClient.get(`/surveys/${id}/progress`)
    return response.data
  },

  async getSurveyStatistics(id) {
    const response = await apiClient.get(`/surveys/${id}/statistics`)
    return response.data
  },

  async getActiveSurveys() {
    const response = await apiClient.get('/surveys/active')
    return response.data
  },

  // Survey locations
  async getSurveyLocations(surveyId) {
    const response = await apiClient.get(`/surveys/${surveyId}/locations`)
    return response.data
  },

  async addSurveyLocation(surveyId, location) {
    const response = await apiClient.post(`/surveys/${surveyId}/locations`, location)
    return response.data
  },

  async deleteSurveyLocation(surveyId, locationId) {
    const response = await apiClient.delete(`/surveys/${surveyId}/locations/${locationId}`)
    return response.data
  },

  // ============ Spectrum / Measurements ============

  async getMeasurements(params = {}) {
    const response = await apiClient.get('/spectrum/measurements', { params })
    return response.data
  },

  async getLiveSpectrum(deviceId, params = {}) {
    const response = await apiClient.get(`/spectrum/live`, {
      params: { device_id: deviceId, ...params }
    })
    return response.data
  },

  async performScan(scanRequest) {
    const response = await apiClient.post('/spectrum/scan', scanRequest)
    return response.data
  },

  // Signals of interest
  async getSignals(surveyId = null) {
    const params = surveyId ? { survey_id: surveyId } : {}
    const response = await apiClient.get('/spectrum/signals', { params })
    return response.data
  },

  async createSignal(signal) {
    const response = await apiClient.post('/spectrum/signals', signal)
    return response.data
  },

  async updateSignal(id, updates) {
    const response = await apiClient.put(`/spectrum/signals/${id}`, updates)
    return response.data
  },

  async deleteSignal(id) {
    const response = await apiClient.delete(`/spectrum/signals/${id}`)
    return response.data
  },

  // ============ Export ============

  async exportCSV(params) {
    const response = await apiClient.post('/export/csv', params)
    return response.data
  },

  async exportGeoPackage(params) {
    const response = await apiClient.post('/export/geopackage', params)
    return response.data
  },

  async getExportJobs() {
    const response = await apiClient.get('/export/jobs')
    return response.data
  },

  async getExportJob(id) {
    const response = await apiClient.get(`/export/jobs/${id}`)
    return response.data
  },

  async downloadExport(id) {
    const response = await apiClient.get(`/export/download/${id}`, {
      responseType: 'blob'
    })
    return response.data
  },
}

export default api
