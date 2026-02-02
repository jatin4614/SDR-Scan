#!/bin/bash
# Run the RF Spectrum Monitor API server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Initialize database if it doesn't exist
if [ ! -f "data/database/spectrum.db" ]; then
    echo "Initializing database..."
    python -c "from backend.storage import init_db; init_db()"
fi

# Run the server
echo "Starting RF Spectrum Monitor API server..."
echo "API docs available at: http://localhost:8000/docs"
echo ""

uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
