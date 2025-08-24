import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import type { TweetResponse } from '../types/api'

const API_BASE = 'http://localhost:8000/api'

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

          const result = (await response.json()) as {
            tweets?: TweetResponse[]
            data?: TweetResponse[]
            total?: number
            has_more?: boolean
          }
          return {
            tweets: result.tweets || result.data || [],
            total: result.total || 0,
            page: pageParam as number,
            hasMore: result.has_more || false,
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

  // 全ページのツイートを結合
  const tweets = data?.pages.flatMap(page => page.tweets) || []
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
