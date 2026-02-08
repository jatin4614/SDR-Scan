# Installation Guide

This guide covers every aspect of deploying the RF Spectrum Monitor on a new machine, from development setups to production Docker deployments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option A: Docker Deployment (Recommended)](#option-a-docker-deployment-recommended)
3. [Option B: Local Development Setup](#option-b-local-development-setup)
4. [SDR Hardware Setup](#sdr-hardware-setup)
5. [GPS Configuration](#gps-configuration)
6. [Database Setup](#database-setup)
7. [Background Task Queue (Celery + Redis)](#background-task-queue-celery--redis)
8. [Production Deployment](#production-deployment)
9. [Windows-Specific Notes](#windows-specific-notes)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Linux (Ubuntu 20.04+), macOS 12+, or Windows 10/11 |
| Python | 3.11 or later |
| Node.js | 20 LTS or later |
| RAM | 2 GB minimum, 4 GB recommended |
| Disk | 500 MB for application + space for measurement data |

### Optional Requirements

| Component | When Needed |
|-----------|-------------|
| Docker & Docker Compose | For containerized deployment |
| RTL-SDR hardware + drivers | For RTL-SDR device support |
| HackRF One + drivers | For HackRF device support |
| Redis | For background export jobs (Celery) |
| GPSD | For live GPS integration |

---

## Option A: Docker Deployment (Recommended)

The simplest way to get everything running. No need to install Python, Node.js, or system libraries manually.

### 1. Install Docker

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

**macOS:**
Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).

**Windows:**
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Enable WSL 2 backend when prompted.

### 2. Clone and Configure

```bash
git clone <repository-url>
cd SDR-Scan

# Create environment file
cp .env.example .env
```

Edit `.env` if you need to change defaults (see [Environment Variables](#environment-variables) below).

### 3. Build and Run

```bash
# Start all services (frontend, backend, redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:

| Service | URL |
|---------|-----|
| Frontend (Nginx) | http://localhost |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

### 4. SDR Device Access in Docker (Linux only)

For USB SDR devices to work inside Docker containers, the backend container needs USB access:

```bash
# The docker-compose.yml already includes:
#   privileged: true
#   volumes:
#     - /dev/bus/usb:/dev/bus/usb

# Ensure your SDR device is plugged in before starting containers
# Verify device visibility inside the container:
docker exec -it rf-monitor-backend lsusb
```

> **Note:** USB passthrough to Docker containers is only supported natively on Linux. On macOS and Windows, use the local development setup for hardware SDR access.

### 5. Enable Background Jobs (Optional)

To enable Celery workers for background export processing:

```bash
docker-compose --profile with-celery up -d
```

---

## Option B: Local Development Setup

### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    build-essential \
    librtlsdr-dev \
    libusb-1.0-0-dev \
    libffi-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    pkg-config
```

**macOS (Homebrew):**
```bash
brew install python@3.11 librtlsdr libusb gdal geos proj pkg-config
```

**Windows:**
- Install [Python 3.11+](https://www.python.org/downloads/) (check "Add to PATH" during install)
- Install [Node.js 20 LTS](https://nodejs.org/)
- Install [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (for compiling native extensions)
- See [Windows-Specific Notes](#windows-specific-notes) for SDR driver setup

### 2. Backend Setup

```bash
# Navigate to project root
cd SDR-Scan

# Create and activate virtual environment
python3 -m venv venv

# Linux/macOS:
source venv/bin/activate

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create Data Directories

```bash
# Linux/macOS:
mkdir -p data/database data/exports logs

# Windows (Command Prompt):
mkdir data\database data\exports logs
```

### 4. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env    # Linux/macOS
copy .env.example .env  # Windows
```

Edit `.env` to match your setup. Key settings:

```ini
# Use mock devices for testing (no hardware needed)
GPS_MODE=mock

# For development with frontend on port 5173
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Log level
LOG_LEVEL=DEBUG
```

### 5. Start the Backend

```bash
# From project root, with venv activated
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the convenience script (Linux/macOS):
./scripts/run_server.sh
```

Verify the backend is running:
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 6. Frontend Setup

Open a **new terminal**:

```bash
cd SDR-Scan/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Or use the convenience script (Linux/macOS):
cd .. && ./scripts/run_frontend.sh
```

The frontend will be available at http://localhost:5173.

### 7. Automated Setup Script (Linux/macOS)

There is a convenience script that automates steps 2-5:

```bash
./scripts/setup_dev.sh
```

This will create the virtual environment, install dependencies, check SDR library availability, create data directories, and copy `.env.example` to `.env`.

---

## SDR Hardware Setup

### RTL-SDR

**Linux:**
```bash
# Install driver library
sudo apt-get install librtlsdr-dev rtl-sdr

# Add udev rules for non-root access
sudo bash -c 'cat > /etc/udev/rules.d/20-rtlsdr.rules << EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"
EOF'
sudo udevadm control --reload-rules
sudo udevadm trigger

# Blacklist the kernel DVB-T driver (conflicts with SDR usage)
sudo bash -c 'echo "blacklist dvb_usb_rtl28xxu" > /etc/modprobe.d/blacklist-rtlsdr.conf'
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true

# Verify device is detected
rtl_test -t
```

**macOS:**
```bash
brew install librtlsdr
# Plug in device and verify
rtl_test -t
```

**Windows:**
1. Download and install [Zadig](https://zadig.akeo.ie/)
2. Plug in the RTL-SDR device
3. In Zadig: Options > List All Devices
4. Select "Bulk-In, Interface (Interface 0)" from the dropdown
5. Set the driver to "WinUSB" and click "Replace Driver"
6. The Python `pyrtlsdr` package should now detect the device

**Python package (all platforms):**
```bash
pip install pyrtlsdr
```

### HackRF One

**Linux:**
```bash
# Install HackRF tools and library
sudo apt-get install hackrf libhackrf-dev

# Add udev rules
sudo bash -c 'cat > /etc/udev/rules.d/53-hackrf.rules << EOF
ATTR{idVendor}=="1d50", ATTR{idProduct}=="604b", SYMLINK+="hackrf-jawbreaker-%k", MODE="0666", GROUP="plugdev"
ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", SYMLINK+="hackrf-one-%k", MODE="0666", GROUP="plugdev"
EOF'
sudo udevadm control --reload-rules
sudo udevadm trigger

# Verify
hackrf_info
```

**macOS:**
```bash
brew install hackrf
hackrf_info
```

**Windows:**
1. Install [Zadig](https://zadig.akeo.ie/)
2. Plug in HackRF, select it in Zadig, install WinUSB driver

**Python package (all platforms):**
```bash
pip install hackrf
```

> **Note:** The HackRF Python bindings may require building from source on some platforms. See the [HackRF documentation](https://hackrf.readthedocs.io/).

### Mock Devices (No Hardware)

Mock devices are always available and require no additional setup. They simulate four RF scenarios:

| Scenario | Description |
|----------|-------------|
| FM Broadcast | Simulated FM radio signals around 88-108 MHz |
| ISM 433 MHz | Industrial/scientific/medical band activity |
| LTE Cellular | Simulated LTE signal patterns |
| WiFi 2.4 GHz | Simulated WiFi channel activity |

Set `GPS_MODE=mock` in `.env` for a fully simulated environment.

---

## GPS Configuration

### Manual Mode (Default)

Coordinates are entered manually in the survey configuration UI. No additional setup required.

```ini
GPS_MODE=manual
```

### GPSD Mode (Live GPS)

Connects to a GPSD daemon for real-time GPS data.

**Install GPSD:**
```bash
# Ubuntu/Debian
sudo apt-get install gpsd gpsd-clients

# Start GPSD with a USB GPS receiver
sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock

# Test GPS output
cgps -s
```

**Configure:**
```ini
GPS_MODE=gpsd
GPSD_HOST=localhost
GPSD_PORT=2947
```

### Mock Mode (Testing)

Simulates GPS data at a fixed location (default: New Delhi, India — 28.6139N, 77.2090E).

```ini
GPS_MODE=mock
```

---

## Database Setup

The application uses **SQLite** by default. The database file is created automatically on first startup.

```ini
DATABASE_URL=sqlite:///./data/database/spectrum.db
```

The schema is initialized via SQLAlchemy when the backend starts. No manual migration steps are required for a fresh install.

### Database Location

| Deployment | Path |
|------------|------|
| Local development | `./data/database/spectrum.db` |
| Docker | `/app/data/database/spectrum.db` (inside `rf-data` volume) |

### Backup

```bash
# Local
cp data/database/spectrum.db data/database/spectrum.db.backup

# Docker
docker cp rf-monitor-backend:/app/data/database/spectrum.db ./spectrum.db.backup
```

### Reset Database

```bash
# Delete the database file (will be recreated on next startup)
rm data/database/spectrum.db

# Docker
docker-compose down
docker volume rm sdr-scan_rf-data
docker-compose up -d
```

---

## Background Task Queue (Celery + Redis)

Celery is used for background data export jobs. It is **optional** — exports will still work without it, but they will run synchronously.

### Install Redis

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Use Docker for Redis or install from [Redis for Windows](https://github.com/microsoftarchive/redis/releases).

### Configure Celery

```ini
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Start a Celery Worker

```bash
# From project root, with venv activated
celery -A backend.core.task_queue worker --loglevel=info
```

---

## Production Deployment

### Docker Compose (Recommended)

The included `docker-compose.yml` is production-ready with:
- Nginx serving the frontend with gzip compression and security headers
- API/WebSocket reverse proxy to the backend
- Health checks on all services
- Automatic restart on failure
- Named volumes for persistent data

```bash
# Build and start in detached mode
docker-compose up -d --build

# With background job processing
docker-compose --profile with-celery up -d --build
```

### Nginx Configuration

The frontend container includes a pre-configured Nginx that:
- Serves the React SPA with proper client-side routing (`try_files`)
- Proxies `/api/*` requests to the backend
- Proxies `/ws/*` WebSocket connections with upgrade headers
- Applies security headers (X-Frame-Options, X-Content-Type-Options, XSS-Protection)
- Enables gzip compression for text-based assets
- Caches static assets (JS, CSS, images) with 1-year expiry

### Custom Domain / HTTPS

To add HTTPS with a custom domain, place your SSL certificate and modify `frontend/nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # ... rest of config remains the same
}
```

Mount the certificates as a Docker volume:
```yaml
# docker-compose.yml
frontend:
  volumes:
    - ./ssl:/etc/nginx/ssl:ro
```

Update `CORS_ORIGINS` in your `.env` to include the new domain.

### Building Frontend for Production

If deploying without Docker:

```bash
cd frontend

# Production build
npm run build:prod

# Output is in frontend/dist/
# Serve with any static file server (nginx, caddy, etc.)
```

### Running Backend in Production

```bash
# Use multiple workers (do NOT use --reload in production)
uvicorn backend.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

---

## Windows-Specific Notes

### Python Virtual Environment

```cmd
:: Command Prompt
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

:: PowerShell (may need execution policy change)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Geospatial Libraries

Installing `geopandas`, `fiona`, and `shapely` on Windows can be challenging. If `pip install` fails:

1. Download pre-built wheels from [Christoph Gohlke's repository](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
2. Install GDAL first, then Fiona, then GeoPandas:
   ```cmd
   pip install GDAL-3.x.x-cp311-cp311-win_amd64.whl
   pip install Fiona-1.9.x-cp311-cp311-win_amd64.whl
   pip install geopandas
   ```

Alternatively, use [Conda](https://docs.conda.io/):
```cmd
conda install -c conda-forge geopandas fiona shapely pyproj
```

### Running the Backend on Windows

```cmd
:: From project root with venv activated
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### USB Device Drivers

Use [Zadig](https://zadig.akeo.ie/) to install WinUSB drivers for both RTL-SDR and HackRF devices. See the [SDR Hardware Setup](#sdr-hardware-setup) section.

---

## Environment Variables

All configuration is managed via environment variables or a `.env` file in the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/database/spectrum.db` | Database connection URL |
| `API_HOST` | `0.0.0.0` | Backend server host |
| `API_PORT` | `8000` | Backend server port |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `GPS_MODE` | `manual` | GPS mode: `manual`, `gpsd`, `mock` |
| `GPSD_HOST` | `localhost` | GPSD daemon host |
| `GPSD_PORT` | `2947` | GPSD daemon port |
| `DEFAULT_SAMPLE_RATE` | `2400000` | Default SDR sample rate in Hz |
| `DEFAULT_GAIN` | `20` | Default SDR gain in dB |
| `DEFAULT_INTEGRATION_TIME` | `0.1` | Default integration time in seconds |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery result storage |
| `EXPORT_DIRECTORY` | `./data/exports` | Export file output path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `./logs/spectrum_monitor.log` | Log file path |

---

## Troubleshooting

### Backend won't start

```
ModuleNotFoundError: No module named 'backend'
```
Make sure you're running `uvicorn` from the **project root** directory, not from inside `backend/`.

### SDR device not detected

1. Verify the device is plugged in: `lsusb` (Linux) or Device Manager (Windows)
2. Check driver installation (Zadig on Windows, udev rules on Linux)
3. Make sure no other application is using the device
4. Try `rtl_test -t` (RTL-SDR) or `hackrf_info` (HackRF) from the command line

### WebSocket connection fails

1. Check that the backend is running and accessible
2. Verify `CORS_ORIGINS` includes your frontend URL
3. In Docker: ensure the Nginx `proxy_pass` for `/ws` is configured correctly (included by default)

### Frontend shows "Disconnected"

1. Ensure a device is selected in the device dropdown
2. The WebSocket connects only when a device is selected
3. Check browser console for connection errors

### Geospatial export fails

```
ImportError: No module named 'fiona'
```
Install geospatial dependencies. On Linux: `sudo apt-get install libgdal-dev`. On Windows: see [Windows-Specific Notes](#windows-specific-notes).

### Docker: SDR device not visible

- USB passthrough only works on **Linux** Docker hosts
- Ensure `privileged: true` is set in `docker-compose.yml` for the backend service
- Plug in the device **before** starting containers
- Verify with `docker exec -it rf-monitor-backend lsusb`

### Port conflicts

If ports 80, 8000, or 6379 are already in use, edit `docker-compose.yml` or `.env`:

```yaml
# docker-compose.yml — change host port
ports:
  - "3080:80"    # Frontend on port 3080 instead of 80
  - "9000:8000"  # Backend on port 9000 instead of 8000
```

### Reset everything

```bash
# Docker
docker-compose down -v   # -v removes volumes (deletes all data)
docker-compose up -d --build

# Local
rm data/database/spectrum.db
rm -rf logs/*
# Restart backend — database will be recreated
```
