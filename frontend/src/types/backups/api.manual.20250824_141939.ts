/**
 * API型定義
 * FastAPIバックエンドとの型安全な通信を保証
 */

export interface SuccessResponse<T = any> {
  success: true;
  message: string;
  data?: T;
}

export interface ErrorResponse {
  success: false;
  message: string;
  error_code?: string;
  details?: Record<string, any>;
}

export type ApiResponse<T = any> = SuccessResponse<T> | ErrorResponse;

// ===== ユーザー関連 =====

export enum UserPriority {
  LOW = 1,
  NORMAL = 2,
  HIGH = 3,
  CRITICAL = 4,
}

export const UserPriorityLabels = {
  [UserPriority.LOW]: '低',
  [UserPriority.NORMAL]: '標準',
  [UserPriority.HIGH]: '高',
  [UserPriority.CRITICAL]: '緊急',
} as const;

export const UserPriorityColors = {
  [UserPriority.LOW]: 'text-gray-500',
  [UserPriority.NORMAL]: 'text-blue-500',
  [UserPriority.HIGH]: 'text-yellow-500',
  [UserPriority.CRITICAL]: 'text-red-500',
} as const;

export interface TargetUser {
  username: string;
  display_name?: string;
  active: boolean;
  priority: UserPriority;
  created_at?: string;
  updated_at?: string;
  last_scraped_at?: string;
  
  // 統計情報
  total_tweets: number;
  tweets_today: number;
  total_articles: number;
  last_error?: string;
  
  // 設定
  scraping_enabled: boolean;
  max_tweets_per_session?: number;
  custom_schedule?: string;
  
  // メタデータ
  profile_image_url?: string;
  follower_count?: number;
  verified?: boolean;
}

export interface TargetUserCreate {
  username: string;
  display_name?: string;
  priority?: UserPriority;
  active?: boolean;
  max_tweets_per_session?: number;
}

export interface TargetUserUpdate {
  display_name?: string;
  priority?: UserPriority;
  active?: boolean;
  scraping_enabled?: boolean;
  max_tweets_per_session?: number;
  custom_schedule?: string;
}

export interface UserStatistics {
  total_users: number;
  active_users: number;
  total_tweets: number;
  total_articles: number;
  priority_distribution: Record<string, number>;
}

// ===== ジョブ関連 =====

export enum JobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export const JobStatusLabels = {
  [JobStatus.PENDING]: '待機中',
  [JobStatus.RUNNING]: '実行中',
  [JobStatus.COMPLETED]: '完了',
  [JobStatus.FAILED]: '失敗',
  [JobStatus.CANCELLED]: 'キャンセル',
} as const;

export const JobStatusColors = {
  [JobStatus.PENDING]: 'text-yellow-500 bg-yellow-50',
  [JobStatus.RUNNING]: 'text-blue-500 bg-blue-50',
  [JobStatus.COMPLETED]: 'text-green-500 bg-green-50',
  [JobStatus.FAILED]: 'text-red-500 bg-red-50',
  [JobStatus.CANCELLED]: 'text-gray-500 bg-gray-50',
} as const;

export interface ScrapingJobStats {
  tweets_collected: number;
  articles_extracted: number;
  media_downloaded: number;
  errors_count: number;
  processing_time_seconds: number;
  pages_scrolled: number;
  api_requests_made: number;
}

export interface ScrapingJob {
  job_id: string;
  target_usernames: string[];
  status: JobStatus;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  
  // 実行情報
  scraper_account?: string;
  proxy_used?: string;
  user_agent?: string;
  
  // 統計
  stats: ScrapingJobStats;
  
  // ログとエラー
  logs: string[];
  errors: string[];
  
  // 設定
  process_articles: boolean;
  max_tweets?: number;
}

export interface ScrapingJobCreate {
  target_usernames: string[];
  process_articles?: boolean;
  max_tweets?: number;
}

export interface JobStatistics {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_tweets: number;
  total_articles: number;
  success_rate: number;
  avg_processing_time: number;
  daily_stats: Record<string, { jobs: number; tweets: number }>;
}

// ===== ツイート関連 =====

export interface Tweet {
  id_str: string;
  content: string;
  author_username: string;
  author_display_name?: string;
  created_at?: string;
  scraped_at?: string;
  scraper_account?: string;
  
  // エンゲージメント情報
  retweet_count?: number;
  like_count?: number;
  reply_count?: number;
  
  // リンクコンテンツ
  extracted_articles?: Array<{
    url: string;
    title: string;
    content: string;
    text_content: string;
    retrieved_at: string;
  }>;
  downloaded_media?: Array<{
    url: string;
    filepath: string;
    content_type: string;
    file_size: number;
  }>;
  
  // ハッシュタグとメンション
  hashtags?: string[];
  mentions?: string[];
}

export interface TweetSearchFilter {
  username?: string;
  keyword?: string;
  start_date?: string;
  end_date?: string;
  has_articles?: boolean;
  has_media?: boolean;
  limit?: number;
  offset?: number;
}

export interface TweetStatistics {
  total_tweets: number;
  tweets_today: number;
  tweets_this_week: number;
  tweets_with_articles: number;
  tweets_with_media: number;
  latest_scraped_at?: string;
  top_users: Array<{
    username: string;
    tweet_count: number;
  }>;
}

// ===== ダッシュボード関連 =====

export interface DashboardStats {
  // ユーザー統計
  total_users: number;
  active_users: number;
  
  // ツイート統計
  total_tweets: number;
  tweets_today: number;
  tweets_this_week: number;
  
  // 記事統計
  total_articles: number;
  articles_today: number;
  
  // ジョブ統計
  total_jobs: number;
  running_jobs: number;
  completed_jobs_today: number;
  failed_jobs_today: number;
  
  // システム情報
  last_scraping_at?: string;
  system_status: 'idle' | 'running' | 'error';
  uptime_seconds: number;
}

export interface SystemStatus {
  overall_status: 'healthy' | 'warning' | 'critical';
  health_score: number;
  services: {
    database: {
      status: 'connected' | 'disconnected';
      collections: {
        tweets: number;
        target_users: number;
        scraping_jobs: number;
      };
    };
    scraping: {
      running_jobs: number;
      active_users: number;
    };
    websocket: {
      active_connections: number;
    };
  };
  timestamp: string;
}

// ===== WebSocket関連 =====

export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface LogMessage {
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  timestamp: string;
  source: string;
}

export interface JobUpdateMessage {
  job_id: string;
  status: JobStatus;
  stats?: ScrapingJobStats;
  timestamp: string;
}

export interface SystemStatsMessage {
  users: {
    total: number;
    active: number;
  };
  tweets: {
    total: number;
  };
  jobs: {
    running: number;
    completed_today: number;
    failed_today: number;
  };
  timestamp: string;
}

// ===== ページネーション =====

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ===== API エラー =====

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}