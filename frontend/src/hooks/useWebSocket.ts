import { useEffect, useCallback } from 'react'
import { useWebSocketStore } from '../stores/websocketStore'
import { useAppStore } from '../stores/appStore'
import { useJobStore } from '../stores/jobStore'
import { useUserStore } from '../stores/userStore'
import { useTweetStore } from '../stores/tweetStore'

interface WebSocketMessage {
  type:
    | 'job_update'
    | 'user_update'
    | 'tweet_added'
    | 'system_stats'
    | 'notification'
    | 'log'
    | 'welcome'
    | 'pong'
    | 'error'
  data: Record<string, unknown>
}

export const useWebSocket = (url?: string) => {
  const { connect, disconnect, connected, lastError } = useWebSocketStore()
  const { addNotification } = useAppStore()
  const { updateJob, addJobLog } = useJobStore()
  const { updateUser } = useUserStore()
  const { addTweets } = useTweetStore()

  useEffect(() => {
    if (url) {
      connect(url)

      return () => {
        disconnect()
      }
    }
  }, [url, connect, disconnect])

  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      switch (message.type) {
        case 'job_update':
          updateJob((message.data.id as string) || (message.data.job_id as string), message.data)

          if (Array.isArray(message.data.logs)) {
            message.data.logs.forEach((log: Record<string, unknown>) => {
              addJobLog((message.data.id as string) || (message.data.job_id as string), log)
            })
          }
          break

        case 'user_update':
          updateUser(message.data.id as string, message.data)
          break

        case 'tweet_added':
          if (Array.isArray(message.data.tweets)) {
            addTweets(message.data.tweets)
          }
          break

        case 'system_stats':
          // システム統計は他のコンポーネントが処理
          break

        case 'notification':
          addNotification({
            type: message.data.level as 'info' | 'success' | 'warning' | 'error',
            title: message.data.title as string,
            message: message.data.message as string,
          })
          break

        case 'log':
          console.log('WebSocket log:', message.data)
          break

        case 'welcome':
          console.log('Connected to WebSocket server')
          break

        case 'pong':
          // Pong response - connection is alive
          break

        case 'error':
          addNotification({
            type: 'error',
            title: 'WebSocketエラー',
            message: message.data.message as string,
          })
          break

        default:
          console.warn('Unknown WebSocket message type:', message.type)
      }
    },
    [updateJob, addJobLog, updateUser, addTweets, addNotification]
  )

  useEffect(() => {
    const { ws } = useWebSocketStore.getState()

    if (ws) {
      ws.onmessage = event => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
    }
  }, [connected, handleMessage])

  const sendMessage = (type: string, data: Record<string, unknown>) => {
    const { send } = useWebSocketStore.getState()
    send({ type, data })
  }

  return {
    connected,
    lastError,
    sendMessage,
  }
}

export const useAutoWebSocket = () => {
  const WS_URL = 'ws://localhost:8000/ws'

  return useWebSocket(WS_URL)
}
