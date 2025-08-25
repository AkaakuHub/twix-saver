import { useEffect, useState } from 'react'
import { apiClient } from '../../services/api'
import { ErrorModal } from './ErrorModal'

interface ConnectionState {
  isConnected: boolean
  isChecking: boolean
  error: string | null
}

export const ConnectionErrorModal = () => {
  const [connection, setConnection] = useState<ConnectionState>({
    isConnected: true,
    isChecking: false,
    error: null,
  })

  const checkConnection = async () => {
    try {
      setConnection(prev => ({ ...prev, isChecking: true, error: null }))
      await apiClient.healthCheck()
      setConnection(prev => ({ ...prev, isConnected: true, isChecking: false }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'サーバーに接続できません'
      setConnection({
        isConnected: false,
        isChecking: false,
        error: message,
      })
    }
  }

  useEffect(() => {
    // 初回チェック
    checkConnection()

    // 定期的にヘルスチェック（30秒間隔）
    const interval = setInterval(checkConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  // 接続済みの場合は何も表示しない
  if (connection.isConnected && !connection.error) {
    return null
  }

  return (
    <ErrorModal
      isOpen={!connection.isConnected}
      title="データの読み込みに失敗しました"
      message="バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。"
      onRetry={connection.isChecking ? undefined : checkConnection}
      showCloseButton={false}
    />
  )
}
