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
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">
                バックエンドサーバーに接続できません
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                サーバーが起動していることを確認してください
                {reconnectAttempts > 0 && (
                  <span className="block text-red-600 font-medium">
                    再接続試行中: {reconnectAttempts}/5
                  </span>
                )}
              </p>
            </div>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <h4 className="text-sm font-medium text-red-800 mb-2">解決方法:</h4>
            <ul className="text-sm text-red-700 space-y-1">
              <li>• バックエンドサーバー (localhost:8000) が起動していることを確認</li>
              <li>• ネットワーク接続を確認</li>
              <li>• ファイアウォール設定を確認</li>
            </ul>
          </div>

          {reconnectAttempts >= 5 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-2 px-4 rounded-md transition-colors"
              >
                ページを再読み込み
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  return null
}