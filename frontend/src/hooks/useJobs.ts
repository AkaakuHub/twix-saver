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
      try {
        const response = await fetch(`${API_BASE}/jobs`)
        if (!response.ok) {
          throw new Error('ジョブ一覧の取得に失敗しました')
        }
        return response.json()
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          throw new Error(
            'バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。'
          )
        }
        throw error
      }
    },
    staleTime: Infinity, // 手動更新のみ
    refetchOnWindowFocus: false,
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
      queryClient.invalidateQueries({ queryKey: ['active-jobs'] })
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

  const startJobMutation = useMutation({
    mutationFn: async (jobId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/jobs/${jobId}/start`, {
        method: 'PUT',
      })
      if (!response.ok) {
        throw new Error('ジョブの開始に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['active-jobs'] })
      addNotification({
        type: 'success',
        title: 'ジョブを開始しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ジョブ開始エラー',
        message: error.message,
      })
    },
  })

  const stopJobMutation = useMutation({
    mutationFn: async (jobId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/jobs/${jobId}/stop`, {
        method: 'PUT',
      })
      if (!response.ok) {
        throw new Error('ジョブの停止に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['active-jobs'] })
      addNotification({
        type: 'info',
        title: 'ジョブを停止しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ジョブ停止エラー',
        message: error.message,
      })
    },
  })

  const startAllJobs = async () => {
    const runningJobs = jobs.filter(job => job.status === 'pending' || job.status === 'stopped')
    for (const job of runningJobs) {
      startJobMutation.mutate(job.job_id)
    }
  }

  const stopAllJobs = async () => {
    const activeJobs = jobs.filter(job => job.status === 'running' || job.status === 'processing')
    for (const job of activeJobs) {
      stopJobMutation.mutate(job.job_id)
    }
  }

  return {
    jobs,
    isLoading,
    error,
    refetch,
    createJob: createJobMutation.mutate,
    cancelJob: cancelJobMutation.mutate,
    startJob: startJobMutation.mutate,
    stopJob: stopJobMutation.mutate,
    startAllJobs,
    stopAllJobs,
    isCreating: createJobMutation.isPending,
    isCancelling: cancelJobMutation.isPending,
    isStarting: startJobMutation.isPending,
    isStopping: stopJobMutation.isPending,
  }
}

export const useActiveJobs = () => {
  return useQuery({
    queryKey: ['active-jobs'],
    queryFn: async (): Promise<ScrapingJobResponse[]> => {
      try {
        const response = await fetch(`${API_BASE}/jobs/active`)
        if (!response.ok) {
          throw new Error('アクティブジョブの取得に失敗しました')
        }
        return response.json()
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          throw new Error(
            'バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。'
          )
        }
        throw error
      }
    },
    staleTime: Infinity, // 手動更新のみ
    refetchOnWindowFocus: false,
  })
}

export const useJobStats = () => {
  return useQuery({
    queryKey: ['job-stats'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE}/jobs/stats`)
        if (!response.ok) {
          throw new Error('ジョブ統計の取得に失敗しました')
        }
        return response.json()
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          throw new Error(
            'バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。'
          )
        }
        throw error
      }
    },
    staleTime: Infinity, // 手動更新のみ
    refetchOnWindowFocus: false,
  })
}
