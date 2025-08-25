import { useState, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import type {
  ImageProcessingStats,
  FailedTweetsResponse,
  ImageProcessingRetryRequest,
  ImageProcessingRetryResponse,
} from '../types/api-custom'
import type { SuccessResponse } from '../types/api'

const API_BASE =
  process.env.NODE_ENV === 'production'
    ? '/api'
    : `http://localhost:${import.meta.env.VITE_BACKEND_PORT || 8000}/api`

/**
 * 画像処理管理用カスタムフック
 */
export const useImageProcessing = () => {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<ImageProcessingStats | null>(null)
  const [failedTweets, setFailedTweets] = useState<FailedTweetsResponse | null>(null)

  /**
   * 画像処理統計を取得
   */
  const fetchStats = useCallback(async (): Promise<ImageProcessingStats | null> => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/image-processing/stats`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setStats(data)
      return data
    } catch (error) {
      console.error('画像処理統計取得エラー:', error)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * 失敗ツイート一覧を取得
   */
  const fetchFailedTweets = async (limit = 10, skip = 0): Promise<FailedTweetsResponse | null> => {
    try {
      setLoading(true)
      const response = await fetch(
        `${API_BASE}/image-processing/failed-tweets?limit=${limit}&skip=${skip}`
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setFailedTweets(data)
      return data
    } catch (error) {
      console.error('失敗ツイート取得エラー:', error)
      toast.error('失敗ツイートの取得に失敗しました')
      return null
    } finally {
      setLoading(false)
    }
  }

  /**
   * 画像処理失敗分のリトライ
   */
  const retryFailed = async (maxTweets = 100): Promise<ImageProcessingRetryResponse | null> => {
    try {
      setLoading(true)
      const response = await fetch(
        `${API_BASE}/image-processing/retry-failed?max_tweets=${maxTweets}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        toast.success(data.message)
        // 統計を再取得
        await fetchStats()
        await fetchFailedTweets()
      } else {
        toast.error(data.message)
      }

      return data
    } catch (error) {
      console.error('リトライエラー:', error)
      toast.error('リトライ処理に失敗しました')
      return null
    } finally {
      setLoading(false)
    }
  }

  /**
   * 全体画像処理リトライ
   */
  const retryAll = async (
    request: ImageProcessingRetryRequest
  ): Promise<ImageProcessingRetryResponse | null> => {
    try {
      setLoading(true)

      const params = new URLSearchParams()
      if (request.max_tweets) params.append('max_tweets', request.max_tweets.toString())
      if (request.username) params.append('username', request.username)
      if (request.force_reprocess) params.append('force_reprocess', 'true')

      const response = await fetch(
        `${API_BASE}/image-processing/retry-all-image-processing?${params}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        toast.success(data.message)
        // 統計を再取得
        await fetchStats()
        await fetchFailedTweets()
      } else {
        toast.error(data.message)
      }

      return data
    } catch (error) {
      console.error('全体リトライエラー:', error)
      toast.error('全体リトライ処理に失敗しました')
      return null
    } finally {
      setLoading(false)
    }
  }

  /**
   * レガシーツイートマイグレーション
   */
  const migrateLegacyTweets = async (maxTweets = 1000): Promise<SuccessResponse | null> => {
    try {
      setLoading(true)
      const response = await fetch(
        `${API_BASE}/image-processing/migrate-legacy-tweets?max_tweets=${maxTweets}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        toast.success(data.message)
        // 統計を再取得
        await fetchStats()
      } else {
        toast.error(data.message)
      }

      return data
    } catch (error) {
      console.error('マイグレーションエラー:', error)
      toast.error('マイグレーション処理に失敗しました')
      return null
    } finally {
      setLoading(false)
    }
  }

  return {
    loading,
    stats,
    failedTweets,
    fetchStats,
    fetchFailedTweets,
    retryFailed,
    retryAll,
    migrateLegacyTweets,
  }
}
