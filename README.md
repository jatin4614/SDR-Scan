# RF Spectrum Monitor

A full-stack RF spectrum monitoring and survey management system built for software-defined radio (SDR) hardware. Capture, visualize, and analyze radio frequency spectrum data in real time using HackRF One, RTL-SDR, or simulated devices.

## Features

### Real-Time Spectrum Analysis
- Live spectrum display with configurable center frequency, bandwidth, and update rate
- Peak detection with automatic signal identification
- Peak hold overlay for tracking maximum signal levels over time
- Waterfall plot (spectrogram) for visualizing signal activity over time
- Noise floor estimation and SNR calculation
- Signal annotations for marking and labeling frequencies of interest

### Multi-Device Support
- **HackRF One** — 1 MHz to 6 GHz, up to 20 Msps
- **RTL-SDR** — 24 MHz to 1766 MHz, up to 3.2 Msps
- **Mock devices** — Simulated scenarios (FM broadcast, ISM 433 MHz, LTE cellular, WiFi 2.4 GHz) for testing without hardware
- Simultaneous management of multiple devices with reference-counted sharing
- Auto-detection of connected SDR hardware
- Per-device configuration (sample rate, gain, calibration offset)

### Survey Management
- Create spectrum surveys across defined frequency ranges
- Multiple survey types with configurable step size, bandwidth, and integration time
- Real-time progress tracking via WebSocket
- Pause, resume, and stop surveys mid-execution
- Background task execution with Celery worker support

### GPS & Location
- **Manual mode** — Enter coordinates directly
- **GPSD mode** — Live GPS via gpsd daemon
- **Mock mode** — Simulated GPS for testing
- Geo-tagged measurements for spatial analysis

### Data Export
- **CSV** — Tabular measurement data export
- **GeoPackage** — OGC-standard geospatial format with full geometry support
- Background export jobs with progress tracking
- Configurable export parameters (frequency range, time window, survey filter)

### Map Visualization
- Interactive map powered by Leaflet with OpenStreetMap tiles
- Heatmap overlay for signal strength visualization
- Marker clustering for dense measurement datasets
- Click-to-inspect measurements at specific locations

### API & WebSocket
- RESTful API with auto-generated OpenAPI/Swagger documentation
- WebSocket channels for real-time streaming:
  - `/ws/spectrum` — Live spectrum data from any device
  - `/ws/survey/{id}` — Survey progress updates
  - `/ws/signals` — Signal detection notifications
- Request timing headers and structured error responses

## Tech Stack

### Backend
- **Python 3.11** with **FastAPI** and **Uvicorn**
- **SQLAlchemy 2.0** ORM with **Alembic** migrations
- **SQLite** database (file-based, zero configuration)
- **NumPy** / **SciPy** for DSP and signal processing
- **GeoPandas** / **Fiona** / **Shapely** for geospatial export
- **Celery** + **Redis** for background task processing
- **Loguru** for structured logging
- **Pydantic v2** for configuration and validation

### Frontend
- **React 18** with **Vite** build tooling
- **Material UI (MUI) v5** component library
- **Plotly.js** for interactive spectrum and waterfall plots
- **Leaflet** + **React-Leaflet** for map visualization
- **Zustand** for lightweight state management
- **Axios** for HTTP client
- **PWA** support via Workbox

### Infrastructure
- **Docker** / **Docker Compose** for containerized deployment
- **Nginx** reverse proxy with WebSocket support, gzip compression, and security headers
- Health checks on all services

## Project Structure

