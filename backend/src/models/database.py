"""
データベースモデル定義
target_users, scraping_jobs コレクション用のモデル
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib


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


class TwitterAccountStatus(Enum):
    """Twitterアカウントのステータス"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    RATE_LIMITED = "rate_limited"
    LOGIN_FAILED = "login_failed"


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
class TwitterAccount:
    """Twitterアカウントモデル（スクレイピング用）"""
    account_id: str  # 一意のID
    username: str    # @username
    email: str
    password_encrypted: str  # 暗号化されたパスワード（復号化可能）
    display_name: Optional[str] = None
    
    # ステータス
    status: str = TwitterAccountStatus.ACTIVE.value
    active: bool = True
    
    # 使用状況統計
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    total_jobs_run: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    
    # レート制限情報
    rate_limit_until: Optional[datetime] = None
    rate_limit_count: int = 0
    
    # セキュリティ
    login_attempts: int = 0
    last_login_failure: Optional[datetime] = None
    
    # 設定
    priority: int = UserPriority.NORMAL.value
    max_concurrent_usage: int = 1
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def update_password(self, new_password: str):
        """パスワード更新"""
        from src.utils.encryption import encrypt_password
        self.password_encrypted = encrypt_password(new_password)
        self.updated_at = datetime.utcnow()
    
    def get_password_for_scraping(self) -> str:
        """スクレイピング用の平文パスワードを取得（復号化）"""
        from src.utils.encryption import decrypt_password
        return decrypt_password(self.password_encrypted)
    
    def mark_used(self):
        """使用記録更新"""
        self.last_used_at = datetime.utcnow()
        self.total_jobs_run += 1
    
    def mark_job_success(self):
        """ジョブ成功記録"""
        self.successful_jobs += 1
        self.login_attempts = 0  # ログイン試行回数リセット
        if self.status == TwitterAccountStatus.LOGIN_FAILED.value:
            self.status = TwitterAccountStatus.ACTIVE.value
    
    def mark_job_failure(self, error_type: str = None):
        """ジョブ失敗記録"""
        self.failed_jobs += 1
        if error_type == "login_failed":
            self.login_attempts += 1
            self.last_login_failure = datetime.utcnow()
            if self.login_attempts >= 3:
                self.status = TwitterAccountStatus.LOGIN_FAILED.value
                self.active = False
    
    def set_rate_limited(self, until: Optional[datetime] = None):
        """レート制限設定"""
        self.status = TwitterAccountStatus.RATE_LIMITED.value
        self.rate_limit_until = until or datetime.utcnow()
        self.rate_limit_count += 1
    
    def is_available(self) -> bool:
        """使用可能かチェック"""
        if not self.active:
            return False
        if self.status in [TwitterAccountStatus.SUSPENDED.value, TwitterAccountStatus.LOGIN_FAILED.value]:
            return False
        if self.rate_limit_until and datetime.utcnow() < self.rate_limit_until:
            return False
        return True
    
    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        
        # 暗号化パスワードを除外（セキュリティ）
        if not include_password:
            data.pop('password_encrypted', None)
        
        # datetime変換
        datetime_fields = ['created_at', 'updated_at', 'last_used_at', 'rate_limit_until', 'last_login_failure']
        for field in datetime_fields:
            if data.get(field) and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TwitterAccount':
        """辞書から作成"""
        # datetime変換
        datetime_fields = ['created_at', 'updated_at', 'last_used_at', 'rate_limit_until', 'last_login_failure']
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
    specific_tweet_ids: Optional[List[str]] = None
    
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
        jst = timezone(timedelta(hours=9))
        timestamp = datetime.now(jst).strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
    
    def add_error(self, error: str):
        """エラーエントリを追加"""
        jst = timezone(timedelta(hours=9))
        timestamp = datetime.now(jst).strftime("%H:%M:%S")
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
    # スクレイピング設定
    SystemConfig(
        key="scraping_interval_minutes",
        value=15,
        description="スクレイピング実行間隔（分）",
        category="scraping"
    ),
    SystemConfig(
        key="random_delay_max_seconds",
        value=120,
        description="ランダム遅延最大値（秒）",
        category="scraping"
    ),
    SystemConfig(
        key="max_tweets_per_session",
        value=100,
        description="1セッションあたりの最大ツイート数",
        category="scraping"
    ),
    SystemConfig(
        key="max_concurrent_jobs",
        value=1,
        description="同時実行可能なスクレイピングジョブ数",
        category="scraping"
    ),
    
    # アンチ検知設定
    SystemConfig(
        key="headless_mode",
        value=True,
        description="ヘッドレスモード（ブラウザを非表示）",
        category="anti_detection"
    ),
    SystemConfig(
        key="viewport_width",
        value=1366,
        description="ブラウザビューポート幅",
        category="anti_detection"
    ),
    SystemConfig(
        key="viewport_height",
        value=768,
        description="ブラウザビューポート高さ",
        category="anti_detection"
    ),
    SystemConfig(
        key="user_agent_rotation",
        value=True,
        description="User-Agent ローテーション",
        category="anti_detection"
    ),
    
    # プロキシ設定
    SystemConfig(
        key="proxy_enabled",
        value=False,
        description="プロキシを使用する",
        category="proxy"
    ),
    SystemConfig(
        key="proxy_server",
        value="",
        description="プロキシサーバー (host:port)",
        category="proxy"
    ),
    SystemConfig(
        key="proxy_username",
        value="",
        description="プロキシ認証ユーザー名",
        category="proxy"
    ),
    SystemConfig(
        key="proxy_password",
        value="",
        description="プロキシ認証パスワード",
        category="proxy"
    ),
    
    # ログ設定
    SystemConfig(
        key="log_level",
        value="INFO",
        description="ログレベル (DEBUG, INFO, WARNING, ERROR)",
        category="logging"
    ),
    
    # CAPTCHA設定
    SystemConfig(
        key="captcha_service_enabled",
        value=False,
        description="CAPTCHA解決サービスを使用する",
        category="captcha"
    ),
    SystemConfig(
        key="captcha_service_api_key",
        value="",
        description="CAPTCHA解決サービスAPIキー",
        category="captcha"
    ),
    
    # 機能設定
    SystemConfig(
        key="enable_article_extraction",
        value=True,
        description="記事抽出機能を有効にする",
        category="features"
    ),
    
    # UI設定
    SystemConfig(
        key="web_ui_auto_refresh_seconds",
        value=30,
        description="WebUI自動更新間隔（秒）",
        category="ui"
    ),
    SystemConfig(
        key="cors_origins",
        value="http://localhost:3000,http://localhost:5173",
        description="CORS許可オリジン（カンマ区切り）",
        category="ui"
    )
]