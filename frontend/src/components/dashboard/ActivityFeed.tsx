import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  UserPlusIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { useWebSocketStore } from '../../stores/websocketStore'
import { clsx } from 'clsx'

interface ActivityItem {
  id: string
  type: 'job_completed' | 'job_failed' | 'user_added' | 'tweet_collected' | 'system_info'
  message: string
  timestamp: string
  details?: Record<string, unknown>
}

const iconMap = {
  job_completed: CheckCircleIcon,
  job_failed: ExclamationTriangleIcon,
  user_added: UserPlusIcon,
  tweet_collected: ChatBubbleLeftRightIcon,
  system_info: InformationCircleIcon,
}

const colorMap = {
  job_completed: 'text-green-500',
  job_failed: 'text-red-500',
  user_added: 'text-blue-500',
  tweet_collected: 'text-purple-500',
  system_info: 'text-gray-500',
}

export const ActivityFeed = () => {
  const [realtimeActivities, setRealtimeActivities] = useState<ActivityItem[]>([])
  const { ws, connected } = useWebSocketStore()

  const { data: activities = [], isLoading } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: async (): Promise<ActivityItem[]> => {
      const response = await fetch('http://localhost:8000/api/activities')
      if (!response.ok) {
        throw new Error('アクティビティの取得に失敗しました')
      }
      return response.json()
    },
    staleTime: 1000 * 60, // 1分
    refetchOnWindowFocus: false,
  })

  // WebSocketメッセージ処理
  useEffect(() => {
    if (!ws || !connected) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)

        if (
          message.type === 'log' ||
          message.type === 'job_update' ||
          message.type === 'system_stats'
        ) {
          // ログや更新情報をアクティビティフィードに変換
          const newActivity: ActivityItem = {
            id: `${Date.now()}-${Math.random()}`,
            type: getActivityType(message),
            message: formatActivityMessage(message),
            timestamp: message.data.timestamp || new Date().toISOString(),
            details: message.data,
          }

          setRealtimeActivities(prev => [newActivity, ...prev.slice(0, 19)]) // 最新20件まで保持
        }
      } catch (error) {
        console.error('WebSocketメッセージの処理に失敗:', error)
      }
    }

    ws.addEventListener('message', handleMessage)
    return () => {
      ws.removeEventListener('message', handleMessage)
    }
  }, [ws, connected])

  // アクティビティタイプの判定
  const getActivityType = (message: Record<string, unknown>): ActivityItem['type'] => {
    switch (message.type) {
      case 'job_update':
        if (message.data?.status === 'completed') return 'job_completed'
        if (message.data?.status === 'failed') return 'job_failed'
        return 'system_info'
      case 'log':
        if (message.data?.level === 'error') return 'job_failed'
        if (message.data?.message?.includes('ユーザー')) return 'user_added'
        if (message.data?.message?.includes('ツイート')) return 'tweet_collected'
        return 'system_info'
      default:
        return 'system_info'
    }
  }

  // アクティビティメッセージのフォーマット
  const formatActivityMessage = (message: Record<string, unknown>): string => {
    switch (message.type) {
      case 'job_update':
        return `ジョブ「${message.data?.job_id || 'unknown'}」が${message.data?.status || 'unknown'}になりました`
      case 'log':
        return message.data?.message || 'ログメッセージ'
      case 'system_stats':
        return 'システム統計が更新されました'
      default:
        return 'システムイベントが発生しました'
    }
  }

  // リアルタイムアクティビティと通常のアクティビティをマージ
  const allActivities = [...realtimeActivities, ...activities]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10) // 最新10件まで表示

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner text="アクティビティ読み込み中..." />
      </div>
    )
  }

  if (allActivities.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        {connected ? (
          <div>
            <div className="mb-2">リアルタイム接続中...</div>
            <div className="text-xs">最近のアクティビティはありません</div>
          </div>
        ) : (
          <div>最近のアクティビティはありません</div>
        )}
      </div>
    )
  }

  return (
    <div className="flow-root">
      {/* リアルタイム接続状態 */}
      {connected && realtimeActivities.length > 0 && (
        <div className="mb-3 px-2 py-1 bg-green-50 rounded text-xs text-green-600 flex items-center">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2 animate-pulse" />
          リアルタイム更新
        </div>
      )}

      <ul className="-mb-8">
        {allActivities.map((activity, index) => {
          const Icon = iconMap[activity.type]
          const isLast = index === allActivities.length - 1
          const isRealtime = realtimeActivities.some(ra => ra.id === activity.id)

          return (
            <li key={activity.id}>
              <div className="relative pb-8">
                {!isLast && (
                  <span
                    className="absolute left-5 top-5 -ml-px h-full w-0.5 bg-gray-200"
                    aria-hidden="true"
                  />
                )}
                <div className="relative flex items-start space-x-3">
                  <div className="relative">
                    <div
                      className={clsx(
                        'flex h-10 w-10 items-center justify-center rounded-full',
                        isRealtime ? 'bg-green-100 ring-2 ring-green-200' : 'bg-gray-100'
                      )}
                    >
                      <Icon className={clsx('h-5 w-5', colorMap[activity.type])} />
                    </div>
                    {isRealtime && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div>
                      <div className="text-sm text-gray-900">{activity.message}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {format(new Date(activity.timestamp), 'MM/dd HH:mm', { locale: ja })}
                      </div>
                    </div>
                    {activity.details && (
                      <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                        {typeof activity.details === 'string'
                          ? activity.details
                          : JSON.stringify(activity.details, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
