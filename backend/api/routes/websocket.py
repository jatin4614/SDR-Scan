"""
WebSocket Routes

Real-time spectrum streaming and survey progress updates via WebSocket.
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from loguru import logger

from ...core import get_survey_manager, GPSMode
from ...sdr import get_scanner, ScanParameters


router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Supports multiple channels:
    - spectrum: Real-time spectrum data streaming
    - survey: Survey progress updates
    - signals: Signal detection notifications
    """

    def __init__(self):
        # Map of channel -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'spectrum': set(),
            'survey': set(),
            'signals': set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = 'spectrum'):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
        logger.debug(f"WebSocket connected to channel: {channel}")

    async def disconnect(self, websocket: WebSocket, channel: str = 'spectrum'):
        """Remove a WebSocket connection"""
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
        logger.debug(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, message: dict, channel: str = 'spectrum'):
        """Broadcast message to all connections in a channel"""
        async with self._lock:
            connections = self.active_connections.get(channel, set()).copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected websockets
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self.active_connections.get(channel, set()).discard(ws)

    async def send_to(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections"""
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    return manager


@router.websocket("/spectrum")
async def spectrum_websocket(
    websocket: WebSocket,
    device_id: Optional[int] = Query(None, description="Device ID to stream from"),
    center_freq: Optional[float] = Query(None, description="Center frequency in Hz"),
    bandwidth: Optional[float] = Query(2.4e6, description="Bandwidth in Hz"),
    interval: Optional[float] = Query(0.5, description="Update interval in seconds")
):
    """
    WebSocket endpoint for real-time spectrum streaming.

    Streams spectrum data at regular intervals for live visualization.

    Messages sent:
    - type: "spectrum" - Spectrum data with frequencies and power values
    - type: "error" - Error messages
    - type: "status" - Connection status updates

    Messages received:
    - type: "config" - Update streaming parameters
    - type: "pause" - Pause streaming
    - type: "resume" - Resume streaming
    """
    await manager.connect(websocket, 'spectrum')

    streaming = True
    current_device_id = device_id
    current_center_freq = center_freq or 100e6
    current_bandwidth = bandwidth
    current_interval = max(0.1, min(5.0, interval))  # Clamp between 0.1 and 5 seconds

    try:
        # Send initial status
        await manager.send_to(websocket, {
            'type': 'status',
            'status': 'connected',
            'config': {
                'device_id': current_device_id,
                'center_freq': current_center_freq,
                'bandwidth': current_bandwidth,
                'interval': current_interval
            }
        })

        # Get scanner
        scanner = get_scanner()

        while True:
            # Check for incoming messages (non-blocking)
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=current_interval if streaming else 1.0
                )

                msg_type = message.get('type', '')

                if msg_type == 'config':
                    # Update configuration
                    if 'center_freq' in message:
                        current_center_freq = float(message['center_freq'])
                    if 'bandwidth' in message:
                        current_bandwidth = float(message['bandwidth'])
                    if 'interval' in message:
                        current_interval = max(0.1, min(5.0, float(message['interval'])))
                    if 'device_id' in message:
                        current_device_id = message['device_id']

                    await manager.send_to(websocket, {
                        'type': 'status',
                        'status': 'config_updated',
                        'config': {
                            'device_id': current_device_id,
                            'center_freq': current_center_freq,
                            'bandwidth': current_bandwidth,
                            'interval': current_interval
                        }
                    })

                elif msg_type == 'pause':
                    streaming = False
                    await manager.send_to(websocket, {
                        'type': 'status',
                        'status': 'paused'
                    })

                elif msg_type == 'resume':
                    streaming = True
                    await manager.send_to(websocket, {
                        'type': 'status',
                        'status': 'streaming'
                    })

            except asyncio.TimeoutError:
                # No message received, continue streaming if active
                pass

            # Stream spectrum data if active
            if streaming:
                try:
                    # Get spectrum data
                    spectrum_data = await asyncio.to_thread(
                        _get_spectrum_snapshot,
                        scanner,
                        current_center_freq,
                        current_bandwidth
                    )

                    if spectrum_data:
                        await manager.send_to(websocket, {
                            'type': 'spectrum',
                            'timestamp': datetime.utcnow().isoformat(),
                            'center_freq': current_center_freq,
                            'bandwidth': current_bandwidth,
                            'frequencies': spectrum_data['frequencies'],
                            'power_dbm': spectrum_data['power_dbm'],
                            'noise_floor': spectrum_data.get('noise_floor'),
                            'peaks': spectrum_data.get('peaks', [])
                        })

                except Exception as e:
                    logger.error(f"Spectrum streaming error: {e}")
                    await manager.send_to(websocket, {
                        'type': 'error',
                        'message': str(e)
                    })

    except WebSocketDisconnect:
        logger.debug("Spectrum WebSocket disconnected")
    except Exception as e:
        logger.error(f"Spectrum WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, 'spectrum')


def _get_spectrum_snapshot(scanner, center_freq: float, bandwidth: float) -> Optional[dict]:
    """Get a single spectrum snapshot (runs in thread pool)"""
    try:
        params = ScanParameters(
            start_freq=center_freq - bandwidth / 2,
            stop_freq=center_freq + bandwidth / 2,
            step_size=bandwidth / 1024,  # 1024 points
            bandwidth=bandwidth / 10,
            integration_time=0.05
        )

        result = scanner.single_sweep(params)
        if result and result.data:
            # Convert numpy arrays to lists for JSON serialization
            return {
                'frequencies': result.data[0].frequencies.tolist(),
                'power_dbm': result.data[0].power_dbm.tolist(),
                'noise_floor': result.noise_floor_dbm,
                'peaks': [
                    {
                        'frequency': p.frequency,
                        'power_dbm': p.power_dbm,
                        'bandwidth': p.bandwidth
                    }
                    for p in (result.peaks or [])[:10]  # Limit to top 10 peaks
                ]
            }
    except Exception as e:
        logger.error(f"Error getting spectrum snapshot: {e}")
    return None


@router.websocket("/survey/{survey_id}")
async def survey_websocket(
    websocket: WebSocket,
    survey_id: int
):
    """
    WebSocket endpoint for survey progress updates.

    Streams real-time updates about survey execution including:
    - Progress percentage
    - Current frequency being scanned
    - Measurements as they're collected
    - Signal detections
    - GPS location updates

    Messages sent:
    - type: "progress" - Survey progress update
    - type: "measurement" - New measurement data
    - type: "signal" - Detected signal notification
    - type: "location" - GPS location update
    - type: "status" - Survey status change
    - type: "error" - Error messages
    """
    await manager.connect(websocket, 'survey')

    survey_manager = get_survey_manager()

    try:
        # Check if survey exists and is running
        state = survey_manager.get_state()

        if not state or state.survey_id != survey_id:
            await manager.send_to(websocket, {
                'type': 'status',
                'status': 'not_running',
                'message': f'Survey {survey_id} is not currently running'
            })
        else:
            await manager.send_to(websocket, {
                'type': 'status',
                'status': state.status.value,
                'progress': state.progress,
                'measurements_collected': state.measurements_collected,
                'current_frequency': state.current_frequency
            })

        # Listen for updates
        while True:
            try:
                # Check for control messages
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=1.0
                )

                msg_type = message.get('type', '')

                if msg_type == 'get_status':
                    state = survey_manager.get_state()
                    if state and state.survey_id == survey_id:
                        await manager.send_to(websocket, {
                            'type': 'progress',
                            'survey_id': survey_id,
                            'status': state.status.value,
                            'progress': state.progress,
                            'measurements_collected': state.measurements_collected,
                            'current_frequency': state.current_frequency,
                            'current_location': state.current_location.to_dict() if state.current_location else None,
                            'errors': state.errors
                        })
                    else:
                        await manager.send_to(websocket, {
                            'type': 'status',
                            'status': 'not_running'
                        })

                elif msg_type == 'pause':
                    if survey_manager.pause_survey():
                        await manager.send_to(websocket, {
                            'type': 'status',
                            'status': 'paused'
                        })

                elif msg_type == 'resume':
                    if survey_manager.resume_survey():
                        await manager.send_to(websocket, {
                            'type': 'status',
                            'status': 'running'
                        })

            except asyncio.TimeoutError:
                # No message, send periodic status update
                state = survey_manager.get_state()
                if state and state.survey_id == survey_id:
                    await manager.send_to(websocket, {
                        'type': 'progress',
                        'survey_id': survey_id,
                        'status': state.status.value,
                        'progress': state.progress,
                        'measurements_collected': state.measurements_collected,
                        'current_frequency': state.current_frequency
                    })

    except WebSocketDisconnect:
        logger.debug(f"Survey WebSocket disconnected for survey {survey_id}")
    except Exception as e:
        logger.error(f"Survey WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, 'survey')


@router.websocket("/signals")
async def signals_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for signal detection notifications.

    Streams notifications when new signals of interest are detected.
    Useful for real-time alerting and monitoring applications.

    Messages sent:
    - type: "signal_detected" - New signal detected
    - type: "signal_lost" - Previously detected signal no longer present
    """
    await manager.connect(websocket, 'signals')

    try:
        await manager.send_to(websocket, {
            'type': 'status',
            'status': 'connected',
            'message': 'Listening for signal detections'
        })

        while True:
            # Keep connection alive, broadcast signals from other sources
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )

                # Handle any control messages
                msg_type = message.get('type', '')
                if msg_type == 'ping':
                    await manager.send_to(websocket, {
                        'type': 'pong',
                        'timestamp': datetime.utcnow().isoformat()
                    })

            except asyncio.TimeoutError:
                # Send keepalive
                await manager.send_to(websocket, {
                    'type': 'keepalive',
                    'timestamp': datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        logger.debug("Signals WebSocket disconnected")
    except Exception as e:
        logger.error(f"Signals WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, 'signals')


async def broadcast_measurement(measurement: dict):
    """Broadcast a new measurement to survey subscribers"""
    await manager.broadcast({
        'type': 'measurement',
        'timestamp': datetime.utcnow().isoformat(),
        'data': measurement
    }, 'survey')


async def broadcast_signal_detection(signal: dict):
    """Broadcast a signal detection to subscribers"""
    await manager.broadcast({
        'type': 'signal_detected',
        'timestamp': datetime.utcnow().isoformat(),
        'signal': signal
    }, 'signals')


async def broadcast_survey_progress(survey_id: int, progress: dict):
    """Broadcast survey progress update"""
    await manager.broadcast({
        'type': 'progress',
        'survey_id': survey_id,
        **progress
    }, 'survey')
