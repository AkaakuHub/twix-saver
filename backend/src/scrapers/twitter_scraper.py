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
from playwright_stealth import Stealth

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
        
        # チャンク処理設定
        self.chunk_size = 20  # 20件ごとに保存
        self.save_counter = 0
        self.total_saved = 0
        
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
        
        # ジョブIDを追跡するための変数（後でmain.pyから設定）
        self.current_job_id = None
    
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
        self._log_to_job("ブラウザを初期化中...")
        
        try:
            playwright_manager = async_playwright()
            self.playwright = await playwright_manager.start()
            self.logger.info("Playwrightを正常に初期化しました")
        except Exception as e:
            self.logger.error(f"Playwright初期化エラー: {e}")
            self.logger.error(f"async_playwright type: {type(async_playwright)}")
            raise
        
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
        
        try:
            browser = await self.playwright.chromium.launch(**browser_options)
            self.logger.info("ブラウザを正常に起動しました")
        except Exception as e:
            self.logger.error(f"ブラウザ起動エラー: {e}")
            self.logger.error(f"playwright type: {type(self.playwright)}")
            self.logger.error(f"chromium type: {type(self.playwright.chromium)}")
            raise
        
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
        
        try:
            self.browser_context = await browser.new_context(**context_options)
            self.logger.info("ブラウザコンテキストを作成しました")
            self.page = await self.browser_context.new_page()
            self.logger.info("ページを作成しました")
        except Exception as e:
            self.logger.error(f"コンテキスト/ページ作成エラー: {e}")
            self.logger.error(f"browser type: {type(browser)}")
            raise
        
        # ステルス機能の適用
        if settings.anti_detection.use_stealth:
            try:
                stealth = Stealth()
                await stealth.apply_stealth_async(self.browser_context)
                self.logger.info("ステルス機能を適用しました")
            except Exception as e:
                self.logger.error(f"ステルス機能の適用エラー: {e}")
                raise
        
        # ネットワーク傍受の設定
        try:
            self.page.on("response", self._handle_response)
            self.logger.info("ネットワーク傍受を設定しました")
        except Exception as e:
            self.logger.error(f"ネットワーク傍受設定エラー: {e}")
            raise
        
        self.logger.info("ブラウザのセットアップが完了しました")
        self._log_to_job("ブラウザセットアップ完了")
    
    def _log_to_job(self, message: str):
        """ジョブログにメッセージを追加"""
        if self.current_job_id:
            try:
                from src.services.job_service import job_service
                job_service.add_job_log(self.current_job_id, message)
                print(f"[{self.account.username}] {message}")  # コンソールにも出力
            except Exception as e:
                self.logger.debug(f"ジョブログ追加エラー: {e}")
    
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
                    
                    # チャンク保存チェック
                    if len(self.collected_tweets) >= self.chunk_size:
                        await self._save_chunk()
            
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
            self._log_to_job("X.com にログイン中...")
            
            await self.page.goto("https://x.com/login")
            await self._random_delay(2, 4)
            
            # ユーザー名入力
            username_selector = 'input[autocomplete="username"]'
            await self.page.wait_for_selector(username_selector, timeout=30000)
            await self.page.fill(username_selector, self.account.username)
            await self.page.keyboard.press("Enter")
            await self._random_delay(2, 3)
            
            # パスワード入力
            password_selector = 'input[name="password"]'
            await self.page.wait_for_selector(password_selector, timeout=30000)
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
                await self.page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=30000)
                self.logger.info("ログインに成功しました")
                self._log_to_job("ログイン成功")
                
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
        self._log_to_job(f"@{username} のタイムライン取得開始 (最大{max_tweets}件)")
        
        try:
            # ユーザーページに移動
            await self.page.goto(f"https://x.com/{username}")
            await self._random_delay(2, 4)
            
            # 無限スクロール実行
            await self._infinite_scroll(max_tweets)
            
            buffer_count = len(self.collected_tweets)
            self.logger.info(f"スクレイピング完了: チャンク保存{self.total_saved}件 + バッファ{buffer_count}件")
            
            # 最後のバッファ分を返す（ScrapingSessionで正確な統計は取得される）
            return self.collected_tweets.copy()
            
        except Exception as e:
            self.logger.error(f"タイムラインスクレイピングエラー: {e}")
            return []
    
    async def _infinite_scroll(self, max_tweets: int):
        """無限スクロールの実装（エラー耐性・段階保存付き）"""
        scroll_attempts = 0
        last_height = 0
        no_new_content_count = 0
        consecutive_errors = 0
        max_errors = 3
        
        self.logger.info(f"無限スクロール開始: 目標{max_tweets}件")
        
        while (self.total_saved + len(self.collected_tweets) < max_tweets and 
               scroll_attempts < settings.scraping.max_scroll_attempts and
               consecutive_errors < max_errors):
            
            try:
                scroll_attempts += 1
                self.logger.debug(f"スクロール試行 #{scroll_attempts}")
                
                # 現在のページ高さを取得
                current_height = await self.page.evaluate("document.body.scrollHeight")
                self.logger.debug(f"現在のページ高さ: {current_height}px")
                
                # 下部までスクロール
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self._random_delay(1, 2)  # 基本遅延
                
                # ネットワーク待機（タイムアウト短縮）
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    self.logger.debug("ネットワークアイドル状態検出")
                except:
                    # タイムアウトの場合は通常の遅延
                    await self._random_delay(
                        settings.scraping.scroll_delay_min,
                        settings.scraping.scroll_delay_max
                    )
                    self.logger.debug("ネットワーク待機タイムアウト、通常遅延実行")
                
                # 新しいコンテンツが読み込まれたかチェック
                new_height = await self.page.evaluate("document.body.scrollHeight")
                self.logger.debug(f"スクロール後の高さ: {new_height}px")
                
                if new_height == current_height:
                    no_new_content_count += 1
                    self.logger.debug(f"高さ変化なし (連続{no_new_content_count}回)")
                    if no_new_content_count >= 3:
                        self.logger.info("新しいコンテンツが見つからないため、スクロールを終了")
                        break
                else:
                    no_new_content_count = 0
                    self.logger.debug("ページ高さ増加、新しいコンテンツ検出")
                
                # エラーカウンターリセット
                consecutive_errors = 0
                
                # 進捗表示（5回毎）
                if scroll_attempts % 5 == 0:
                    current_total = self.total_saved + len(self.collected_tweets)
                    progress_msg = f"スクロール{scroll_attempts}回 - バッファ{len(self.collected_tweets)}件, 保存済み{self.total_saved}件"
                    self.logger.info(f"スクロール進捗: {scroll_attempts}回, 現在バッファ: {len(self.collected_tweets)}件, 累計: {current_total}件")
                    self._log_to_job(progress_msg)
                    print(f"[進捗] {progress_msg}")
                
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"スクロールエラー (連続{consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors < max_errors:
                    self.logger.info("エラーからリトライします...")
                    await self._random_delay(3, 5)  # エラー後は長めの待機
                else:
                    self.logger.error("連続エラー上限に達しました、スクロールを中断")
                    break
        
        # 最終チャンク保存
        if self.collected_tweets:
            self.logger.info("最終チャンクを保存します")
            await self._save_chunk()
        
        self.logger.info(f"スクロール完了: 総スクロール{scroll_attempts}回, 総保存数: {self.total_saved}件 (チャンク{self.save_counter}回)")
    
    async def _save_chunk(self):
        """チャンク単位でのデータ保存"""
        if not self.collected_tweets:
            return
        
        try:
            self.save_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tweets_{self.account.username}_{timestamp}_chunk{self.save_counter:03d}.jsonl"
            
            filepath = Path(settings.raw_data_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                for tweet in self.collected_tweets:
                    f.write(json.dumps(tweet, ensure_ascii=False) + "\n")
            
            saved_count = len(self.collected_tweets)
            self.total_saved += saved_count
            abs_filepath = filepath.absolute()
            
            self.logger.info(f"チャンク保存完了: {abs_filepath} ({saved_count}件, 累計{self.total_saved}件)")
            chunk_msg = f"チャンク{self.save_counter:03d} - {saved_count}件保存 (累計{self.total_saved}件)"
            self._log_to_job(chunk_msg)
            print(f"[チャンク{self.save_counter:03d}] {saved_count}件保存 → {filename}")
            
            # リセット
            self.collected_tweets.clear()
            
        except Exception as e:
            self.logger.error(f"チャンク保存エラー: {e}")

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
        
        abs_filepath = filepath.absolute()
        saved_count = len(self.collected_tweets)
        total_final = self.total_saved + saved_count
        self.logger.info(f"最終データを保存: {abs_filepath} ({saved_count}件, 総計{total_final}件)")
        return str(abs_filepath)
    
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
        if hasattr(self, 'playwright') and self.playwright:
            await self.playwright.stop()
        
        self.logger.info("ブラウザリソースをクリーンアップしました")


class ScrapingSession:
    """スクレイピングセッションの管理クラス"""
    
    def __init__(self):
        self.logger = setup_logger("scraping_session")
        self.start_time = time.time()
        self.scrapers: List[TwitterScraper] = []
    
    async def run_session(self, target_users: List[str]) -> Dict[str, any]:
        """スクレイピングセッションを実行"""
        tweet_results = {}
        session_stats = {
            "total_tweets_saved": 0,
            "total_chunks": 0,
            "users_processed": [],
            "users_failed": []
        }
        
        # DB連携: 利用可能なアカウントを取得
        from src.services.account_service import twitter_account_service
        available_accounts = twitter_account_service.get_available_accounts()
        
        if not available_accounts:
            self.logger.error("利用可能なTwitterアカウントがありません")
            return {
                "tweets": tweet_results,
                "stats": session_stats
            }
        
        self.logger.info(f"利用可能なアカウント: {len(available_accounts)}件")
        
        # アカウントプールからランダム選択  
        self.logger.info(f"アカウント型: {type(available_accounts)}, 内容: {available_accounts}")
        account = random.choice(available_accounts)
        self.logger.info(f"選択されたアカウント: @{account.username} (型: {type(account)})")
        
        try:
            async with TwitterScraper(account) as scraper:
                # ジョブIDを設定（main.pyから呼ばれる場合）
                if hasattr(self, '_current_job_id'):
                    scraper.current_job_id = self._current_job_id
                # ログイン
                self.logger.info(f"アカウント @{account.username} でログイン試行中...")
                if not await scraper.login():
                    self.logger.error(f"アカウント @{account.username} のログインに失敗しました")
                    return {
                        "tweets": tweet_results,
                        "stats": session_stats
                    }
                
                self.logger.info(f"アカウント @{account.username} のログインに成功しました")
                
                # 各ターゲットユーザーをスクレイピング
                for username in target_users:
                    try:
                        self.logger.info(f"ユーザー @{username} のタイムラインを取得中...")
                        tweets = await scraper.scrape_user_timeline(username)
                        tweet_results[username] = tweets
                        
                        # 正確な統計情報を収集
                        buffer_count = len(tweets)
                        total_saved = scraper.total_saved + buffer_count  # バッファ分も含めて最終保存予定
                        chunks_created = scraper.save_counter
                        
                        # セッション統計を更新
                        session_stats["total_tweets_saved"] += total_saved
                        session_stats["total_chunks"] += chunks_created
                        session_stats["users_processed"].append(username)
                        
                        self.logger.info(f"ユーザー @{username}: 総取得数 {total_saved}件 (チャンク保存{chunks_created}回)")
                        print(f"\n[完了] @{username}")
                        print(f"  総取得数: {total_saved}件")
                        print(f"  チャンク保存: {chunks_created}回")
                        print(f"  保存場所: data/raw/")
                        
                    except Exception as e:
                        self.logger.error(f"ユーザー @{username} のスクレイピングエラー: {e}")
                        tweet_results[username] = []
                        session_stats["users_failed"].append(username)
                        print(f"\n[エラー] @{username}: {str(e)}")
        except Exception as e:
            self.logger.error(f"スクレイピングセッションエラー: {e}")
            raise
        
        session_duration = time.time() - self.start_time
        session_stats["processing_time"] = session_duration
        
        self.logger.info(f"セッション完了: {session_stats['total_tweets_saved']}件のツイートを収集 ({session_duration:.2f}秒)")
        
        return {
            "tweets": tweet_results,
            "stats": session_stats
        }