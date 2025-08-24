import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface WebSocketState {
  ws: WebSocket | null
  connected: boolean
  reconnectAttempts: number
  lastError: string | null

  connect: (url: string) => void
  disconnect: () => void
  send: (data: Record<string, unknown>) => void
  setConnected: (connected: boolean) => void
  setError: (error: string | null) => void
  incrementReconnectAttempts: () => void
  resetReconnectAttempts: () => void
}

export const useWebSocketStore = create<WebSocketState>()(
  devtools(
    (set, get) => ({
      ws: null,
      connected: false,
      reconnectAttempts: 0,
      lastError: null,

      connect: url => {
        const { ws: currentWs } = get()

        if (currentWs) {
          currentWs.close()
        }

        try {
          const ws = new WebSocket(url)

          ws.onopen = () => {
            set({ connected: true, lastError: null })
            get().resetReconnectAttempts()
          }

          ws.onclose = () => {
            set({ connected: false })

            // Auto-reconnect with exponential backoff
            const { reconnectAttempts } = get()
            if (reconnectAttempts < 5) {
              const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
              get().incrementReconnectAttempts()

              setTimeout(() => {
                get().connect(url)
              }, delay)
            }
          }

          ws.onerror = error => {
            console.error('WebSocket error:', error)
            set({ lastError: 'WebSocket接続エラーが発生しました' })
          }

          set({ ws })
        } catch (error) {
          console.error('Failed to create WebSocket:', error)
          set({ lastError: 'WebSocket接続の作成に失敗しました' })
        }
      },

      disconnect: () => {
        const { ws } = get()
        if (ws) {
          ws.close()
          set({ ws: null, connected: false })
        }
      },

      send: data => {
        const { ws, connected } = get()
        if (ws && connected) {
          ws.send(JSON.stringify(data))
        } else {
          console.warn('WebSocket is not connected')
        }
      },

      setConnected: connected => set({ connected }),
      setError: error => set({ lastError: error }),
      incrementReconnectAttempts: () =>
        set(state => ({ reconnectAttempts: state.reconnectAttempts + 1 })),
      resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),
    }),
    {
      name: 'websocket-store',
    }
  )
)
