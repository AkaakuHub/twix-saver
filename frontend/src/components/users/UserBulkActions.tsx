import { useState } from 'react'
import { useUsers } from '../../hooks/useUsers'
import { useUserStore } from '../../stores/userStore'
import { Button } from '../ui/Button'
import { Modal, ModalFooter } from '../ui/Modal'
import {
  PlayIcon,
  PauseIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'

export const UserBulkActions = () => {
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [bulkAction, setBulkAction] = useState<'activate' | 'deactivate' | 'delete' | null>(null)

  const { bulkUpdate, deleteUser, isBulkUpdating, isDeleting } = useUsers()
  const { selectedUsers, clearSelection } = useUserStore()

  const selectedCount = selectedUsers.size

  const handleBulkAction = (action: 'activate' | 'deactivate' | 'delete') => {
    setBulkAction(action)
    setShowConfirmModal(true)
  }

  const executeBulkAction = async () => {
    const userIds = Array.from(selectedUsers)

    try {
      switch (bulkAction) {
        case 'activate':
          bulkUpdate({ userIds, updates: { active: true } })
          break
        case 'deactivate':
          bulkUpdate({ userIds, updates: { active: false } })
          break
        case 'delete':
          // 削除は一括APIがないので個別実行
          for (const userId of userIds) {
            deleteUser(userId)
          }
          break
      }
      clearSelection()
    } finally {
      setShowConfirmModal(false)
      setBulkAction(null)
    }
  }

  const getActionText = () => {
    switch (bulkAction) {
      case 'activate':
        return '有効化'
      case 'deactivate':
        return '無効化'
      case 'delete':
        return '削除'
      default:
        return ''
    }
  }

  const getActionColor = () => {
    switch (bulkAction) {
      case 'activate':
        return 'text-green-600'
      case 'deactivate':
        return 'text-yellow-600'
      case 'delete':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <CheckCircleIcon className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-800">
              {selectedCount}件のユーザーが選択されています
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              icon={<PlayIcon className="w-4 h-4" />}
              onClick={() => handleBulkAction('activate')}
              disabled={isBulkUpdating}
            >
              有効化
            </Button>

            <Button
              variant="outline"
              size="sm"
              icon={<PauseIcon className="w-4 h-4" />}
              onClick={() => handleBulkAction('deactivate')}
              disabled={isBulkUpdating}
            >
              無効化
            </Button>

            <Button
              variant="outline"
              size="sm"
              icon={<TrashIcon className="w-4 h-4" />}
              onClick={() => handleBulkAction('delete')}
              disabled={isDeleting}
              className="text-red-600 hover:text-red-700 border-red-300 hover:border-red-400"
            >
              削除
            </Button>

            <Button
              variant="ghost"
              size="sm"
              icon={<XCircleIcon className="w-4 h-4" />}
              onClick={clearSelection}
            >
              選択解除
            </Button>
          </div>
        </div>
      </div>

      {/* 確認モーダル */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title={`${getActionText()}の確認`}
      >
        <div className="text-center py-4">
          <div className={`text-lg font-medium mb-2 ${getActionColor()}`}>
            選択された{selectedCount}件のユーザーを{getActionText()}しますか？
          </div>

          {bulkAction === 'delete' && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg mt-4">
              この操作は取り消せません。削除されたユーザーのデータも同時に失われます。
            </div>
          )}
        </div>

        <ModalFooter>
          <Button variant="outline" onClick={() => setShowConfirmModal(false)}>
            キャンセル
          </Button>
          <Button
            variant={bulkAction === 'delete' ? 'danger' : 'primary'}
            onClick={executeBulkAction}
            loading={isBulkUpdating || isDeleting}
          >
            {getActionText()}を実行
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}
