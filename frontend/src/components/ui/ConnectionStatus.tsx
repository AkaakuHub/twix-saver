import { useEffect, useState } from 'react'
import { useWebSocketStore } from '../../stores/websocketStore'
import { useAppStore } from '../../stores/appStore'

export const ConnectionStatus = () => {
  const { connected, lastError, reconnectAttempts } = useWebSocketStore()
  const { addNotification } = useAppStore()
  const [hasShownError, setHasShownError] = useState(false)

  useEffect(() => {
    if (lastError && !hasShownError) {
      addNotification({
        type: 'error',
        title: 'バックエンド接続エラー',
        message: 'バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。',
        duration: 0,
      })
      setHasShownError(true)
    }

    if (connected && hasShownError) {
      addNotification({
        type: 'success',
        title: '接続復旧',
        message: 'バックエンドサーバーに再接続しました。',
        duration: 3000,
      })
      setHasShownError(false)
    }
  }, [lastError, connected, hasShownError, addNotification])

  if (!connected && (lastError || reconnectAttempts > 0)) {
    return (
      <div className="fixed top-0 left-0 right-0 bg-red-600 text-white p-4 text-center z-50 shadow-lg">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center space-x-3">
            <div className="animate-pulse">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <div className="font-bold text-lg">
                バックエンドサーバーに接続できません
              </div>
              <div className="text-sm opacity-90">
                サーバーが起動していることを確認してください。
                {reconnectAttempts > 0 && ` (再接続試行: ${reconnectAttempts}/5)`}
              </div>
            </div>
          </div>
          
          <div className="mt-3 text-sm bg-red-700 bg-opacity-50 rounded px-3 py-2">
            <div className="font-medium">解決方法:</div>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>バックエンドサーバー (localhost:8000) が起動していることを確認</li>
              <li>ネットワーク接続を確認</li>
              <li>ファイアウォール設定を確認</li>
            </ul>
          </div>
        </div>
      </div>
    )
  }

  return null
}