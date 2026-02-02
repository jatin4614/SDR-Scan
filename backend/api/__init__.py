"""
API Module

This module provides the FastAPI application and all REST endpoints
for the RF Spectrum Monitor.

To run the API server:
    uvicorn backend.api.main:app --reload

Or use the convenience script:
    python -m backend.api.main
"""

from .main import app

__all__ = ['app']
