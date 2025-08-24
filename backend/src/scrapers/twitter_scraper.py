"""
Playwright ベースの X.com スクレイピングエンジン
"""

import json
import random
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from playwright.async_api import async_playwright, BrowserContext, Page, Response
from playwright_stealth import stealth

from src.config.settings import settings
from src.models.database import TwitterAccount
from src.utils.logger import setup_logger, log_performance


class TwitterScraper:
    """
    X.com スクレイピングエンジン
    ネットワーク傍受とアンチ検知機能を備えた堅牢なスクレイパー
    """
    
    def __init__(self, account: TwitterAccount):
        self.account = account
        self.logger = setup_logger(f"twitter_scraper.{account.username}")
        
        # 内部状態
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_file = Path(settings.sessions_dir) / f"{account.username}_session.json"
        
        # データ収集
        self.collected_tweets: List[Dict] = []
        self.tweet_ids_seen: Set[str] = set()
        self.errors: List[Dict] = []
        
        # ネットワーク傍受用のパターン
        self.tweet_patterns = [
            "TweetResultByRestId",
            "UserByRestId", 
            "SearchTimeline",
            "HomeTimeline"
        ]
        
        # User-Agent ローテーション用
        self.current_user_agent = random.choice(settings.user_agents)
        
        self.logger.info(f"Twitter スクレイパーを初期化: {account.username}")
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー（開始）"""
        await self.setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー（終了）"""
        await self.cleanup()
    
    @log_performance
    async def setup_browser(self):
        """ブラウザとページの初期化"""
        self.logger.info("ブラウザを初期化しています...")
        
        playwright = await async_playwright().start()
        
        # ブラウザ起動オプション
        browser_options = {
            "headless": settings.anti_detection.headless,
            "args": [
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
        }
        
        # プロキシ設定
        proxy_config = settings.get_proxy_config()
        if proxy_config:
            browser_options["proxy"] = proxy_config
            self.logger.info(f"プロキシを設定: {proxy_config['server']}")
        
        browser = await playwright.chromium.launch(**browser_options)
        
        # コンテキスト作成オプション
        context_options = {
            "viewport": settings.anti_detection.viewport_size,
            "user_agent": self.current_user_agent,
            "locale": "ja-JP",
            "timezone_id": "Asia/Tokyo"
        }
        
        # 既存セッション復元
        if self.session_file.exists():
            try:
                context_options["storage_state"] = str(self.session_file)
                self.logger.info("既存セッションを復元しました")
            except Exception as e:
                self.logger.warning(f"セッション復元に失敗: {e}")
        
        self.browser_context = await browser.new_context(**context_options)
        self.page = await self.browser_context.new_page()
        
        # ステルス機能の適用
        if settings.anti_detection.use_stealth:
            await stealth(self.page)
            self.logger.info("ステルス機能を適用しました")
        
        # ネットワーク傍受の設定
        self.page.on("response", self._handle_response)
        
        self.logger.info("ブラウザのセットアップが完了しました")
    
    async def _handle_response(self, response: Response):
        """ネットワーク応答の傍受処理"""
        url = response.url
        
        # Twitter APIの応答をフィルタリング
        if any(pattern in url for pattern in self.tweet_patterns):
            try:
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        json_data = await response.json()
                        await self._process_twitter_response(url, json_data)
            except Exception as e:
                self.logger.error(f"応答処理エラー ({url}): {e}")
    
    async def _process_twitter_response(self, url: str, data: Dict):
        """Twitter API 応答の処理"""
        try:
            # ツイートデータの抽出
            tweets = self._extract_tweets_from_response(data)
            
            for tweet in tweets:
                tweet_id = tweet.get("id_str") or tweet.get("rest_id")
                if tweet_id and tweet_id not in self.tweet_ids_seen:
                    self.tweet_ids_seen.add(tweet_id)
                    
                    # タイムスタンプを追加
                    tweet["scraped_at"] = datetime.utcnow().isoformat()
                    tweet["scraper_account"] = self.account.username
                    
                    self.collected_tweets.append(tweet)
                    
                    self.logger.debug(f"新しいツイートを収集: {tweet_id}")
            
            if tweets:
                self.logger.info(f"{len(tweets)}件のツイートを処理しました")
                
        except Exception as e:
            self.logger.error(f"Twitter応答処理エラー: {e}")
    
    def _extract_tweets_from_response(self, data: Dict) -> List[Dict]:
        """応答データからツイート情報を抽出"""
        tweets = []
        
        def extract_recursive(obj):
            if isinstance(obj, dict):
                # Tweet オブジェクトの識別
                if "rest_id" in obj and "legacy" in obj:
                    tweets.append(obj)
                elif "tweet" in obj:
                    extract_recursive(obj["tweet"])
                elif "tweets" in obj:
                    for tweet in obj["tweets"]:
                        extract_recursive(tweet)
                
                # 再帰的に検索
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(data)
        return tweets
    
    async def login(self) -> bool:
        """X.com へのログイン"""
        try:
            self.logger.info("X.com にログインしています...")
            
            await self.page.goto("https://x.com/login")
            await self._random_delay(2, 4)
            
            # ユーザー名入力
            username_selector = 'input[autocomplete="username"]'
            await self.page.wait_for_selector(username_selector, timeout=10000)
            await self.page.fill(username_selector, self.account.username)
            await self.page.keyboard.press("Enter")
            await self._random_delay(2, 3)
            
            # パスワード入力
            password_selector = 'input[name="password"]'
            await self.page.wait_for_selector(password_selector, timeout=10000)
            await self.page.fill(password_selector, self.account.get_password_for_scraping())
            await self.page.keyboard.press("Enter")
            await self._random_delay(3, 5)
            
            # 追加認証が必要な場合
            try:
                # 電話番号/メール入力が要求される場合
                email_selector = 'input[data-testid="ocfEnterTextTextInput"]'
                if await self.page.is_visible(email_selector):
                    self.logger.info("追加認証が必要です（メール）")
                    await self.page.fill(email_selector, self.account.email)
                    await self.page.keyboard.press("Enter")
                    await self._random_delay(3, 5)
            except Exception as e:
                self.logger.debug(f"追加認証処理: {e}")
            
            # ログイン成功確認
            try:
                await self.page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=15000)
                self.logger.info("ログインに成功しました")
                
                # セッション保存
                await self._save_session()
                return True
            except:
                self.logger.error("ログインに失敗しました")
                return False
                
        except Exception as e:
            self.logger.error(f"ログイン処理エラー: {e}")
            return False
    
    async def scrape_user_timeline(self, username: str, max_tweets: Optional[int] = None) -> List[Dict]:
        """指定ユーザーのタイムラインをスクレイピング"""
        if max_tweets is None:
            max_tweets = settings.scraping.max_tweets_per_session
        
        self.logger.info(f"@{username} のタイムラインをスクレイピング開始 (最大{max_tweets}件)")
        
        try:
            # ユーザーページに移動
            await self.page.goto(f"https://x.com/{username}")
            await self._random_delay(2, 4)
            
            # 無限スクロール実行
            await self._infinite_scroll(max_tweets)
            
            self.logger.info(f"スクレイピング完了: {len(self.collected_tweets)}件のツイートを収集")
            return self.collected_tweets.copy()
            
        except Exception as e:
            self.logger.error(f"タイムラインスクレイピングエラー: {e}")
            return []
    
    async def _infinite_scroll(self, max_tweets: int):
        """無限スクロールの実装"""
        scroll_attempts = 0
        last_height = 0
        no_new_content_count = 0
        
        while (len(self.collected_tweets) < max_tweets and 
               scroll_attempts < settings.scraping.max_scroll_attempts):
            
            # 現在のページ高さを取得
            current_height = await self.page.evaluate("document.body.scrollHeight")
            
            # 下部までスクロール
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # ネットワークがアイドル状態になるまで待機
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except:
                # タイムアウトの場合は通常の遅延
                await self._random_delay(
                    settings.scraping.scroll_delay_min,
                    settings.scraping.scroll_delay_max
                )
            
            # 新しいコンテンツが読み込まれたかチェック
            new_height = await self.page.evaluate("document.body.scrollHeight")
            
            if new_height == current_height:
                no_new_content_count += 1
                if no_new_content_count >= 3:
                    self.logger.info("新しいコンテンツが見つからないため、スクロールを終了")
                    break
            else:
                no_new_content_count = 0
            
            scroll_attempts += 1
            
            if scroll_attempts % 10 == 0:
                self.logger.info(f"スクロール進捗: {scroll_attempts}回, 収集済み: {len(self.collected_tweets)}件")
    
    async def save_to_jsonl(self, filename: Optional[str] = None) -> str:
        """収集したデータをJSONL形式で保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tweets_{self.account.username}_{timestamp}.jsonl"
        
        filepath = Path(settings.raw_data_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            for tweet in self.collected_tweets:
                f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
        
        self.logger.info(f"データを保存: {filepath} ({len(self.collected_tweets)}件)")
        return str(filepath)
    
    async def _save_session(self):
        """ブラウザセッション状態の保存"""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            await self.browser_context.storage_state(path=str(self.session_file))
            self.logger.debug("セッションを保存しました")
        except Exception as e:
            self.logger.warning(f"セッション保存エラー: {e}")
    
    async def _random_delay(self, min_seconds: float, max_seconds: float):
        """ランダムな遅延（人間らしい動作をシミュレート）"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def cleanup(self):
        """リソースのクリーンアップ"""
        if self.page:
            await self.page.close()
        if self.browser_context:
            await self.browser_context.close()
        
        self.logger.info("ブラウザリソースをクリーンアップしました")


