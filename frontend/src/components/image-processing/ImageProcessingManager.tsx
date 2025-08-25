import { useEffect, useState } from 'react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { useImageProcessing } from '../../hooks/useImageProcessing'
import { formatJobDateTime } from '../../utils/dateFormat'
import { ImageProcessingStatus } from '../../types/api'
import type { ImageProcessingRetryRequest } from '../../types/api'

export const ImageProcessingManager = () => {
  const {
    loading,
    stats,
    failedTweets,
    fetchStats,
    fetchFailedTweets,
    retryFailed,
    retryAll,
    migrateLegacyTweets,
  } = useImageProcessing()

  const [retryLoading, setRetryLoading] = useState(false)
  const [retryOptions, setRetryOptions] = useState<ImageProcessingRetryRequest>({
    max_tweets: 100,
    username: undefined,
    force_reprocess: false,
  })

  useEffect(() => {
    fetchStats()
    fetchFailedTweets()
  }, [fetchStats, fetchFailedTweets])

  const handleRetryFailed = async () => {
    setRetryLoading(true)
    await retryFailed(100)
    setRetryLoading(false)
  }

  const handleRetryAll = async () => {
    if (
      !confirm(
        `${retryOptions.force_reprocess ? '強制再処理' : '未完了ツイートのリトライ'}を実行しますか？\n` +
          `最大${retryOptions.max_tweets}件のツイートが対象です。`
      )
    ) {
      return
    }

    setRetryLoading(true)
    await retryAll(retryOptions)
    setRetryLoading(false)
  }

  const handleMigration = async () => {
    if (
      !confirm('レガシーツイートのマイグレーションを実行しますか？\n画像処理状態が追加されます。')
    ) {
      return
    }

    setRetryLoading(true)
    await migrateLegacyTweets(1000)
    setRetryLoading(false)
  }

  const getStatusBadge = (status: string, count: number) => {
    if (count === 0) return null

    const variants = {
      [ImageProcessingStatus.COMPLETED]: 'success',
      [ImageProcessingStatus.FAILED]: 'error',
      [ImageProcessingStatus.PENDING]: 'warning',
      [ImageProcessingStatus.PROCESSING]: 'info',
      [ImageProcessingStatus.SKIPPED]: 'default',
    } as const

    return <Badge variant={variants[status as keyof typeof variants] || 'default'}>{count}件</Badge>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">📸 画像処理管理</h1>
        <Button
          onClick={() => {
            fetchStats()
            fetchFailedTweets()
          }}
          disabled={loading}
          size="sm"
          variant="outline"
        >
          🔄 更新
        </Button>
      </div>

      {/* 統計情報 */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">📊 処理状況統計</h2>

          {stats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">
                  {stats.total_tweets.toLocaleString()}
                </div>
                <div className="text-sm text-gray-600">総ツイート数</div>
              </div>

              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-700">
                  {stats.image_processing_stats.completed.toLocaleString()}
                </div>
                <div className="text-sm text-green-600">完了</div>
              </div>

              <div className="text-center p-4 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-700">
                  {stats.image_processing_stats.failed.toLocaleString()}
                </div>
                <div className="text-sm text-red-600">失敗</div>
              </div>

              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-700">{stats.success_rate}%</div>
                <div className="text-sm text-blue-600">成功率</div>
              </div>
            </div>
          ) : loading ? (
            <div className="animate-pulse">
              <div className="grid grid-cols-4 gap-4 mb-4">
                {Array(4)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="h-20 bg-gray-200 rounded-lg"></div>
                  ))}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">統計情報の取得に失敗しました</div>
          )}

          {/* 詳細統計 */}
          {stats && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-md font-medium mb-3">詳細状況</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.image_processing_stats).map(([status, count]) => {
                  const labels = {
                    pending: '未処理',
                    processing: '処理中',
                    completed: '完了',
                    failed: '失敗',
                    skipped: 'スキップ',
                    no_status: '状態なし',
                  }
                  return (
                    <div key={status} className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">
                        {labels[status as keyof typeof labels] || status}:
                      </span>
                      {getStatusBadge(status, count)}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* リトライ操作 */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">🔄 リトライ操作</h2>

          <div className="space-y-4">
            {/* 失敗分のみリトライ */}
            <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
              <div>
                <h3 className="font-medium text-yellow-800">失敗分のみリトライ</h3>
                <p className="text-sm text-yellow-600">
                  画像処理が失敗したツイートのみを再処理します
                </p>
              </div>
              <Button
                onClick={handleRetryFailed}
                disabled={retryLoading || loading}
                variant="outline"
                size="sm"
              >
                {retryLoading ? '処理中...' : 'リトライ実行'}
              </Button>
            </div>

            {/* 全体リトライ設定 */}
            <div className="p-4 bg-blue-50 rounded-lg">
              <h3 className="font-medium text-blue-800 mb-3">全体リトライ</h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    最大処理件数
                  </label>
                  <input
                    type="number"
                    value={retryOptions.max_tweets}
                    onChange={e =>
                      setRetryOptions({
                        ...retryOptions,
                        max_tweets: parseInt(e.target.value) || 100,
                      })
                    }
                    min="1"
                    max="10000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    特定ユーザー（省略時は全員）
                  </label>
                  <input
                    type="text"
                    value={retryOptions.username || ''}
                    onChange={e =>
                      setRetryOptions({
                        ...retryOptions,
                        username: e.target.value || undefined,
                      })
                    }
                    placeholder="@username"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>

                <div className="flex items-center">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={retryOptions.force_reprocess}
                      onChange={e =>
                        setRetryOptions({
                          ...retryOptions,
                          force_reprocess: e.target.checked,
                        })
                      }
                      className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">強制再処理（完了済み含む）</span>
                  </label>
                </div>
              </div>

              <Button
                onClick={handleRetryAll}
                disabled={retryLoading || loading}
                variant="primary"
                size="sm"
              >
                {retryLoading ? '処理中...' : '全体リトライ実行'}
              </Button>
            </div>

            {/* マイグレーション */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <h3 className="font-medium text-gray-800">レガシーデータマイグレーション</h3>
                <p className="text-sm text-gray-600">
                  画像処理状態がない既存ツイートに状態を追加します
                </p>
              </div>
              <Button
                onClick={handleMigration}
                disabled={retryLoading || loading}
                variant="outline"
                size="sm"
              >
                {retryLoading ? '処理中...' : 'マイグレーション'}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* 失敗ツイート一覧 */}
      <Card>
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">❌ 失敗ツイート一覧</h2>

          {failedTweets?.failed_tweets.length ? (
            <div className="space-y-3">
              {failedTweets.failed_tweets.map(tweet => (
                <div
                  key={tweet.id_str}
                  className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">@{tweet.author_username}</span>
                      <Badge variant="error" size="sm">
                        {tweet.image_processing_retry_count || 0}回リトライ
                      </Badge>
                    </div>
                    <div className="text-sm text-red-600 mt-1">
                      {tweet.image_processing_error || 'エラー詳細不明'}
                    </div>
                    {tweet.image_processing_attempted_at && (
                      <div className="text-xs text-gray-500 mt-1">
                        最終試行: {formatJobDateTime(tweet.image_processing_attempted_at)}
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={() =>
                      retryAll({
                        max_tweets: 1,
                        username: tweet.author_username,
                      })
                    }
                    disabled={retryLoading}
                    variant="outline"
                    size="sm"
                  >
                    個別リトライ
                  </Button>
                </div>
              ))}

              {failedTweets.total_failed > failedTweets.failed_tweets.length && (
                <div className="text-center text-sm text-gray-500 pt-4">
                  他に{failedTweets.total_failed - failedTweets.failed_tweets.length}
                  件の失敗ツイートがあります
                </div>
              )}
            </div>
          ) : loading ? (
            <div className="animate-pulse space-y-3">
              {Array(3)
                .fill(0)
                .map((_, i) => (
                  <div key={i} className="h-16 bg-gray-200 rounded-lg"></div>
                ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">😊 失敗したツイートはありません</div>
          )}
        </div>
      </Card>
    </div>
  )
}
