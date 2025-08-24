/**
 * 自動生成されたAPI型定義
 *
 * このファイルは scripts/simple-generate.py によって自動生成されます。
 * 手動で編集しないでください。変更は src/web/models.py で行ってください。
 *
 * 生成日時: 2025-08-24 14:19:24
 */

export interface DashboardStats {
  total_users: number
  active_users: number
  total_tweets: number
  tweets_today: number
  tweets_this_week: number
  total_articles: number
  articles_today: number
  total_jobs: number
  running_jobs: number
  completed_jobs_today: number
  failed_jobs_today: number
  last_scraping_at?: string | null
  system_status: string
  uptime_seconds: number
}

export interface ErrorResponse {
  success: boolean
  message: string
  error_code?: string | null
  details?: Record<string, unknown> | null
}

export interface JobStatistics {
  total_jobs: number
  completed_jobs: number
  failed_jobs: number
  total_tweets: number
  total_articles: number
  success_rate: number
  avg_processing_time: number
  daily_stats: Record<string, Record<string, number>>
}

export enum JobStatusEnum {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface LogMessage {
  level: string
  message: string
  timestamp: string
  source: string
}

export interface PaginatedResponse<T = unknown> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ScrapingJobCreate {
  target_usernames: string[]
  process_articles: boolean
  max_tweets?: number | null
}

export interface ScrapingJobResponse {
  job_id: string
  target_usernames: string[]
  status: string
  created_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  scraper_account?: string | null
  proxy_used?: string | null
  user_agent?: string | null
  stats: ScrapingJobStats
  logs: string[]
  errors: string[]
  process_articles: boolean
  max_tweets?: number | null
}

export interface ScrapingJobStats {
  tweets_collected: number
  articles_extracted: number
  media_downloaded: number
  errors_count: number
  processing_time_seconds: number
  pages_scrolled: number
  api_requests_made: number
}

export interface SuccessResponse {
  success: boolean
  message: string
  data?: Record<string, unknown> | null
}

export interface TargetUserCreate {
  username: string
  display_name?: string | null
  priority: number
  active: boolean
  max_tweets_per_session?: number | null
}

export interface TargetUserResponse {
  username: string
  display_name?: string | null
  active: boolean
  priority: number
  created_at?: string | null
  updated_at?: string | null
  last_scraped_at?: string | null
  total_tweets: number
  tweets_today: number
  total_articles: number
  last_error?: string | null
  scraping_enabled: boolean
  max_tweets_per_session?: number | null
  custom_schedule?: string | null
  profile_image_url?: string | null
  follower_count?: number | null
  verified?: boolean | null
}

export interface TargetUserUpdate {
  display_name?: string | null
  priority?: number | null
  active?: boolean | null
  scraping_enabled?: boolean | null
  max_tweets_per_session?: number | null
  custom_schedule?: string | null
}

export interface TweetResponse {
  id_str: string
  content: string
  author_username: string
  author_display_name?: string | null
  created_at?: string | null
  scraped_at?: string | null
  scraper_account?: string | null
  retweet_count?: number | null
  like_count?: number | null
  reply_count?: number | null
  extracted_articles?: Record<string, unknown>[] | null
  downloaded_media?: Record<string, unknown>[] | null
  hashtags?: string[] | null
  mentions?: string[] | null
}

export interface TweetSearchFilter {
  username?: string | null
  keyword?: string | null
  start_date?: string | null
  end_date?: string | null
  has_articles?: boolean | null
  has_media?: boolean | null
  limit: number
  offset: number
}

export enum UserPriorityEnum {
  LOW = '1',
  NORMAL = '2',
  HIGH = '3',
  CRITICAL = '4',
}

export interface UserStatistics {
  total_users: number
  active_users: number
  total_tweets: number
  total_articles: number
  priority_distribution: Record<string, number>
}

export interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
  timestamp: string
}

// ===== カスタム型定義と拡張 =====

export type ApiResponse<T = unknown> = (SuccessResponse & { data?: T }) | ErrorResponse

// エイリアス型定義（後方互換性）
export type TargetUser = TargetUserResponse
export type ScrapingJob = ScrapingJobResponse
export type Tweet = TweetResponse

// 型の名前を統一（既存コードとの互換性）
export const JobStatus = JobStatusEnum
export type JobStatus = JobStatusEnum

export const UserPriority = UserPriorityEnum
export type UserPriority = UserPriorityEnum

// 優先度表示用ラベルとカラー
export const UserPriorityLabels = {
  [UserPriorityEnum.LOW]: '低',
  [UserPriorityEnum.NORMAL]: '標準',
  [UserPriorityEnum.HIGH]: '高',
  [UserPriorityEnum.CRITICAL]: '緊急',
} as const

export const UserPriorityColors = {
  [UserPriorityEnum.LOW]: 'text-gray-500',
  [UserPriorityEnum.NORMAL]: 'text-blue-500',
  [UserPriorityEnum.HIGH]: 'text-yellow-500',
  [UserPriorityEnum.CRITICAL]: 'text-red-500',
} as const

// ジョブステータス表示用ラベルとカラー
export const JobStatusLabels = {
  [JobStatusEnum.PENDING]: '待機中',
  [JobStatusEnum.RUNNING]: '実行中',
  [JobStatusEnum.COMPLETED]: '完了',
  [JobStatusEnum.FAILED]: '失敗',
  [JobStatusEnum.CANCELLED]: 'キャンセル',
} as const

export const JobStatusColors = {
  [JobStatusEnum.PENDING]: 'text-yellow-500 bg-yellow-50',
  [JobStatusEnum.RUNNING]: 'text-blue-500 bg-blue-50',
  [JobStatusEnum.COMPLETED]: 'text-green-500 bg-green-50',
  [JobStatusEnum.FAILED]: 'text-red-500 bg-red-50',
  [JobStatusEnum.CANCELLED]: 'text-gray-500 bg-gray-50',
} as const

// ===== 拡張型定義 =====

// システム状態
export interface SystemStatus {
  overall_status: 'healthy' | 'warning' | 'critical'
  health_score: number
  services: {
    database: {
      status: 'connected' | 'disconnected'
      collections: {
        tweets: number
        target_users: number
        scraping_jobs: number
      }
    }
    scraping: {
      running_jobs: number
      active_users: number
    }
    websocket: {
      active_connections: number
    }
  }
  timestamp: string
}

// WebSocketメッセージタイプ
export interface JobUpdateMessage {
  job_id: string
  status: JobStatusEnum
  stats?: ScrapingJobStats
  timestamp: string
}

export interface SystemStatsMessage {
  users: {
    total: number
    active: number
  }
  tweets: {
    total: number
  }
  jobs: {
    running: number
    completed_today: number
    failed_today: number
  }
  timestamp: string
}

// ===== APIエラークラス =====

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ===== ユーティリティ型 =====

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>

// ジェネリック ページネーション（エイリアス）
export type PaginatedList<T> = PaginatedResponse<T>
