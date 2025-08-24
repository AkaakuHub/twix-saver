import { useState, useEffect } from 'react'
import { useTweets } from '../../hooks/useTweets'
import { Card } from '../ui/Card'
import { LoadingSpinner } from '../ui/LoadingSpinner'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { TweetSearch, TweetFilters } from './TweetSearch'
import { TweetCard } from './TweetCard'
import { ViewColumnsIcon, ListBulletIcon, ArrowUpIcon } from '@heroicons/react/24/outline'
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

  const handleTweetExpand = (tweetId: string) => {
    const newExpanded = new Set(expandedTweets)
    if (newExpanded.has(tweetId)) {
      newExpanded.delete(tweetId)
    } else {
      newExpanded.add(tweetId)
    }
    setExpandedTweets(newExpanded)
  }

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

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

        {/* 表示モード切替 */}
        <div className="flex items-center space-x-2">
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
          {tweets.map(tweet =>
            viewMode === 'card' ? (
              <TweetCard
                key={tweet.id_str}
                tweet={{
                  id: tweet.id_str,
                  text: tweet.content,
                  author: {
                    username: tweet.author_username,
                    display_name: tweet.author_display_name || tweet.author_username,
                    profile_image_url: undefined,
                  },
                  created_at: tweet.created_at || '',
                  public_metrics: {
                    like_count: tweet.like_count || 0,
                    retweet_count: tweet.retweet_count || 0,
                    reply_count: tweet.reply_count || 0,
                    quote_count: 0,
                  },
                  media: tweet.downloaded_media?.map((media: Record<string, unknown>) => ({
                    type: 'photo' as const,
                    url: media.url || '',
                    preview_image_url: media.url || '',
                  })),
                  extracted_articles: tweet.extracted_articles as
                    | Record<string, unknown>[]
                    | undefined,
                }}
                expanded={expandedTweets.has(tweet.id_str)}
                onExpand={handleTweetExpand}
              />
            ) : (
              <Card key={tweet.id_str} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-blue-600 text-sm">
                        @{tweet.author_username}
                      </span>
                      <span className="text-gray-500 text-xs">
                        {tweet.created_at &&
                          new Date(tweet.created_at).toLocaleDateString('ja-JP', {
                            month: 'short',
                            day: 'numeric',
                          })}
                      </span>
                    </div>
                    <div className="truncate text-sm text-gray-900 flex-1">{tweet.content}</div>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-500 ml-4">
                    <span>❤️ {tweet.like_count || 0}</span>
                    <span>🔄 {tweet.retweet_count || 0}</span>
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
