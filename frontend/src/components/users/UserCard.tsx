import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import { useUserStore } from '../../stores/userStore'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { PencilIcon, TrashIcon, PlayIcon, PauseIcon, CheckIcon } from '@heroicons/react/24/outline'
import type { TargetUserResponse } from '../../types/api'
import { clsx } from 'clsx'

interface UserCardProps {
  user: TargetUserResponse
  onEdit: () => void
  onDelete: () => void
}

export const UserCard = ({ user, onEdit, onDelete }: UserCardProps) => {
  const { selectedUsers, toggleUserSelection } = useUserStore()
  const isSelected = selectedUsers.has(user.username)

  const formatDate = (date: string | null) => {
    if (!date) return '未実行'
    return format(new Date(date), 'MM/dd HH:mm', { locale: ja })
  }

  const getPriorityBadge = (priority: number) => {
    const variants = {
      1: 'info', // 低
      2: 'default', // 標準
      3: 'warning', // 高
      4: 'error', // 緊急
    } as const

    const labels = {
      1: '低',
      2: '標準',
      3: '高',
      4: '緊急',
    } as const

    return (
      <Badge variant={variants[priority as keyof typeof variants] || 'default'}>
        {labels[priority as keyof typeof labels] || '不明'}
      </Badge>
    )
  }

  const getStatusBadge = (isActive: boolean, lastError?: string | null) => {
    if (lastError) {
      return <Badge variant="error">エラー</Badge>
    }
    return <Badge variant={isActive ? 'success' : 'default'}>{isActive ? '有効' : '無効'}</Badge>
  }

  return (
    <Card
      className={clsx(
        'relative transition-all hover:shadow-md',
        isSelected && 'ring-2 ring-blue-500'
      )}
    >
      <div className="p-4">
        {/* 選択チェックボックス */}
        <div className="absolute top-4 left-4">
          <button
            onClick={() => toggleUserSelection(user.username)}
            className={clsx(
              'w-5 h-5 border-2 rounded flex items-center justify-center transition-colors',
              isSelected
                ? 'bg-blue-500 border-blue-500 text-white'
                : 'border-gray-300 hover:border-blue-400'
            )}
          >
            {isSelected && <CheckIcon className="w-3 h-3" />}
          </button>
        </div>

        <div className="ml-8">
          {/* ユーザー名とステータス */}
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-lg text-gray-900">@{user.username}</h3>
            {getStatusBadge(user.active, user.last_error)}
          </div>

          {/* 優先度 */}
          <div className="mb-3">{getPriorityBadge(user.priority)}</div>

          {/* 統計情報 */}
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-500">収集数</span>
              <div className="font-medium">{user.total_tweets || 0}件</div>
            </div>
            <div>
              <span className="text-gray-500">最終実行</span>
              <div className="font-medium">{formatDate(user.last_scraped_at || null)}</div>
            </div>
          </div>

          {/* エラーメッセージ */}
          {user.last_error && (
            <div className="mb-4 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
              {user.last_error}
            </div>
          )}

          {/* アクション */}
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              icon={
                user.active ? <PauseIcon className="w-4 h-4" /> : <PlayIcon className="w-4 h-4" />
              }
            >
              {user.active ? '停止' : '開始'}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              icon={<PencilIcon className="w-4 h-4" />}
              onClick={onEdit}
            >
              編集
            </Button>

            <Button
              variant="ghost"
              size="sm"
              icon={<TrashIcon className="w-4 h-4" />}
              onClick={onDelete}
              className="text-red-600 hover:text-red-700"
            >
              削除
            </Button>
          </div>
        </div>
      </div>

      {/* 作成日時 */}
      <div className="px-4 pb-3 text-xs text-gray-400">
        登録:{' '}
        {user.created_at
          ? format(new Date(user.created_at), 'yyyy/MM/dd HH:mm', { locale: ja })
          : '不明'}
      </div>
    </Card>
  )
}
