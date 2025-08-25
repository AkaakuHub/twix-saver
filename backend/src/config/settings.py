"""
X.com スクレイピングボットの設定管理（DB連携版）
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProxyConfig:
    """プロキシ設定"""

    server: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = False

    @property
    def is_enabled(self) -> bool:
        return self.enabled and bool(self.server)


@dataclass
class ScrapingConfig:
    """スクレイピング設定"""

    interval_minutes: int = 15
    random_delay_max_seconds: int = 120
    max_tweets_per_session: int = 100
    max_scroll_attempts: int = 50
    scroll_delay_min: float = 2.0
    scroll_delay_max: float = 5.0


@dataclass
class AntiDetectionConfig:
    """アンチ検知設定"""

    use_stealth: bool = True
    headless: bool = True
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent_rotation: bool = True

    @property
    def viewport_size(self) -> dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}


class Settings:
    """アプリケーション設定の中央管理クラス（DB連携版）"""

    def __init__(self):
        # MongoDB 設定（環境変数から取得）
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "twitter_scraper")

        # DB連携サービスは初期化後に設定される
        self._config_service = None
        self._account_service = None

        # ファイルパス設定
        self.data_dir = "data"
        self.raw_data_dir = f"{self.data_dir}/raw"
        self.processed_data_dir = f"{self.data_dir}/processed"
        self.database_dir = "database"
        self.images_dir = f"{self.database_dir}/images"
        self.logs_dir = "logs"
        self.sessions_dir = "sessions"

    def set_services(self, config_service, account_service):
        """DB連携サービスを設定"""
        self._config_service = config_service
        self._account_service = account_service

    @property
    def proxy(self) -> ProxyConfig:
        """プロキシ設定を取得（DB連携）"""
        if not self._config_service:
            return ProxyConfig()

        return ProxyConfig(
            enabled=self._config_service.get_config("proxy_enabled", False),
            server=self._config_service.get_config("proxy_server", ""),
            username=self._config_service.get_config("proxy_username", ""),
            password=self._config_service.get_config("proxy_password", ""),
        )

    @property
    def scraping(self) -> ScrapingConfig:
        """スクレイピング設定を取得（DB連携）"""
        if not self._config_service:
            return ScrapingConfig()

        return ScrapingConfig(
            interval_minutes=self._config_service.get_config("scraping_interval_minutes", 15),
            random_delay_max_seconds=self._config_service.get_config("random_delay_max_seconds", 120),
            max_tweets_per_session=self._config_service.get_config("max_tweets_per_session", 100),
        )

    @property
    def anti_detection(self) -> AntiDetectionConfig:
        """アンチ検知設定を取得（DB連携）"""
        if not self._config_service:
            return AntiDetectionConfig()

        return AntiDetectionConfig(
            headless=self._config_service.get_config("headless_mode", True),
            viewport_width=self._config_service.get_config("viewport_width", 1366),
            viewport_height=self._config_service.get_config("viewport_height", 768),
            user_agent_rotation=self._config_service.get_config("user_agent_rotation", True),
        )

    @property
    def log_level(self) -> str:
        """ログレベルを取得（DB連携）"""
        if not self._config_service:
            return "INFO"
        return self._config_service.get_config("log_level", "INFO")

    @property
    def captcha_service_api_key(self) -> Optional[str]:
        """CAPTCHA解決サービスAPIキーを取得（DB連携）"""
        if not self._config_service:
            return None

        if not self._config_service.get_config("captcha_service_enabled", False):
            return None

        return self._config_service.get_config("captcha_service_api_key", "")

    @property
    def cors_origins(self) -> list[str]:
        """CORS許可オリジンを取得（DB連携）"""
        if not self._config_service:
            return ["http://localhost:3000", "http://localhost:5173"]
        return self._config_service.get_cors_origins()

    @property
    def has_accounts(self) -> bool:
        """使用可能なTwitterアカウントがあるかチェック（DB連携）"""
        if not self._account_service:
            return False
        return len(self._account_service.get_available_accounts()) > 0

    def get_available_twitter_accounts(self):
        """使用可能なTwitterアカウント一覧を取得（DB連携）"""
        if not self._account_service:
            return []
        return self._account_service.get_available_accounts()

    @property
    def user_agents(self) -> list[str]:
        """モダンなUser-Agentのリスト"""
        return [
            # Chrome (Windows)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            # Chrome (macOS)
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            # Firefox (Windows)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            # Edge (Windows)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
            # Safari (macOS)
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        ]

    def get_proxy_config(self) -> Optional[dict[str, str]]:
        """Playwright用のプロキシ設定を取得"""
        proxy = self.proxy
        if not proxy.is_enabled:
            return None

        proxy_config = {"server": proxy.server}
        if proxy.username and proxy.password:
            proxy_config.update({"username": proxy.username, "password": proxy.password})

        return proxy_config


# グローバル設定インスタンス
settings = Settings()


# 初期化用のヘルパー関数
def initialize_settings():
    """設定システムを初期化（アプリケーション起動時に呼び出し）"""
    try:
        from src.services.account_service import twitter_account_service
        from src.services.config_service import config_service

        settings.set_services(config_service, twitter_account_service)
    except ImportError:
        # サービスがまだ利用できない場合はスキップ
        pass
