import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../stores/appStore'
import type { ScrapingJobResponse, ScrapingJobCreate } from '../types/api'

const API_BASE = 'http://localhost:8000/api'

export const useJobs = () => {
  const { addNotification } = useAppStore()
  const queryClient = useQueryClient()

  const {
    data: jobs = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['jobs'],
    queryFn: async (): Promise<ScrapingJobResponse[]> => {
      const response = await fetch(`${API_BASE}/jobs`)
      if (!response.ok) {
        throw new Error('ジョブ一覧の取得に失敗しました')
      }
      return response.json()
    },
    staleTime: 1000 * 30, // 30秒
    refetchInterval: 1000 * 10, // 10秒毎に自動更新
  })

  const createJobMutation = useMutation({
    mutationFn: async (jobData: ScrapingJobCreate): Promise<ScrapingJobResponse> => {
      const response = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jobData),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ジョブの作成に失敗しました')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      addNotification({
        type: 'success',
        title: 'スクレイピングジョブを作成しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ジョブ作成エラー',
        message: error.message,
      })
    },
  })

  const cancelJobMutation = useMutation({
    mutationFn: async (jobId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error('ジョブのキャンセルに失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      addNotification({
        type: 'info',
        title: 'ジョブをキャンセルしました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ジョブキャンセルエラー',
        message: error.message,
      })
    },
  })

  return {
    jobs,
    isLoading,
    error,
    refetch,
    createJob: createJobMutation.mutate,
    cancelJob: cancelJobMutation.mutate,
    isCreating: createJobMutation.isPending,
    isCancelling: cancelJobMutation.isPending,
  }
}

export const useActiveJobs = () => {
  return useQuery({
    queryKey: ['active-jobs'],
    queryFn: async (): Promise<ScrapingJobResponse[]> => {
      const response = await fetch(`${API_BASE}/jobs/active`)
      if (!response.ok) {
        throw new Error('アクティブジョブの取得に失敗しました')
      }
      return response.json()
    },
    staleTime: 1000 * 10, // 10秒
    refetchInterval: 1000 * 5, // 5秒毎に自動更新
  })
}

export const useJobStats = () => {
  return useQuery({
    queryKey: ['job-stats'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/jobs/stats`)
      if (!response.ok) {
        throw new Error('ジョブ統計の取得に失敗しました')
      }
      return response.json()
    },
    staleTime: 1000 * 60, // 1分
    refetchInterval: 1000 * 30, // 30秒毎に自動更新
  })
}
