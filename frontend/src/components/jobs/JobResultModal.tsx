import { Modal } from '../ui/Modal'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline'
import type { ScrapingJobResponse } from '../../types/api'

interface JobResultModalProps {
  isOpen: boolean
  onClose: () => void
  job: ScrapingJobResponse | null
}

export const JobResultModal = ({ isOpen, onClose, job }: JobResultModalProps) => {
  if (!job) return null

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
    job.stats &&
    (job.stats.tweets_collected > 0 ||
      job.stats.articles_extracted > 0 ||
      job.stats.media_downloaded > 0)

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" title="ジョブ実行結果">
      <div className="space-y-6">
        {/* ジョブ基本情報 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                {getStatusIcon(job.status)}
                <span>ジョブ情報</span>
              </CardTitle>
              {getStatusBadge(job.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-700">ジョブID:</span>
              <span className="ml-2 text-sm text-gray-900 font-mono">{job.job_id}</span>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-700">対象ユーザー:</span>
              <span className="ml-2 text-sm text-gray-900">
                {job.target_usernames.map(username => `@${username}`).join(', ')}
              </span>
            </div>
            {job.created_at && (
              <div>
                <span className="text-sm font-medium text-gray-700">作成日時:</span>
                <span className="ml-2 text-sm text-gray-900">
                  {new Date(job.created_at).toLocaleString('ja-JP')}
                </span>
              </div>
            )}
            {job.scraper_account && (
              <div>
                <span className="text-sm font-medium text-gray-700">使用アカウント:</span>
                <span className="ml-2 text-sm text-gray-900">@{job.scraper_account}</span>
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
            {!hasData && job.status === 'completed' ? (
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
                    {job.stats?.tweets_collected || 0}
                  </div>
                  <div className="text-sm text-blue-700">収集ツイート</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {job.stats?.articles_extracted || 0}
                  </div>
                  <div className="text-sm text-green-700">記事抽出</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {job.stats?.media_downloaded || 0}
                  </div>
                  <div className="text-sm text-purple-700">メディア取得</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {job.stats?.errors_count || 0}
                  </div>
                  <div className="text-sm text-red-700">エラー数</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* エラーログ */}
        {job.errors && job.errors.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-red-600">エラーログ</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-red-50 border border-red-200 rounded-md p-4 max-h-64 overflow-y-auto">
                {job.errors.map((error, index) => (
                  <div key={index} className="text-sm text-red-700 mb-2 font-mono">
                    {error}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 実行ログ（最新5件） */}
        {job.logs && job.logs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>実行ログ（最新5件）</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4 max-h-64 overflow-y-auto">
                {job.logs.slice(-5).map((log, index) => (
                  <div key={index} className="text-sm text-gray-700 mb-1 font-mono">
                    {log}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Modal>
  )
}
