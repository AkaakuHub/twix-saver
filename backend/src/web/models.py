"""
FastAPI用のPydanticモデル定義
API リクエスト・レスポンスの型安全性を保証
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserPriorityEnum(str, Enum):
    """ユーザー優先度"""

    LOW = "1"
    NORMAL = "2"
    HIGH = "3"
    CRITICAL = "4"


class JobStatusEnum(str, Enum):
    """ジョブステータス"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ===== ユーザー関連モデル =====


class TargetUserCreate(BaseModel):
    """ターゲットユーザー作成リクエスト"""

    username: str = Field(..., min_length=1, max_length=50, description="Twitterユーザー名")
    display_name: Optional[str] = Field(None, max_length=100, description="表示名")
    priority: int = Field(2, ge=1, le=4, description="優先度 (1:低, 2:標準, 3:高, 4:緊急)")
    active: bool = Field(True, description="有効状態")
    scraping_interval_minutes: int = Field(30, ge=15, le=1440, description="実行間隔（分）")
    max_tweets_per_session: Optional[int] = Field(None, gt=0, le=1000, description="1セッションあたり最大ツイート数")


class TargetUserUpdate(BaseModel):
    """ターゲットユーザー更新リクエスト"""

    display_name: Optional[str] = Field(None, max_length=100)
    priority: Optional[int] = Field(None, ge=1, le=4)
    active: Optional[bool] = None
    scraping_enabled: Optional[bool] = None
    scraping_interval_minutes: Optional[int] = Field(None, ge=15, le=1440, description="実行間隔（分）")
    max_tweets_per_session: Optional[int] = Field(None, gt=0, le=1000)


class TargetUserResponse(BaseModel):
    """ターゲットユーザーレスポンス"""

    model_config = ConfigDict(from_attributes=True)

    username: str
    display_name: Optional[str] = None
    active: bool
    priority: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_scraped_at: Optional[datetime] = None

    # 統計情報
    total_tweets: int = 0
    tweets_today: int = 0
    total_articles: int = 0
    last_error: Optional[str] = None

    # 設定
    scraping_enabled: bool = True
    scraping_interval_minutes: int = 30
    max_tweets_per_session: Optional[int] = None

    # メタデータ
    profile_image_url: Optional[str] = None
    follower_count: Optional[int] = None
    verified: Optional[bool] = None


# ===== ジョブ関連モデル =====


class ScrapingJobStats(BaseModel):
    """スクレイピングジョブ統計"""

    tweets_collected: int = 0
    articles_extracted: int = 0
    media_downloaded: int = 0
    errors_count: int = 0
    processing_time_seconds: float = 0.0
    pages_scrolled: int = 0
    api_requests_made: int = 0


class ScrapingJobCreate(BaseModel):
    """スクレイピングジョブ作成リクエスト"""

    target_usernames: list[str] = Field(..., min_length=1, description="対象ユーザー名リスト")
    process_articles: bool = Field(True, description="記事抽出を実行するか")
    max_tweets: Optional[int] = Field(None, gt=0, le=1000, description="最大ツイート数")
    scraper_account: Optional[str] = Field(None, description="使用するスクレイパーアカウント")


class ScrapingJobResponse(BaseModel):
    """スクレイピングジョブレスポンス"""

    model_config = ConfigDict(from_attributes=True)

    job_id: str
    target_usernames: list[str]
    status: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 実行情報
    scraper_account: Optional[str] = None
    proxy_used: Optional[str] = None
    user_agent: Optional[str] = None

    # 統計
    stats: ScrapingJobStats = Field(default_factory=ScrapingJobStats)

    # ログとエラー
    logs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # 設定
    process_articles: bool = True
    max_tweets: Optional[int] = None


# ===== ツイート関連モデル =====


class TweetSearchFilter(BaseModel):
    """ツイート検索フィルター"""

    username: Optional[str] = Field(None, description="特定ユーザーのツイートのみ")
    keyword: Optional[str] = Field(None, min_length=1, description="検索キーワード")
    start_date: Optional[datetime] = Field(None, description="開始日時")
    end_date: Optional[datetime] = Field(None, description="終了日時")
    has_articles: Optional[bool] = Field(None, description="記事リンクありのみ")
    has_media: Optional[bool] = Field(None, description="メディアありのみ")
    limit: int = Field(20, ge=1, le=100, description="取得件数")
    offset: int = Field(0, ge=0, description="オフセット")


class TweetResponse(BaseModel):
    """ツイートレスポンス"""

    model_config = ConfigDict(from_attributes=True)

    id_str: str
    content: str
    author_username: str
    author_display_name: Optional[str] = None
    created_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    scraper_account: Optional[str] = None

    # エンゲージメント情報
    retweet_count: Optional[int] = None
    like_count: Optional[int] = None
    reply_count: Optional[int] = None

    # リンクコンテンツ
    extracted_articles: Optional[list[dict[str, Any]]] = None
    downloaded_media: Optional[list[dict[str, Any]]] = None

    # ハッシュタグとメンション
    hashtags: Optional[list[str]] = None
    mentions: Optional[list[str]] = None


# ===== 統計関連モデル =====


class DashboardStats(BaseModel):
    """ダッシュボード統計情報"""

    # ユーザー統計
    total_users: int = 0
    active_users: int = 0

    # ツイート統計
    total_tweets: int = 0
    tweets_today: int = 0
    tweets_this_week: int = 0

    # 記事統計
    total_articles: int = 0
    articles_today: int = 0

    # ジョブ統計
    total_jobs: int = 0
    running_jobs: int = 0
    completed_jobs_today: int = 0
    failed_jobs_today: int = 0

    # システム情報
    last_scraping_at: Optional[datetime] = None
    system_status: str = "idle"  # idle, running, error
    uptime_seconds: float = 0.0


class UserStatistics(BaseModel):
    """ユーザー統計"""

    total_users: int
    active_users: int
    total_tweets: int
    total_articles: int
    priority_distribution: dict[str, int]


class JobStatistics(BaseModel):
    """ジョブ統計"""

    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_tweets: int
    total_articles: int
    success_rate: float
    avg_processing_time: float
    daily_stats: dict[str, dict[str, int]]


# ===== WebSocket関連モデル =====


class WebSocketMessage(BaseModel):
    """WebSocketメッセージ"""

    type: str = Field(..., description="メッセージタイプ")
    data: dict[str, Any] = Field(default_factory=dict, description="メッセージデータ")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


class LogMessage(BaseModel):
    """ログメッセージ"""

    level: str = Field(..., description="ログレベル (DEBUG, INFO, WARNING, ERROR)")
    message: str = Field(..., description="ログメッセージ")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field("system", description="ログソース")


# ===== 汎用レスポンスモデル =====


class SuccessResponse(BaseModel):
    """成功レスポンス"""

    success: bool = True
    message: str = "操作が正常に完了しました"
    data: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """エラーレスポンス"""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    """ページネーション付きレスポンス"""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False
