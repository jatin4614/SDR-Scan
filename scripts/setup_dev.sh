#!/bin/bash
# Development Environment Setup Script
# RF Spectrum Monitor

set -e

echo "========================================"
echo "  RF Spectrum Monitor - Setup"
echo "========================================"

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "  Found: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "  Virtual environment created."
else
    echo ""
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for optional SDR libraries
echo ""
echo "Checking SDR library status..."

python3 -c "
try:
    import rtlsdr
    print('  [OK] RTL-SDR support available (pyrtlsdr)')
except ImportError:
    print('  [--] RTL-SDR support not available')
    print('       Install with: pip install pyrtlsdr')

try:
    import hackrf
    print('  [OK] HackRF support available')
except ImportError:
    print('  [--] HackRF support not available')
    print('       See: https://github.com/greatscottgadgets/hackrf')
"

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/database
mkdir -p data/exports
mkdir -p logs

# Copy example environment file if .env doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from example..."
    cp .env.example .env
fi

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run SDR tests:"
echo "  python scripts/test_sdr.py --all"
echo ""
echo "To start the backend server:"
echo "  cd backend && uvicorn api.main:app --reload"
echo ""
