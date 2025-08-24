import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Tweet } from '../types/api'

interface TweetState {
  tweets: Tweet[]
  filters: TweetFilters
  pagination: {
    page: number
    pageSize: number
    total: number
  }

  setTweets: (tweets: Tweet[]) => void
  addTweets: (tweets: Tweet[]) => void
  setFilters: (filters: Partial<TweetFilters>) => void
  setPagination: (pagination: Partial<TweetState['pagination']>) => void
  clearTweets: () => void
}

interface TweetFilters {
  search: string
  username: string
  dateRange: {
    start?: Date
    end?: Date
  }
  hasMedia: boolean | null
  hasArticle: boolean | null
  sortBy: 'created_at' | 'likes' | 'retweets' | 'replies'
  sortOrder: 'asc' | 'desc'
}

export const useTweetStore = create<TweetState>()(
  devtools(
    set => ({
      tweets: [],
      filters: {
        search: '',
        username: '',
        dateRange: {},
        hasMedia: null,
        hasArticle: null,
        sortBy: 'created_at',
        sortOrder: 'desc',
      },
      pagination: {
        page: 1,
        pageSize: 50,
        total: 0,
      },

      setTweets: tweets => set({ tweets }),

      addTweets: tweets =>
        set(state => ({
          tweets: [...state.tweets, ...tweets],
        })),

      setFilters: newFilters =>
        set(state => ({
          filters: { ...state.filters, ...newFilters },
          pagination: { ...state.pagination, page: 1 }, // Reset page when filters change
        })),

      setPagination: newPagination =>
        set(state => ({
          pagination: { ...state.pagination, ...newPagination },
        })),

      clearTweets: () => set({ tweets: [] }),
    }),
    {
      name: 'tweet-store',
    }
  )
)
