/**
 * WebSocket Service
 *
 * Manages WebSocket connections for real-time spectrum streaming
 * and survey progress updates.
 */

class WebSocketService {
  constructor() {
    this.connections = new Map()
    this.listeners = new Map()
    this.reconnectAttempts = new Map()
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
  }

  /**
   * Get the WebSocket URL for the given path
   */
  getWebSocketUrl(path) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}${path}`
  }

  /**
   * Connect to a WebSocket endpoint
   */
  connect(path, onMessage, onStatusChange) {
    if (this.connections.has(path)) {
      console.debug(`WebSocket already connected to ${path}`)
      return this.connections.get(path)
    }

    const url = this.getWebSocketUrl(path)
    console.debug(`Connecting to WebSocket: ${url}`)

    const ws = new WebSocket(url)
    this.connections.set(path, ws)
    this.reconnectAttempts.set(path, 0)

    ws.onopen = () => {
      console.debug(`WebSocket connected: ${path}`)
      this.reconnectAttempts.set(path, 0)
      if (onStatusChange) onStatusChange('connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (onMessage) onMessage(data)

        // Notify all listeners
        const listeners = this.listeners.get(path) || []
        listeners.forEach(listener => listener(data))
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error on ${path}:`, error)
      if (onStatusChange) onStatusChange('error')
    }

    ws.onclose = (event) => {
      console.debug(`WebSocket closed: ${path}, code: ${event.code}`)
      this.connections.delete(path)

      if (onStatusChange) onStatusChange('disconnected')

      // Attempt reconnection
      const attempts = this.reconnectAttempts.get(path) || 0
      if (attempts < this.maxReconnectAttempts) {
        this.reconnectAttempts.set(path, attempts + 1)
        const delay = this.reconnectDelay * Math.pow(2, attempts)
        console.debug(`Reconnecting to ${path} in ${delay}ms (attempt ${attempts + 1})`)
        setTimeout(() => {
          this.connect(path, onMessage, onStatusChange)
        }, delay)
      } else {
        console.error(`Max reconnection attempts reached for ${path}`)
      }
    }

    return ws
  }

  /**
   * Disconnect from a WebSocket endpoint
   */
  disconnect(path) {
    const ws = this.connections.get(path)
    if (ws) {
      this.reconnectAttempts.set(path, this.maxReconnectAttempts) // Prevent reconnection
      ws.close()
      this.connections.delete(path)
      this.listeners.delete(path)
    }
  }

  /**
   * Send a message to a WebSocket endpoint
   */
  send(path, message) {
    const ws = this.connections.get(path)
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
      return true
    }
    console.warn(`Cannot send message, WebSocket not connected: ${path}`)
    return false
  }

  /**
   * Add a listener for messages on a path
   */
  addListener(path, listener) {
    if (!this.listeners.has(path)) {
      this.listeners.set(path, [])
    }
    this.listeners.get(path).push(listener)
  }

  /**
   * Remove a listener
   */
  removeListener(path, listener) {
    const listeners = this.listeners.get(path)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index !== -1) {
        listeners.splice(index, 1)
      }
    }
  }

  /**
   * Check if connected to a path
   */
  isConnected(path) {
    const ws = this.connections.get(path)
    return ws && ws.readyState === WebSocket.OPEN
  }

  /**
   * Disconnect all WebSocket connections
   */
  disconnectAll() {
    this.connections.forEach((ws, path) => {
      this.disconnect(path)
    })
  }
}

// Export singleton instance
export const wsService = new WebSocketService()

export default wsService
