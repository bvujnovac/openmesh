import { useEffect, useRef, useState, useCallback } from 'react'

/**
 * Custom hook for WebSocket connection with automatic reconnection.
 *
 * @param {string} url - WebSocket URL (without ws:// prefix)
 * @param {Object} options - Configuration options
 * @param {Function} options.onMessage - Message handler callback
 * @param {Function} options.onConnect - Connection established callback
 * @param {Function} options.onDisconnect - Disconnection callback
 * @param {Function} options.onError - Error callback
 * @param {boolean} options.autoReconnect - Enable automatic reconnection (default: true)
 * @param {number} options.reconnectDelay - Delay between reconnection attempts in ms (default: 3000)
 * @param {number} options.maxReconnectAttempts - Maximum reconnection attempts (default: 10)
 * @returns {Object} WebSocket connection state and methods
 */
export function useWebSocket(url, options = {}) {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState(null)
  const wsRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef(null)
  const pingIntervalRef = useRef(null)

  // Determine WebSocket URL (handle relative paths)
  const getWebSocketUrl = useCallback(() => {
    const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws'
    const wsHost = baseUrl.replace(/^https?:\/\//, '')
    return `${wsProtocol}://${wsHost}${url}`
  }, [url])

  // Send a message through WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    console.warn('WebSocket is not connected. Cannot send message:', message)
    return false
  }, [])

  // Subscribe to a topic
  const subscribe = useCallback(
    (type, id = null) => {
      const message = { action: 'subscribe', type }
      if (id !== null) {
        message.id = id
      }
      return sendMessage(message)
    },
    [sendMessage]
  )

  // Unsubscribe from a topic
  const unsubscribe = useCallback(
    (type, id = null) => {
      const message = { action: 'unsubscribe', type }
      if (id !== null) {
        message.id = id
      }
      return sendMessage(message)
    },
    [sendMessage]
  )

  // Send ping to keep connection alive
  const sendPing = useCallback(() => {
    sendMessage({ action: 'ping' })
  }, [sendMessage])

  // Connect to WebSocket
  const connect = useCallback(() => {
    try {
      const wsUrl = getWebSocketUrl()
      console.log('Connecting to WebSocket:', wsUrl)

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionError(null)
        reconnectAttemptsRef.current = 0

        // Start ping interval (every 30 seconds)
        pingIntervalRef.current = setInterval(sendPing, 30000)

        if (onConnect) {
          onConnect()
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)

          if (onMessage) {
            onMessage(data)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionError(error)

        if (onError) {
          onError(error)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setIsConnected(false)

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        if (onDisconnect) {
          onDisconnect(event)
        }

        // Attempt reconnection if enabled
        if (
          autoReconnect &&
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          !event.wasClean
        ) {
          reconnectAttemptsRef.current += 1
          console.log(
            `Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          )

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
      setConnectionError(error)
    }
  }, [
    getWebSocketUrl,
    autoReconnect,
    maxReconnectAttempts,
    reconnectDelay,
    onConnect,
    onMessage,
    onError,
    onDisconnect,
    sendPing,
  ])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Clear ping interval
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }

    setIsConnected(false)
  }, [])

  // Connect on mount
  useEffect(() => {
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, []) // Only run on mount/unmount

  return {
    isConnected,
    connectionError,
    sendMessage,
    subscribe,
    unsubscribe,
    connect,
    disconnect,
  }
}