class ScrapingSession:
    """スクレイピングセッションの管理クラス"""
    
    def __init__(self):
        self.logger = setup_logger("scraping_session")
        self.start_time = time.time()
        self.scrapers: List[TwitterScraper] = []
    
    async def run_session(self, target_users: List[str]) -> Dict[str, List[Dict]]:
        """スクレイピングセッションを実行"""
        results = {}
        
        # DB連携: 利用可能なアカウントを取得
        from src.services.account_service import twitter_account_service
        available_accounts = twitter_account_service.get_available_accounts()
        
        if not available_accounts:
            self.logger.error("利用可能なTwitterアカウントがありません")
            return results
        
        self.logger.info(f"利用可能なアカウント: {len(available_accounts)}件")
        
        # アカウントプールからランダム選択  
        self.logger.info(f"アカウント型: {type(available_accounts)}, 内容: {available_accounts}")
        account = random.choice(available_accounts)
        self.logger.info(f"選択されたアカウント: @{account.username} (型: {type(account)})")
        
        try:
            async with TwitterScraper(account) as scraper:
                # ログイン
                self.logger.info(f"アカウント @{account.username} でログイン試行中...")
                if not await scraper.login():
                    self.logger.error(f"アカウント @{account.username} のログインに失敗しました")
                    return results
                
                self.logger.info(f"アカウント @{account.username} のログインに成功しました")
                
                # 各ターゲットユーザーをスクレイピング
                for username in target_users:
                    try:
                        self.logger.info(f"ユーザー @{username} のタイムラインを取得中...")
                        tweets = await scraper.scrape_user_timeline(username)
                        results[username] = tweets
                        self.logger.info(f"ユーザー @{username}: {len(tweets)}件のツイートを取得")
                    except Exception as e:
                        self.logger.error(f"ユーザー @{username} のスクレイピングエラー: {e}")
                        results[username] = []
        except Exception as e:
            self.logger.error(f"スクレイピングセッションエラー: {e}")
            raise
        
        session_duration = time.time() - self.start_time
        total_tweets = sum(len(tweets) for tweets in results.values())
        
        self.logger.info(f"セッション完了: {total_tweets}件のツイートを収集 ({session_duration:.2f}秒)")
        
        return results