"""
X.com スクレイピングボットの設定管理
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProxyConfig:
    """プロキシ設定"""
    server: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    @property
    def is_enabled(self) -> bool:
        return bool(self.server)


@dataclass
class TwitterAccount:
    """Twitter アカウント情報"""
    username: str
    password: str
    email: str


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
    def viewport_size(self) -> Dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}


class Settings:
    """アプリケーション設定の中央管理クラス"""
    
    def __init__(self):
        # MongoDB 設定
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "twitter_scraper")
        
        # プロキシ設定
        self.proxy = ProxyConfig(
            server=os.getenv("PROXY_SERVER"),
            username=os.getenv("PROXY_USERNAME"),
            password=os.getenv("PROXY_PASSWORD")
        )
        
        # Twitter アカウント設定
        self._load_twitter_accounts()
        
        # CAPTCHA 解決サービス
        self.captcha_service_api_key = os.getenv("CAPTCHA_SERVICE_API_KEY")
        
        # スクレイピング設定
        self.scraping = ScrapingConfig(
            interval_minutes=int(os.getenv("SCRAPING_INTERVAL_MINUTES", "15")),
            random_delay_max_seconds=int(os.getenv("RANDOM_DELAY_MAX_SECONDS", "120")),
            max_tweets_per_session=int(os.getenv("MAX_TWEETS_PER_SESSION", "100"))
        )
        
        # アンチ検知設定
        self.anti_detection = AntiDetectionConfig(
            headless=os.getenv("HEADLESS", "true").lower() == "true"
        )
        
        # ログ設定
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # ファイルパス設定
        self.data_dir = "data"
        self.raw_data_dir = f"{self.data_dir}/raw"
        self.processed_data_dir = f"{self.data_dir}/processed"
        self.logs_dir = "logs"
        self.sessions_dir = "sessions"
    
    def _load_twitter_accounts(self):
        """環境変数からTwitterアカウント情報を読み込み"""
        # 単一アカウント（基本設定）
        username = os.getenv("TWITTER_USERNAME")
        password = os.getenv("TWITTER_PASSWORD")
        email = os.getenv("TWITTER_EMAIL")
        
        if username and password and email:
            self.twitter_accounts = [TwitterAccount(username, password, email)]
        else:
            self.twitter_accounts = []
        
        # 複数アカウント対応（アカウントプール）
        # TWITTER_ACCOUNT_1_USERNAME, TWITTER_ACCOUNT_1_PASSWORD, ... の形式
        account_index = 1
        while True:
            acc_username = os.getenv(f"TWITTER_ACCOUNT_{account_index}_USERNAME")
            acc_password = os.getenv(f"TWITTER_ACCOUNT_{account_index}_PASSWORD")
            acc_email = os.getenv(f"TWITTER_ACCOUNT_{account_index}_EMAIL")
            
            if not all([acc_username, acc_password, acc_email]):
                break
            
            self.twitter_accounts.append(TwitterAccount(acc_username, acc_password, acc_email))
            account_index += 1
    
    @property
    def has_accounts(self) -> bool:
        """使用可能なTwitterアカウントがあるかチェック"""
        return len(self.twitter_accounts) > 0
    
    @property
    def user_agents(self) -> List[str]:
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
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
        ]
    
    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Playwright用のプロキシ設定を取得"""
        if not self.proxy.is_enabled:
            return None
        
        proxy_config = {"server": self.proxy.server}
        if self.proxy.username and self.proxy.password:
            proxy_config.update({
                "username": self.proxy.username,
                "password": self.proxy.password
            })
        
        return proxy_config


# グローバル設定インスタンス
settings = Settings()