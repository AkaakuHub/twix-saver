import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../stores/appStore'
import type { TargetUserResponse, TargetUserCreate, TargetUserUpdate } from '../types/api'

const API_BASE = 'http://localhost:8000/api'

export const useUsers = () => {
  const { addNotification } = useAppStore()
  const queryClient = useQueryClient()

  const {
    data: users = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['users'],
    queryFn: async (): Promise<TargetUserResponse[]> => {
      try {
        const response = await fetch(`${API_BASE}/users`)
        if (!response.ok) {
          throw new Error('ユーザー一覧の取得に失敗しました')
        }
        return response.json()
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          throw new Error('バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。')
        }
        throw error
      }
    },
    staleTime: 1000 * 60 * 5, // 5分
  })

  const createUserMutation = useMutation({
    mutationFn: async (userData: TargetUserCreate): Promise<TargetUserResponse> => {
      const response = await fetch(`${API_BASE}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ユーザーの作成に失敗しました')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addNotification({
        type: 'success',
        title: 'ユーザーを追加しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ユーザー追加エラー',
        message: error.message,
      })
    },
  })

  const updateUserMutation = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string
      data: TargetUserUpdate
    }): Promise<TargetUserResponse> => {
      const response = await fetch(`${API_BASE}/users/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ユーザーの更新に失敗しました')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addNotification({
        type: 'success',
        title: 'ユーザーを更新しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ユーザー更新エラー',
        message: error.message,
      })
    },
  })

  const deleteUserMutation = useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/users/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error('ユーザーの削除に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addNotification({
        type: 'success',
        title: 'ユーザーを削除しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ユーザー削除エラー',
        message: error.message,
      })
    },
  })

  const bulkUpdateMutation = useMutation({
    mutationFn: async ({
      userIds,
      updates,
    }: {
      userIds: string[]
      updates: Partial<TargetUserResponse>
    }) => {
      const promises = userIds.map(id =>
        fetch(`${API_BASE}/users/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates),
        })
      )

      const responses = await Promise.all(promises)
      const failedUpdates = responses.filter(r => !r.ok)

      if (failedUpdates.length > 0) {
        throw new Error(`${failedUpdates.length}件のユーザー更新に失敗しました`)
      }
    },
    onSuccess: (_, { userIds }) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      addNotification({
        type: 'success',
        title: `${userIds.length}件のユーザーを更新しました`,
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: '一括更新エラー',
        message: error.message,
      })
    },
  })

  return {
    users,
    isLoading,
    error,
    refetch,
    createUser: createUserMutation.mutate,
    updateUser: updateUserMutation.mutate,
    deleteUser: deleteUserMutation.mutate,
    bulkUpdate: bulkUpdateMutation.mutate,
    isCreating: createUserMutation.isPending,
    isUpdating: updateUserMutation.isPending,
    isDeleting: deleteUserMutation.isPending,
    isBulkUpdating: bulkUpdateMutation.isPending,
  }
}
