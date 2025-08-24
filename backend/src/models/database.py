"""
データベースモデル定義
target_users, scraping_jobs コレクション用のモデル
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict


class ScrapingJobStatus(Enum):
    """スクレイピングジョブのステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserPriority(Enum):
    """ユーザーの優先度"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TargetUser:
    """ターゲットユーザーモデル"""
    username: str
    display_name: Optional[str] = None
    active: bool = True
    priority: int = UserPriority.NORMAL.value
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
    max_tweets_per_session: Optional[int] = None
    custom_schedule: Optional[str] = None  # cron形式
    
    # メタデータ
    profile_image_url: Optional[str] = None
    follower_count: Optional[int] = None
    verified: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        # datetimeオブジェクトをISO文字列に変換
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TargetUser':
        """辞書から作成"""
        # ISO文字列をdatetimeオブジェクトに変換
        datetime_fields = ['created_at', 'updated_at', 'last_scraped_at']
        for field in datetime_fields:
            if data.get(field) and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    data[field] = None
        
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ScrapingJobStats:
    """スクレイピングジョブの統計情報"""
    tweets_collected: int = 0
    articles_extracted: int = 0
    media_downloaded: int = 0
    errors_count: int = 0
    processing_time_seconds: float = 0.0
    pages_scrolled: int = 0
    api_requests_made: int = 0


@dataclass
class ScrapingJob:
    """スクレイピングジョブモデル"""
    job_id: str
    target_usernames: List[str]
    status: str = ScrapingJobStatus.PENDING.value
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 実行情報
    scraper_account: Optional[str] = None
    proxy_used: Optional[str] = None
    user_agent: Optional[str] = None
    
    # 統計
    stats: Optional[ScrapingJobStats] = None
    
    # ログとエラー
    logs: List[str] = None
    errors: List[str] = None
    
    # 設定
    process_articles: bool = True
    max_tweets: Optional[int] = None
    
    def __post_init__(self):
        if self.stats is None:
            self.stats = ScrapingJobStats()
        if self.logs is None:
            self.logs = []
        if self.errors is None:
            self.errors = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        
        # datetime変換
        datetime_fields = ['created_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if data.get(field) and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapingJob':
        """辞書から作成"""
        # datetime変換
        datetime_fields = ['created_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if data.get(field) and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    data[field] = None
        
        # stats変換
        if data.get('stats') and isinstance(data['stats'], dict):
            data['stats'] = ScrapingJobStats(**data['stats'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def add_log(self, message: str):
        """ログエントリを追加"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
    
    def add_error(self, error: str):
        """エラーエントリを追加"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.errors.append(f"[{timestamp}] {error}")
        self.stats.errors_count += 1
    
    def start(self):
        """ジョブ開始"""
        self.status = ScrapingJobStatus.RUNNING.value
        self.started_at = datetime.utcnow()
        self.add_log("スクレイピングジョブを開始しました")
    
    def complete(self):
        """ジョブ完了"""
        self.status = ScrapingJobStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.stats.processing_time_seconds = duration
        
        self.add_log(f"スクレイピングジョブが完了しました "
                    f"(ツイート: {self.stats.tweets_collected}件, "
                    f"記事: {self.stats.articles_extracted}件)")
    
    def fail(self, error_message: str):
        """ジョブ失敗"""
        self.status = ScrapingJobStatus.FAILED.value
        self.completed_at = datetime.utcnow()
        self.add_error(error_message)


@dataclass
class SystemConfig:
    """システム設定モデル"""
    key: str
    value: Any
    description: Optional[str] = None
    category: str = "general"
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get('updated_at') and isinstance(data['updated_at'], datetime):
            data['updated_at'] = data['updated_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemConfig':
        if data.get('updated_at') and isinstance(data['updated_at'], str):
            try:
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            except ValueError:
                data['updated_at'] = None
        
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# デフォルト設定
DEFAULT_SYSTEM_CONFIGS = [
    SystemConfig(
        key="scraping_interval_minutes",
        value=15,
        description="スクレイピング実行間隔（分）",
        category="scraping"
    ),
    SystemConfig(
        key="max_concurrent_jobs",
        value=1,
        description="同時実行可能なスクレイピングジョブ数",
        category="scraping"
    ),
    SystemConfig(
        key="default_max_tweets_per_session",
        value=100,
        description="1セッションあたりのデフォルト最大ツイート数",
        category="scraping"
    ),
    SystemConfig(
        key="enable_article_extraction",
        value=True,
        description="記事抽出機能を有効にする",
        category="features"
    ),
    SystemConfig(
        key="web_ui_auto_refresh_seconds",
        value=30,
        description="WebUI自動更新間隔（秒）",
        category="ui"
    )
]