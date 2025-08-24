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
  const { data: activities = [], isLoading } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: async (): Promise<ActivityItem[]> => {
      const response = await fetch('http://localhost:8000/api/activities')
      if (!response.ok) {
        throw new Error('アクティビティの取得に失敗しました')
      }
      return response.json()
    },
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  })

  const allActivities = activities
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner text="アクティビティ読み込み中..." />
      </div>
    )
  }

  if (allActivities.length === 0) {
    return <div className="text-center py-8 text-gray-500">最近のアクティビティはありません</div>
  }

  return (
    <div className="flow-root" data-testid="activity-feed">
      <ul className="-mb-8">
        {allActivities.map((activity, index) => {
          const Icon = iconMap[activity.type]
          const isLast = index === allActivities.length - 1
          const isRealtime = false

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
