import { useState, useEffect, useRef } from 'react'
import { Modal } from '../ui/Modal'
import { formatJobDateTime } from '../../utils/dateFormat'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { CheckCircleIcon, XCircleIcon, ClockIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import { useJobLogs, useJobDetail } from '../../hooks/useJobs'
import type { ScrapingJobResponse } from '../../types/api'

interface JobResultModalProps {
  isOpen: boolean
  onClose: () => void
  job: ScrapingJobResponse | null
}

export const JobResultModal = ({ isOpen, onClose, job }: JobResultModalProps) => {
  const [lastTimestamp, setLastTimestamp] = useState<string | undefined>()
  const [allLogs, setAllLogs] = useState<string[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)

  // ジョブ詳細をリアルタイム取得（ステータス・統計更新用）
  const { data: currentJob } = useJobDetail(job?.job_id || '')

  // ジョブログをリアルタイム取得
  const { data: logData, isLoading: isLogsLoading } = useJobLogs(job?.job_id || '', lastTimestamp)

  // 表示に使用するジョブデータ（リアルタイム更新された値を優先）
  const displayJob = currentJob || job

  // ログが更新されたときの処理
  useEffect(() => {
    if (logData?.logs) {
      if (!lastTimestamp) {
        // 初回ロード時はすべてのログを設定
        setAllLogs(logData.logs)
      } else {
        // 差分のみを追加
        setAllLogs(prev => [...prev, ...logData.logs])
      }

      if (logData.last_timestamp) {
        setLastTimestamp(logData.last_timestamp)
      }
    }
  }, [logData, lastTimestamp])

  // ログが追加されたときに下にスクロール
  useEffect(() => {
    if (logsEndRef.current && logData?.logs?.length > 0) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logData?.logs])

  // モーダルが開いたときにログをリセット
  useEffect(() => {
    if (isOpen && job) {
      setLastTimestamp(undefined)
      setAllLogs([])
    }
  }, [isOpen, job])

  if (!displayJob) return null

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <Badge variant="success">完了</Badge>
      case 'failed':
        return <Badge variant="error">失敗</Badge>
      case 'running':
        return <Badge variant="info">実行中</Badge>
      case 'pending':
        return <Badge variant="default">待機中</Badge>
      default:
        return <Badge variant="default">{status}</Badge>
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircleIcon className="w-5 h-5 text-red-500" />
      case 'running':
      case 'pending':
        return <ClockIcon className="w-5 h-5 text-yellow-500" />
      default:
        return <ClockIcon className="w-5 h-5 text-gray-500" />
    }
  }

  const hasData =
    displayJob.stats &&
    (displayJob.stats.tweets_collected > 0 ||
      displayJob.stats.articles_extracted > 0 ||
      displayJob.stats.media_downloaded > 0)

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" title="ジョブ実行結果">
      <div className="space-y-6">
        {/* ジョブ基本情報 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                {getStatusIcon(displayJob.status)}
                <span>ジョブ情報</span>
              </CardTitle>
              {getStatusBadge(displayJob.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-700">ジョブID:</span>
              <span className="ml-2 text-sm text-gray-900 font-mono">{displayJob.job_id}</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-700">対象ユーザー:</span>
              <span className="ml-2 text-sm text-gray-900">
                {displayJob.target_usernames.map(username => `@${username}`).join(', ')}
              </span>
            </div>
            {displayJob.created_at && (
              <div>
                <span className="text-sm font-medium text-gray-700">作成日時:</span>
                <span className="ml-2 text-sm text-gray-900" title="JST">
                  {formatJobDateTime(displayJob.created_at)}
                </span>
              </div>
            )}
            {displayJob.scraper_account && (
              <div>
                <span className="text-sm font-medium text-gray-700">使用アカウント:</span>
                <span className="ml-2 text-sm text-gray-900">@{displayJob.scraper_account}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 実行結果・統計 */}
        <Card>
          <CardHeader>
            <CardTitle>実行結果</CardTitle>
          </CardHeader>
          <CardContent>
            {!hasData && displayJob.status === 'completed' ? (
              <div className="text-center py-8">
                <div className="text-6xl mb-4">📭</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">diff なし</h3>
                <p className="text-sm text-gray-600">
                  指定したユーザーからは新しいツイートが見つかりませんでした
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {displayJob.stats?.tweets_collected || 0}
                  </div>
                  <div className="text-sm text-blue-700">収集ツイート</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {displayJob.stats?.articles_extracted || 0}
                  </div>
                  <div className="text-sm text-green-700">記事抽出</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {displayJob.stats?.media_downloaded || 0}
                  </div>
                  <div className="text-sm text-purple-700">メディア取得</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {displayJob.stats?.errors_count || 0}
                  </div>
                  <div className="text-sm text-red-700">エラー数</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* エラーログ */}
        {displayJob.errors && displayJob.errors.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-red-600">エラーログ</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-red-50 border border-red-200 rounded-md p-4 max-h-64 overflow-y-auto">
                {displayJob.errors.map((error, index) => (
                  <div key={index} className="text-sm text-red-700 mb-2 font-mono">
                    {error}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* リアルタイム実行ログ */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <span>実行ログ</span>
                {(['running', 'processing'].includes(displayJob.status.toLowerCase()) ||
                  isLogsLoading) && (
                  <ArrowPathIcon className="w-4 h-4 animate-spin text-blue-500" />
                )}
                {['running', 'processing'].includes(displayJob.status.toLowerCase()) && (
                  <Badge variant="info" size="sm">
                    リアルタイム更新
                  </Badge>
                )}
              </CardTitle>
              <div className="text-sm text-gray-500">
                {allLogs.length > 0 ? `${allLogs.length}件のログ` : 'ログなし'}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-gray-900 text-gray-100 rounded-md p-4 max-h-96 overflow-y-auto font-mono text-sm">
              {allLogs.length === 0 && !isLogsLoading ? (
                <div className="text-gray-400 text-center py-8">ログがまだありません</div>
              ) : (
                <div className="space-y-1">
                  {allLogs.map((log, index) => (
                    <div key={index} className="text-gray-100">
                      {log}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Modal>
  )
}