```
SDR-Scan/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app with lifespan management
│   │   ├── models.py            # Pydantic request/response models
│   │   ├── dependencies.py      # Dependency injection
│   │   └── routes/
│   │       ├── devices.py       # Device CRUD & detection
│   │       ├── surveys.py       # Survey management
│   │       ├── spectrum.py      # Measurement queries & on-demand scans
│   │       ├── export.py        # CSV & GeoPackage export
│   │       └── websocket.py     # Real-time WebSocket endpoints
│   ├── core/
│   │   ├── config.py            # Pydantic Settings configuration
│   │   ├── survey_manager.py    # Survey execution engine
│   │   └── task_queue.py        # Background task management
│   ├── sdr/
│   │   ├── base.py              # SDRDevice abstract base class
│   │   ├── scanner.py           # SpectrumScanner (sweep, FFT, peak detection)
│   │   ├── registry.py          # DeviceRegistry (multi-device management)
│   │   ├── mock.py              # Simulated SDR with realistic scenarios
│   │   ├── rtlsdr.py            # RTL-SDR driver
│   │   └── hackrf.py            # HackRF driver
│   ├── storage/
│   │   ├── database.py          # SQLAlchemy models & engine
│   │   └── repositories.py      # Data access layer
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router & layout
│   │   ├── components/
│   │   │   ├── SpectrumViewer.jsx    # Main spectrum display
│   │   │   ├── WaterfallPlot.jsx     # Spectrogram view
│   │   │   ├── SpectrumControls.jsx  # Frequency/gain controls
│   │   │   ├── SignalAnnotation.jsx  # Frequency annotations
│   │   │   ├── MeasurementHistory.jsx
│   │   │   ├── SurveyManager.jsx
│   │   │   ├── DeviceConfig.jsx
│   │   │   ├── MapViewer.jsx
│   │   │   ├── ExportManager.jsx
│   │   │   └── analysis/
│   │   │       ├── BandStatistics.jsx
│   │   │       └── TimeSeriesView.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js  # WebSocket hooks with auto-reconnect
│   │   ├── store/
│   │   │   └── useStore.js      # Zustand state management
│   │   └── services/
│   │       └── api.js           # Axios API client
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── setup_dev.sh             # Development environment setup
│   ├── run_server.sh            # Start backend server
│   └── run_frontend.sh          # Start frontend dev server
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Database Schema

| Table | Description |
|-------|-------------|
| `devices` | SDR device configuration (type, serial, sample rate, gain, calibration) |
| `surveys` | Survey metadata (frequency range, step size, status, progress) |
| `locations` | GPS locations tied to surveys |
| `measurements` | Individual spectrum measurements (frequency, power, SNR, coordinates) |
| `signals_of_interest` | Detected or user-tagged signals with statistics |
| `export_jobs` | Background export job tracking |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/devices` | List configured devices |
| `GET` | `/api/devices/detect` | Auto-detect connected SDR hardware |
| `POST` | `/api/devices` | Register a new device |
| `POST` | `/api/devices/{id}/test` | Test device connectivity |
| `GET` | `/api/devices/registry/status` | Open device registry status |
| `GET` | `/api/surveys` | List surveys |
| `POST` | `/api/surveys` | Create a new survey |
| `POST` | `/api/surveys/{id}/start` | Start survey execution |
| `POST` | `/api/surveys/{id}/stop` | Stop a running survey |
| `GET` | `/api/spectrum/measurements` | Query stored measurements |
| `POST` | `/api/spectrum/scan` | Perform an on-demand scan |
| `POST` | `/api/export` | Start a data export job |
| `GET` | `/api/export/{id}/download` | Download exported file |
| `WS` | `/ws/spectrum` | Live spectrum streaming |
| `WS` | `/ws/survey/{id}` | Survey progress updates |
| `WS` | `/ws/signals` | Signal detection notifications |

Full interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the backend is running.

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd SDR-Scan

# Run with Docker (recommended)
docker-compose up

# Or run locally (see INSTALLATION.md for full guide)
./scripts/setup_dev.sh
./scripts/run_server.sh    # Terminal 1
./scripts/run_frontend.sh  # Terminal 2
```

- Frontend: http://localhost:5173 (dev) or http://localhost (Docker)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions covering all deployment scenarios.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/database/spectrum.db` | Database connection string |
| `API_HOST` | `0.0.0.0` | Backend listen address |
| `API_PORT` | `8000` | Backend listen port |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `GPS_MODE` | `manual` | GPS mode: `manual`, `gpsd`, `mock` |
| `GPSD_HOST` | `localhost` | GPSD daemon host |
| `GPSD_PORT` | `2947` | GPSD daemon port |
| `DEFAULT_SAMPLE_RATE` | `2400000` | Default SDR sample rate (Hz) |
| `DEFAULT_GAIN` | `20` | Default SDR gain (dB) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `EXPORT_DIRECTORY` | `./data/exports` | Export file output directory |
| `LOG_LEVEL` | `INFO` | Logging level |
