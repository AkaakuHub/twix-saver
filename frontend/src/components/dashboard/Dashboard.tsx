import { useState, useEffect } from 'react'
import { useAutoWebSocket } from '../../hooks/useWebSocket'
import { useActiveJobs, useJobStats } from '../../hooks/useJobs'
import { useTweetStats } from '../../hooks/useTweets'
import { useUsers } from '../../hooks/useUsers'
import { useWebSocketStore } from '../../stores/websocketStore'
import type { ScrapingJobResponse } from '../../types/api'
import { StatsCard } from './StatsCard'
import { ActivityFeed } from './ActivityFeed'
import { TweetsTimeChart } from './charts/TweetsTimeChart'
import { JobSuccessRateChart } from './charts/JobSuccessRateChart'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { Button } from '../ui/Button'
import { PlusIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline'

export const Dashboard = () => {
  const { connected: wsConnected } = useAutoWebSocket()
  const { ws } = useWebSocketStore()

  // リアルタイム統計状態
  const [realtimeStats, setRealtimeStats] = useState<{
    users?: { total: number; active: number }
    tweets?: { total: number }
    jobs?: { running: number }
  } | null>(null)

  const { users = [], isLoading: usersLoading } = useUsers()
  const { data: activeJobs = [], isLoading: activeJobsLoading } = useActiveJobs()
  const { data: jobStats, isLoading: jobStatsLoading } = useJobStats()
  const { data: tweetStats, isLoading: tweetStatsLoading } = useTweetStats()

  // WebSocket経由でシステム統計を受信
  useEffect(() => {
    if (!ws || !wsConnected) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)

        if (message.type === 'system_stats') {
          setRealtimeStats(message.data)
        }
      } catch (error) {
        console.error('WebSocketメッセージの処理に失敗:', error)
      }
    }

    ws.addEventListener('message', handleMessage)
    return () => {
      ws.removeEventListener('message', handleMessage)
    }
  }, [ws, wsConnected])

  // ジョブ成功率を計算
  const calculateSuccessRate = () => {
    if (realtimeStats?.jobs) {
      const jobs = realtimeStats.jobs as { completed_today?: number; failed_today?: number }
      const completed_today = jobs.completed_today || 0
      const failed_today = jobs.failed_today || 0
      const total = completed_today + failed_today
      return total > 0 ? Math.round((completed_today / total) * 100) : 0
    }
    return (jobStats as { successRate?: number })?.successRate || 0
  }

  const isLoading = usersLoading || activeJobsLoading || jobStatsLoading || tweetStatsLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" text="ダッシュボードを読み込み中..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
          <p className="text-gray-600">Twix Saverシステムの概要</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div
              className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}
            />
            <span className="text-sm text-gray-600">
              {wsConnected ? 'リアルタイム接続中' : '接続なし'}
            </span>
          </div>
          <Button icon={<PlusIcon className="w-4 h-4" />}>新規ジョブ作成</Button>
        </div>
      </div>

      {/* 統計カード */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="監視ユーザー数"
          value={
            (realtimeStats?.users as { total?: number })?.total || (users as unknown[]).length || 0
          }
          previousValue={
            (realtimeStats?.users as { active?: number })?.active ||
            (users as unknown[]).length ||
            0
          }
          icon="users"
          color="blue"
        />
        <StatsCard
          title="収集ツイート数"
          value={
            (realtimeStats?.tweets as { total?: number })?.total ||
            (tweetStats as { total?: number })?.total ||
            0
          }
          previousValue={(tweetStats as { yesterday?: number })?.yesterday || 0}
          icon="tweets"
          color="green"
        />
        <StatsCard
          title="実行中ジョブ"
          value={
            (realtimeStats?.jobs as { running?: number })?.running ||
            (activeJobs as unknown[]).length ||
            0
          }
          previousValue={0}
          icon="jobs"
          color="yellow"
        />
        <StatsCard
          title="ジョブ成功率"
          value={calculateSuccessRate()}
          previousValue={(jobStats as { previousSuccessRate?: number })?.previousSuccessRate || 0}
          icon="success"
          color="purple"
          suffix="%"
        />
      </div>

      {/* チャートとアクティビティ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>ツイート収集推移</CardTitle>
          </CardHeader>
          <CardContent>
            <TweetsTimeChart />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>ジョブ成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <JobSuccessRateChart />
          </CardContent>
        </Card>
      </div>

      {/* アクティブジョブとアクティビティフィード */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>実行中ジョブ</CardTitle>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm" icon={<PlayIcon className="w-4 h-4" />}>
                  全開始
                </Button>
                <Button variant="outline" size="sm" icon={<StopIcon className="w-4 h-4" />}>
                  全停止
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {(activeJobs as unknown[]).length === 0 ? (
              <div className="text-center py-8 text-gray-500">実行中のジョブはありません</div>
            ) : (
              <div className="space-y-3">
                {(activeJobs as ScrapingJobResponse[])
                  .slice(0, 5)
                  .map((job: ScrapingJobResponse) => (
                    <div
                      key={job.job_id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div>
                        <div className="font-medium text-sm">{job.target_usernames.join(', ')}</div>
                        <div className="text-xs text-gray-600">{job.status}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-600">実行中</div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>最近のアクティビティ</CardTitle>
          </CardHeader>
          <CardContent>
            <ActivityFeed />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
