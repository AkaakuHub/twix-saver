/**
 * カスタム型定義とユーティリティ型
 *
 * このファイルには手動で定義したカスタム型を含めます。
 * 基本的なAPI型定義は ./api.ts をimportして使用してください。
 */

import {
  SuccessResponse,
  ErrorResponse,
  JobStatusEnum,
  UserPriorityEnum,
  ScrapingJobResponse,
  TargetUserResponse,
  TweetResponse,
  ScrapingJobStats,
  PaginatedResponse,
} from './api'

// ===== カスタム型定義と拡張 =====

export type ApiResponse<T = unknown> = (SuccessResponse & { data?: T }) | ErrorResponse

// エイリアス型定義（後方互換性）
export type TargetUser = TargetUserResponse
export type ScrapingJob = ScrapingJobResponse
export type Tweet = TweetResponse

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

// ===== ユーティリティ型 =====

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>

// ジェネリック ページネーション（エイリアス）
export type PaginatedList<T> = PaginatedResponse<T>

// ===== 画像処理関連の型定義 =====

export enum ImageProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

export interface ImageProcessingStats {
  total_tweets: number
  image_processing_stats: {
    pending: number
    processing: number
    completed: number
    failed: number
    skipped: number
    no_status: number
  }
  success_rate: number
}

export interface FailedTweet {
  id_str: string
  author_username: string
  image_processing_error?: string | null
  image_processing_retry_count?: number
  image_processing_attempted_at?: string | null
}

export interface FailedTweetsResponse {
  failed_tweets: FailedTweet[]
  total_failed: number
  limit: number
  skip: number
}

export interface ImageProcessingRetryRequest {
  max_tweets?: number
  username?: string
  force_reprocess?: boolean
}

export interface ImageProcessingRetryResponse {
  success: boolean
  message: string
  data: {
    processed_count: number
    success_count: number
    failed_count?: number
    retry_count?: number
    username?: string | null
    force_reprocess?: boolean
    filter?: string
  }
}
