import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { useAppStore } from '../stores/appStore'

interface RawTweet {
  id_str?: string
  id?: string
  content?: string
  like_count?: number
  retweet_count?: number
  reply_count?: number
  author_username?: string
  author_display_name?: string
  downloaded_media?: Array<{
    media_id: string
    original_url: string
    type: 'photo' | 'linked_image'
    mime_type: string
    size: number
    local_url?: string
    position?: number
    order_type?: 'attachment' | 'link'
  }>
  created_at?: string
  scraped_at?: string
  extracted_articles?: Array<Record<string, unknown>>
  [key: string]: unknown
}

import { API_BASE } from '../config/env'

interface TweetSearchParams {
  search?: string
  username?: string
  start_date?: string
  end_date?: string
  has_media?: boolean
  has_articles?: boolean
  min_engagement?: number
  hashtags?: string
  sort_by?: 'date' | 'engagement' | 'relevance'
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export const useTweets = (params: TweetSearchParams = {}) => {
  const buildQueryParams = (pageParam: number = 1) => {
    const queryParams = new URLSearchParams()
    const searchParams = { ...params, page: pageParam }

    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, value.toString())
      }
    })
    return queryParams
  }

  const { data, isLoading, error, refetch, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ['tweets', params],
      queryFn: async ({ pageParam = 1 }) => {
        try {
          const queryParams = buildQueryParams(pageParam as number)
          const response = await fetch(`${API_BASE}/tweets?${queryParams.toString()}`)

          if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`ツイートデータの取得に失敗しました: ${errorText}`)
          }

          const result = await response.json()

          // 配列が直接返される場合と、オブジェクト内に配列がある場合に対応
          if (Array.isArray(result)) {
            // APIレスポンスをフロントエンド形式にマッピング
            const mappedTweets = result.map((tweet: RawTweet) => ({
              ...tweet,
              id: tweet.id_str || tweet.id || '',
              public_metrics: {
                like_count: tweet.like_count || 0,
                retweet_count: tweet.retweet_count || 0,
                reply_count: tweet.reply_count || 0,
                quote_count: 0,
              },
              author: {
                username: tweet.author_username || '',
                display_name: tweet.author_display_name || '',
              },
              text: tweet.content || '',
              created_at: tweet.created_at,
              scraped_at: tweet.scraped_at,
              downloaded_media: tweet.downloaded_media,
              extracted_articles: tweet.extracted_articles,
            }))

            return {
              tweets: mappedTweets,
              total: mappedTweets.length,
              page: pageParam as number,
              hasMore: false, // 単一ページの場合
            }
          } else {
            // オブジェクト形式の場合
            const objectResult = result as {
              tweets?: RawTweet[]
              data?: RawTweet[]
              total?: number
              has_more?: boolean
            }

            const rawTweets = objectResult.tweets || objectResult.data || []
            const mappedTweets = rawTweets.map((tweet: RawTweet) => ({
              ...tweet,
              id: tweet.id_str || tweet.id || '',
              public_metrics: {
                like_count: tweet.like_count || 0,
                retweet_count: tweet.retweet_count || 0,
                reply_count: tweet.reply_count || 0,
                quote_count: 0,
              },
              author: {
                username: tweet.author_username || '',
                display_name: tweet.author_display_name || '',
              },
              text: tweet.content || '',
              created_at: tweet.created_at,
              scraped_at: tweet.scraped_at,
              downloaded_media: tweet.downloaded_media,
              extracted_articles: tweet.extracted_articles,
            }))

            return {
              tweets: mappedTweets,
              total: objectResult.total || 0,
              page: pageParam as number,
              hasMore: objectResult.has_more || false,
            }
          }
        } catch (error) {
          if (error instanceof TypeError && error.message.includes('fetch')) {
            throw new Error(
              'バックエンドサーバーに接続できません。サーバーが起動していることを確認してください。'
            )
          }
          throw error
        }
      },
      getNextPageParam: lastPage => {
        return lastPage.hasMore ? lastPage.page + 1 : undefined
      },
      initialPageParam: 1,
      staleTime: Infinity, // 手動更新のみ
      refetchOnWindowFocus: false,
    })

  // 全ページのツイートを結合してcreated_atで降順ソート（新しい順）
  const tweets =
    data?.pages
      .flatMap(page => page.tweets)
      .sort((a, b) => {
        const dateA = new Date(a.created_at || 0).getTime()
        const dateB = new Date(b.created_at || 0).getTime()
        return dateB - dateA // 降順（新しい順）
      }) || []
  const total = data?.pages[0]?.total || 0
  const hasMore = data?.pages[data?.pages.length - 1]?.hasMore || false

  const loadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }

  return {
    tweets,
    total,
    isLoading,
    error: error?.message || null,
    refetch,
    loadMore,
    hasMore,
    isFetchingNextPage,
  }
}

