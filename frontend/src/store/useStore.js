import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Connection status
  connectionStatus: 'disconnected', // 'connected', 'connecting', 'disconnected'
  setConnectionStatus: (status) => set({ connectionStatus: status }),

  // Devices
  devices: [],
  selectedDevice: null,
  setDevices: (devices) => set({ devices }),
  setSelectedDevice: (device) => set({ selectedDevice: device }),
  addDevice: (device) => set((state) => ({ devices: [...state.devices, device] })),
  updateDevice: (id, updates) => set((state) => ({
    devices: state.devices.map((d) => (d.id === id ? { ...d, ...updates } : d)),
  })),
  removeDevice: (id) => set((state) => ({
    devices: state.devices.filter((d) => d.id !== id),
  })),

  // Surveys
  surveys: [],
  activeSurvey: null,
  surveyProgress: null,
  setSurveys: (surveys) => set({ surveys }),
  setActiveSurvey: (survey) => set({ activeSurvey: survey }),
  setSurveyProgress: (progress) => set({ surveyProgress: progress }),
  addSurvey: (survey) => set((state) => ({ surveys: [...state.surveys, survey] })),
  updateSurvey: (id, updates) => set((state) => ({
    surveys: state.surveys.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    activeSurvey: state.activeSurvey?.id === id ? { ...state.activeSurvey, ...updates } : state.activeSurvey,
  })),
  removeSurvey: (id) => set((state) => ({
    surveys: state.surveys.filter((s) => s.id !== id),
    activeSurvey: state.activeSurvey?.id === id ? null : state.activeSurvey,
  })),

  // Spectrum data
  spectrumData: null,
  spectrumHistory: [],
  setSpectrumData: (data) => set((state) => {
    const history = [...state.spectrumHistory, data].slice(-100) // Keep last 100 for waterfall
    return { spectrumData: data, spectrumHistory: history }
  }),
  clearSpectrumHistory: () => set({ spectrumHistory: [] }),

  // Spectrum settings
  spectrumSettings: {
    centerFrequency: 100e6,
    bandwidth: 2.4e6,
    rbw: 100000,          // Resolution bandwidth
    gain: 30,             // Device gain in dB
    referenceLevel: -20,  // Top of display range
    noiseFloor: -120,     // Bottom of display range
    averaging: 1,         // Number of averages
    peakHold: false,      // Enable peak hold
    autoScale: true,      // Auto scale Y axis
    isStreaming: false,
    updateInterval: 0.5,
  },
  setSpectrumSettings: (settings) => set((state) => ({
    spectrumSettings: { ...state.spectrumSettings, ...settings },
  })),

  // Measurements
  measurements: [],
  measurementFilters: {
    surveyId: null,
    startFrequency: null,
    endFrequency: null,
    startTime: null,
    endTime: null,
  },
  setMeasurements: (measurements) => set({ measurements }),
  setMeasurementFilters: (filters) => set((state) => ({
    measurementFilters: { ...state.measurementFilters, ...filters },
  })),

  // Signals of interest
  signals: [],
  setSignals: (signals) => set({ signals }),
  addSignal: (signal) => set((state) => ({ signals: [...state.signals, signal] })),

  // Export jobs
  exportJobs: [],
  setExportJobs: (jobs) => set({ exportJobs: jobs }),
  addExportJob: (job) => set((state) => ({ exportJobs: [...state.exportJobs, job] })),
  updateExportJob: (id, updates) => set((state) => ({
    exportJobs: state.exportJobs.map((j) => (j.id === id ? { ...j, ...updates } : j)),
  })),

  // UI state
  notifications: [],
  addNotification: (notification) => set((state) => ({
    notifications: [...state.notifications, { id: Date.now(), ...notification }],
  })),
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter((n) => n.id !== id),
  })),

  // Loading states
  loading: {
    devices: false,
    surveys: false,
    measurements: false,
    exports: false,
  },
  setLoading: (key, value) => set((state) => ({
    loading: { ...state.loading, [key]: value },
  })),
}))
