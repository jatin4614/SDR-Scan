import { useState, useEffect, useCallback, useRef } from 'react'
import { wsService } from '../services/websocket'
import { useStore } from '../store/useStore'

/**
 * React hook for WebSocket connections
 *
 * @param {string} path - WebSocket endpoint path (e.g., '/ws/spectrum')
 * @param {object} options - Options
 * @param {boolean} options.autoConnect - Connect automatically on mount (default: true)
 * @param {function} options.onMessage - Custom message handler
 */
export function useWebSocket(path, options = {}) {
  const { autoConnect = true, onMessage } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const [error, setError] = useState(null)

  const { setConnectionStatus, setSpectrumData, setSurveyProgress } = useStore()

  const messageHandlerRef = useRef(onMessage)
  messageHandlerRef.current = onMessage

  // Handle incoming messages
  const handleMessage = useCallback((data) => {
    setLastMessage(data)

    // Call custom handler if provided
    if (messageHandlerRef.current) {
      messageHandlerRef.current(data)
    }

    // Handle different message types
    switch (data.type) {
      case 'spectrum':
        setSpectrumData(data)
        break

      case 'progress':
        setSurveyProgress(data)
        break

      case 'error':
        setError(data.message)
        console.error('WebSocket error:', data.message)
        break

      case 'status':
        console.debug('WebSocket status:', data.status)
        break

      default:
        // Unknown message type
        break
    }
  }, [setSpectrumData, setSurveyProgress])

  // Handle status changes
  const handleStatusChange = useCallback((status) => {
    setIsConnected(status === 'connected')
    setConnectionStatus(status)

    if (status === 'error') {
      setError('WebSocket connection error')
    } else {
      setError(null)
    }
  }, [setConnectionStatus])

  // Connect to WebSocket
  const connect = useCallback(() => {
    wsService.connect(path, handleMessage, handleStatusChange)
  }, [path, handleMessage, handleStatusChange])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    wsService.disconnect(path)
  }, [path])

  // Send message
  const sendMessage = useCallback((message) => {
    return wsService.send(path, message)
  }, [path])

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    isConnected,
    lastMessage,
    error,
    connect,
    disconnect,
    sendMessage,
  }
}

/**
 * Hook for spectrum WebSocket
 *
 * @param {number|null} deviceId - DB device ID to stream from
 * @param {object} options - Additional options
 */
export function useSpectrumWebSocket(deviceId, options = {}) {
  const path = deviceId
    ? `/ws/spectrum?device_id=${deviceId}`
    : '/ws/spectrum'
  return useWebSocket(path, { ...options, autoConnect: !!deviceId })
}

/**
 * Hook for survey progress WebSocket
 */
export function useSurveyWebSocket(surveyId, options = {}) {
  return useWebSocket(`/ws/survey/${surveyId}`, {
    autoConnect: !!surveyId,
    ...options,
  })
}

/**
 * Hook for signals WebSocket
 */
export function useSignalsWebSocket(options = {}) {
  return useWebSocket('/ws/signals', options)
}

export default useWebSocket