export const useTweetStats = () => {
  return useQuery({
    queryKey: ['tweet-stats'],
    queryFn: async () => {
      try {
        const response = await fetch(`${API_BASE}/tweets/stats`)
        if (!response.ok) {
          throw new Error('ツイート統計の取得に失敗しました')
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

export const useTweetManagement = () => {
  const { addNotification } = useAppStore()
  const queryClient = useQueryClient()

  // 単体ツイート削除
  const deleteTweetMutation = useMutation({
    mutationFn: async (tweetId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/tweets/${tweetId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ツイートの削除に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tweets'] })
      queryClient.invalidateQueries({ queryKey: ['tweet-stats'] })
      addNotification({
        type: 'success',
        title: 'ツイートを削除しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ツイート削除エラー',
        message: error.message,
      })
    },
  })

  // 一括削除
  const deleteTweetsBulkMutation = useMutation({
    mutationFn: async (tweetIds: string[]): Promise<void> => {
      const response = await fetch(`${API_BASE}/tweets/bulk`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tweet_ids: tweetIds }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '一括削除に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tweets'] })
      queryClient.invalidateQueries({ queryKey: ['tweet-stats'] })
      addNotification({
        type: 'success',
        title: '選択したツイートを削除しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: '一括削除エラー',
        message: error.message,
      })
    },
  })

  // 全ツイート再取得
  const refreshAllTweetsMutation = useMutation({
    mutationFn: async (): Promise<void> => {
      const response = await fetch(`${API_BASE}/tweets/refresh`, {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ツイート再取得に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tweets'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      addNotification({
        type: 'success',
        title: 'ツイート再取得ジョブを開始しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ツイート再取得エラー',
        message: error.message,
      })
    },
  })

  // ユーザー別ツイート再取得
  const refreshUserTweetsMutation = useMutation({
    mutationFn: async (username: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/tweets/refresh/${username}`, {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ユーザーツイート再取得に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tweets'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      addNotification({
        type: 'success',
        title: 'ユーザーツイート再取得ジョブを開始しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ユーザーツイート再取得エラー',
        message: error.message,
      })
    },
  })

  // 特定ツイート再取得
  const refreshTweetMutation = useMutation({
    mutationFn: async (tweetId: string): Promise<void> => {
      const response = await fetch(`${API_BASE}/tweets/refresh/tweet/${tweetId}`, {
        method: 'POST',
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'ツイート再取得に失敗しました')
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tweets'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      addNotification({
        type: 'success',
        title: 'ツイート再取得ジョブを開始しました',
      })
    },
    onError: (error: Error) => {
      addNotification({
        type: 'error',
        title: 'ツイート再取得エラー',
        message: error.message,
      })
    },
  })

  return {
    deleteTweet: deleteTweetMutation.mutate,
    deleteTweetsBulk: deleteTweetsBulkMutation.mutate,
    refreshAllTweets: refreshAllTweetsMutation.mutate,
    refreshUserTweets: refreshUserTweetsMutation.mutate,
    refreshTweet: refreshTweetMutation.mutate,
    isDeleting: deleteTweetMutation.isPending,
    isDeletingBulk: deleteTweetsBulkMutation.isPending,
    isRefreshing: refreshAllTweetsMutation.isPending,
    isRefreshingUser: refreshUserTweetsMutation.isPending,
    isRefreshingTweet: refreshTweetMutation.isPending,
  }
}
