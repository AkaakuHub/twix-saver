import { useState, useCallback, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { formatJobDateTime } from '../../utils/dateFormat'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { JobForm } from './JobForm'
import { JobResultModal } from './JobResultModal'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { useJobs } from '../../hooks/useJobs'
import type { ScrapingJobResponse } from '../../types/api'
import {
  PlayIcon,
  StopIcon,
  PlusIcon,
  EyeIcon,
  BoltIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'

export const JobsList = () => {
  const [forcePolling, setForcePolling] = useState(false)
  const [hasActiveJobs, setHasActiveJobs] = useState(false)

  const shouldPoll = hasActiveJobs || forcePolling

  const {
    jobs,
    isLoading,
    createJob,
    deleteJob,
    startJob,
    stopJob,
    runJob,
    isCreating,
    isDeleting,
    isStarting,
    isStopping,
    isRunning,
  } = useJobs(shouldPoll)

  // ジョブリストが更新されたら実行中ジョブの有無をチェック
  useEffect(() => {
    const activeJobs = jobs.filter(job =>
      ['running', 'processing'].includes(job.status.toLowerCase())
    )
    const hasActive = activeJobs.length > 0
    setHasActiveJobs(hasActive)

    // 実行中ジョブがなくなったら強制ポーリングを停止
    if (!hasActive && forcePolling) {
      setTimeout(() => setForcePolling(false), 5000) // 5秒後に停止
    }
  }, [jobs, forcePolling])

  // ジョブアクション時に一時的にポーリングを有効化
  const handleStartJob = (jobId: string) => {
    setForcePolling(true)
    startJob(jobId)
  }

  const handleRunJob = (jobId: string) => {
    setForcePolling(true)
    runJob(jobId)
  }

  const [isJobModalOpen, setIsJobModalOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<ScrapingJobResponse | null>(null)
  const [isResultModalOpen, setIsResultModalOpen] = useState(false)

  const getStatusBadge = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <Badge variant="success">完了</Badge>
      case 'failed':
        return <Badge variant="error">失敗</Badge>
      case 'running':
      case 'processing':
        return <Badge variant="info">実行中</Badge>
      case 'pending':
        return <Badge variant="default">待機中</Badge>
      case 'stopped':
        return <Badge variant="warning">停止</Badge>
      case 'cancelled':
        return <Badge variant="default">キャンセル</Badge>
      default:
        return <Badge variant="default">{status}</Badge>
    }
  }, [])

  const canStart = useCallback(
    (status: string) => ['pending', 'stopped', 'failed'].includes(status.toLowerCase()),
    []
  )

  const canStop = useCallback(
    (status: string) => ['running', 'processing'].includes(status.toLowerCase()),
    []
  )

  const handleViewResult = useCallback((job: ScrapingJobResponse) => {
    setSelectedJob(job)
    setIsResultModalOpen(true)
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="ジョブ一覧を読み込み中..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ジョブ管理</h1>
          <p className="text-gray-600">スクレイピングジョブの作成・管理</p>
        </div>
        <Button icon={<PlusIcon className="w-4 h-4" />} onClick={() => setIsJobModalOpen(true)}>
          新規ジョブ作成
        </Button>
      </div>

      {/* ジョブ一覧 */}
      <Card>
        <CardHeader>
          <CardTitle>ジョブ一覧 ({jobs.length}件)</CardTitle>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-4">📝</div>
              <h3 className="text-lg font-medium mb-2">ジョブがありません</h3>
              <p className="text-sm mb-4">最初のスクレイピングジョブを作成してみましょう</p>
              <Button onClick={() => setIsJobModalOpen(true)}>ジョブを作成</Button>
            </div>
          ) : (
            <div className="space-y-4">
              {jobs.map(job => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-medium text-gray-900">
                        {job.target_usernames.map(username => `@${username}`).join(', ')}
                      </h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>ジョブID: {job.job_id.slice(0, 8)}...</span>
                      {job.scraper_account && <span>アカウント: @{job.scraper_account}</span>}
                      {job.created_at && (
                        <span title="作成日時 (JST)">
                          作成: {formatJobDateTime(job.created_at)}
                        </span>
                      )}
                      {job.stats && <span>収集: {job.stats.tweets_collected || 0}件</span>}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* 即座実行ボタン */}
                    {canStart(job.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<BoltIcon className="w-4 h-4" />}
                        onClick={() => handleRunJob(job.job_id)}
                        loading={isRunning}
                        disabled={isRunning}
                        title="即座に実行"
                      >
                        実行
                      </Button>
                    )}

                    {/* 開始ボタン */}
                    {canStart(job.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<PlayIcon className="w-4 h-4" />}
                        onClick={() => handleStartJob(job.job_id)}
                        loading={isStarting}
                        disabled={isStarting || isStopping}
                      >
                        開始
                      </Button>
                    )}

                    {/* 停止ボタン */}
                    {canStop(job.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<StopIcon className="w-4 h-4" />}
                        onClick={() => stopJob(job.job_id)}
                        loading={isStopping}
                        disabled={isStarting || isStopping}
                      >
                        停止
                      </Button>
                    )}

                    {/* 結果表示ボタン */}
                    <Button
                      variant="outline"
                      size="sm"
                      icon={<EyeIcon className="w-4 h-4" />}
                      onClick={() => handleViewResult(job)}
                    >
                      結果
                    </Button>

                    {/* 削除ボタン */}
                    {job.status !== 'running' && (
                      <Button
                        variant="outline"
                        size="sm"
                        icon={<TrashIcon className="w-4 h-4" />}
                        onClick={() => deleteJob(job.job_id)}
                        loading={isDeleting}
                        disabled={isDeleting}
                        className="text-red-600 hover:text-red-700"
                        title="ジョブを削除"
                      >
                        削除
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ジョブ作成モーダル */}
      <Modal isOpen={isJobModalOpen} onClose={() => setIsJobModalOpen(false)} size="2xl">
        <JobForm
          onSubmit={jobData => {
            createJob(jobData)
            setIsJobModalOpen(false)
          }}
          onCancel={() => setIsJobModalOpen(false)}
          isSubmitting={isCreating}
        />
      </Modal>

      {/* ジョブ結果モーダル */}
      <JobResultModal
        isOpen={isResultModalOpen}
        onClose={() => {
          setIsResultModalOpen(false)
          setSelectedJob(null)
        }}
        job={selectedJob}
      />
    </div>
  )
}
