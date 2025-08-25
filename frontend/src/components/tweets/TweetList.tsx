import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTweets, useTweetManagement } from '../../hooks/useTweets'
import { useImageProcessing } from '../../hooks/useImageProcessing'
import { formatDateOnly } from '../../utils/dateFormat'
import { Card } from '../ui/Card'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { TweetSearch, TweetFilters } from './TweetSearch'
import { TweetCard } from './TweetCard'
import {
  ViewColumnsIcon,
  ListBulletIcon,
  ArrowUpIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'

export const TweetList = () => {
  const [searchFilters, setSearchFilters] = useState<TweetFilters>({
    query: '',
    sortBy: 'date',
    sortOrder: 'desc',
  })
  const [viewMode, setViewMode] = useState<'card' | 'compact'>('card')
  const [expandedTweets, setExpandedTweets] = useState<Set<string>>(new Set())
  const [showScrollTop, setShowScrollTop] = useState(false)

  const { retryFailed, loading: imageProcessingLoading } = useImageProcessing()

  const { tweets, isLoading, total, error, hasMore, loadMore } = useTweets({
    search: searchFilters.query,
    username: searchFilters.username,
    start_date: searchFilters.dateFrom,
    end_date: searchFilters.dateTo,
    has_media: searchFilters.hasMedia,
    has_articles: searchFilters.hasArticles,
    min_engagement: searchFilters.minEngagement,
    hashtags: searchFilters.hashtags?.join(','),
    sort_by: searchFilters.sortBy,
    sort_order: searchFilters.sortOrder,
    page: 1,
    page_size: 20,
  })

  const {
    deleteTweet,
    refreshTweet,
    refreshAllTweets,
    deleteAllTweets,
    isRefreshing,
    isDeletingAll,
  } = useTweetManagement()

  // スクロール検出
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 400)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleFiltersChange = (filters: TweetFilters) => {
    setSearchFilters(filters)
  }

  const handleTweetExpand = useCallback(
    (tweetId: string) => {
      const newExpanded = new Set(expandedTweets)
      if (newExpanded.has(tweetId)) {
        newExpanded.delete(tweetId)
      } else {
        newExpanded.add(tweetId)
      }
      setExpandedTweets(newExpanded)
    },
    [expandedTweets]
  )

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  // 2段階確認での全ツイート削除
  const handleDeleteAllTweets = useCallback(() => {
    // 第1段階確認
    const firstConfirm = window.confirm(
      `⚠️ 本当にすべてのツイートを削除しますか？\n\n` +
        `削除されるデータ:\n` +
        `• 全ツイート (${total.toLocaleString()}件)\n` +
        `• 関連するメディアファイル\n` +
        `• この操作は取り消せません\n\n` +
        `続行するには「OK」をクリックしてください。`
    )

    if (!firstConfirm) return

    // 第2段階確認
    const secondConfirm = window.confirm(
      `🚨 最終確認\n\n` +
        `すべてのツイートとメディアファイルが完全に削除されます。\n` +
        `この操作は絶対に元に戻せません。\n\n` +
        `本当に削除を実行しますか？`
    )

    if (secondConfirm) {
      deleteAllTweets()
    }
  }, [total, deleteAllTweets])

  // メモ化されたツイート変換
  const transformedTweets = useMemo(() => {
    return tweets.map(tweet => ({
      ...tweet,
      tweetCardData: {
        id: tweet.id,
        text: tweet.text,
        author: tweet.author,
        created_at: tweet.created_at || '',
        scraped_at: tweet.scraped_at || undefined,
        public_metrics: tweet.public_metrics,
        downloaded_media: tweet.downloaded_media,
        extracted_articles: tweet.extracted_articles?.map((article: Record<string, unknown>) => ({
          title: (article.title as string) || '',
          url: (article.url as string) || '',
          description: (article.description as string) || undefined,
          image: (article.image as string) || undefined,
          domain: (article.domain as string) || undefined,
        })) as
          | Array<{
              title: string
              url: string
              description?: string
              image?: string
              domain?: string
            }>
          | undefined,
      },
    }))
  }, [tweets])

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 text-lg mb-4">ツイートの読み込み中にエラーが発生しました</div>
        <div className="text-gray-600">{error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ツイート一覧</h1>
          <p className="text-gray-600">
            {total > 0 ? (
              <>
                収集されたツイート ({total.toLocaleString()}件)
                {searchFilters.query && (
                  <span className="ml-2 text-blue-600">「{searchFilters.query}」の検索結果</span>
                )}
              </>
            ) : (
              'ツイートを検索・フィルタしてください'
            )}
          </p>
        </div>

        {/* 表示モード切替・管理機能 */}
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshAllTweets()}
            loading={isRefreshing}
            icon={<ArrowPathIcon className="w-4 h-4" />}
          >
            全再取得
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => retryFailed(100)}
            loading={imageProcessingLoading}
            className="text-amber-600 border-amber-300 hover:bg-amber-50"
          >
            📸 画像のみリトライ
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDeleteAllTweets}
            loading={isDeletingAll}
            className="text-red-600 border-red-300 hover:bg-red-50"
            disabled={total === 0}
          >
            🗑️ 全ツイート削除
          </Button>

          <div className="border-l border-gray-200 h-6 mx-2" />

          <Button
            variant={viewMode === 'card' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('card')}
            icon={<ViewColumnsIcon className="w-4 h-4" />}
          >
            カード
          </Button>
          <Button
            variant={viewMode === 'compact' ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('compact')}
            icon={<ListBulletIcon className="w-4 h-4" />}
          >
            コンパクト
          </Button>
        </div>
      </div>

      {/* 検索・フィルタ */}
      <TweetSearch onSearch={() => {}} onFiltersChange={handleFiltersChange} />

      {/* ローディング */}
      {isLoading && tweets.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" text="ツイートを読み込み中..." />
        </div>
      )}

      {/* ツイート一覧 */}
      {!isLoading && tweets.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg mb-4">
            {searchFilters.query ||
            Object.values(searchFilters).some(
              v => v !== undefined && v !== '' && v !== 'date' && v !== 'desc'
            )
              ? 'マッチするツイートが見つかりません'
              : 'ツイートデータがありません'}
          </div>
          {searchFilters.query && (
            <p className="text-gray-400">フィルタ条件を変更して再検索してください</p>
          )}
        </div>
      ) : (
        <div className={clsx(viewMode === 'card' ? 'space-y-6' : 'space-y-3')}>
          {transformedTweets.map(tweet =>
            viewMode === 'card' ? (
              <TweetCard
                key={tweet.id}
                tweet={tweet.tweetCardData}
                expanded={expandedTweets.has(tweet.id.toString())}
                onExpand={handleTweetExpand}
                onDelete={deleteTweet}
                onRefreshTweet={refreshTweet}
              />
            ) : (
              <Card key={tweet.id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-blue-600 text-sm">
                        @{tweet.author.username}
                      </span>
                      <span className="text-gray-500 text-xs" title="ツイート作成日 (JST)">
                        {tweet.created_at && formatDateOnly(tweet.created_at)}
                      </span>
                    </div>
                    <div className="truncate text-sm text-gray-900 flex-1">{tweet.text}</div>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-500 ml-4">
                    <span>❤️ {tweet.public_metrics.like_count || 0}</span>
                    <span>🔄 {tweet.public_metrics.retweet_count || 0}</span>
                    {(tweet.downloaded_media?.length || 0) > 0 && (
                      <Badge variant="info" size="sm">
                        メディア
                      </Badge>
                    )}
                    {tweet.extracted_articles && (
                      <Badge variant="success" size="sm">
                        記事
                      </Badge>
                    )}
                  </div>
                </div>
              </Card>
            )
          )}
        </div>
      )}

      {/* もっと読み込む */}
      {hasMore && tweets.length > 0 && (
        <div className="flex justify-center py-6">
          <Button onClick={loadMore} variant="outline" loading={isLoading}>
            もっと読み込む
          </Button>
        </div>
      )}

      {/* トップに戻るボタン */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors z-10"
        >
          <ArrowUpIcon className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}
