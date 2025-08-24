import { useState } from 'react'
import { useUsers } from '../../hooks/useUsers'
import { useUserStore } from '../../stores/userStore'
import { UserCard } from './UserCard'
import { UserForm } from './UserForm'
import { UserSearch } from './UserSearch'
import { UserBulkActions } from './UserBulkActions'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { EmptyStateWithRetry } from '../ui/EmptyStateWithRetry'
import { PlusIcon } from '@heroicons/react/24/outline'
import type { TargetUserResponse, TargetUserCreate, TargetUserUpdate } from '../../types/api'
import type { UserFormData } from './UserForm'

export const UserList = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<TargetUserResponse | null>(null)

  const { users, isLoading, error, refetch, createUser, updateUser, deleteUser } = useUsers()
  const { selectedUsers, filters } = useUserStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="ユーザー一覧を読み込み中..." />
      </div>
    )
  }

  if (error) {
    return (
      <EmptyStateWithRetry
        title="データの読み込みに失敗しました"
        message={error.message}
        onRetry={refetch}
        icon={
          <svg className="h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        }
      />
    )
  }

  const handleCreateUser = (userData: Record<string, unknown>) => {
    createUser(userData as unknown as TargetUserCreate)
    setIsCreateModalOpen(false)
  }

  const handleUpdateUser = (userData: Record<string, unknown>) => {
    if (editingUser) {
      updateUser({ id: editingUser.username, data: userData as unknown as TargetUserUpdate })
      setEditingUser(null)
    }
  }

  const handleDeleteUser = (id: string) => {
    if (window.confirm('本当に削除しますか？')) {
      deleteUser(id)
    }
  }

  const filteredUsers = (users as TargetUserResponse[]).filter((user: TargetUserResponse) => {
    // 検索フィルタ
    if (filters.search && !user.username.toLowerCase().includes(filters.search.toLowerCase())) {
      return false
    }

    // ステータスフィルタ
    if (filters.status !== 'all' && user.active !== (filters.status === 'active')) {
      return false
    }

    // 優先度フィルタ
    if (filters.priority !== 'all' && user.priority !== Number(filters.priority)) {
      return false
    }

    return true
  })

  // ソート
  const sortedUsers = [...filteredUsers].sort((a, b) => {
    const { sortBy, sortOrder } = filters
    let aValue: unknown = a[sortBy as keyof TargetUserResponse]
    let bValue: unknown = b[sortBy as keyof TargetUserResponse]

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = bValue.toLowerCase()
    }

    if ((aValue as string | number) < (bValue as string | number))
      return sortOrder === 'asc' ? -1 : 1
    if ((aValue as string | number) > (bValue as string | number))
      return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ユーザー管理</h1>
          <p className="text-gray-600">監視対象ユーザーの管理 ({(users as unknown[]).length}件)</p>
        </div>
        <Button icon={<PlusIcon className="w-4 h-4" />} onClick={() => setIsCreateModalOpen(true)}>
          新規ユーザー追加
        </Button>
      </div>

      {/* 検索・フィルタ */}
      <UserSearch />

      {/* 一括操作 */}
      {selectedUsers.size > 0 && <UserBulkActions />}

      {/* ユーザー一覧 */}
      {sortedUsers.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">
            {(users as unknown[]).length === 0
              ? '監視対象ユーザーが登録されていません'
              : '検索条件に該当するユーザーがいません'}
          </div>
          {(users as unknown[]).length === 0 && (
            <Button className="mt-4" onClick={() => setIsCreateModalOpen(true)}>
              最初のユーザーを追加
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedUsers.map(user => (
            <UserCard
              key={user.username}
              user={user}
              onEdit={() => setEditingUser(user)}
              onDelete={() => handleDeleteUser(user.username)}
            />
          ))}
        </div>
      )}

      {/* 新規作成モーダル */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="新規ユーザー追加"
        size="lg"
      >
        <UserForm
          onSubmit={handleCreateUser as unknown as (data: UserFormData) => void}
          onCancel={() => setIsCreateModalOpen(false)}
        />
      </Modal>

      {/* 編集モーダル */}
      <Modal
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        title="ユーザー編集"
        size="lg"
      >
        <UserForm
          user={editingUser}
          onSubmit={handleUpdateUser as unknown as (data: UserFormData) => void}
          onCancel={() => setEditingUser(null)}
        />
      </Modal>
    </div>
  )
}
