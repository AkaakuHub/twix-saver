"""
Playwright ベースの X.com スクレイピングエンジン
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, Response, async_playwright
from playwright_stealth import Stealth

from src.config.settings import settings
from src.models.database import TwitterAccount
from src.utils.logger import log_performance, setup_logger


class TwitterScraper:
    """
    X.com スクレイピングエンジン
    ネットワーク傍受とアンチ検知機能を備えた堅牢なスクレイパー
    """

    def __init__(self, account: TwitterAccount, max_tweets: Optional[int] = None):
        self.account = account
        self.max_tweets = max_tweets
        self.logger = setup_logger(f"twitter_scraper.{account.username}")

        if max_tweets:
            self.logger.info(f"デバッグモード：最大{max_tweets}件のツイートを取得")

        # 内部状態
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_file = Path(settings.sessions_dir) / f"{account.username}_session.json"

        # データ収集
        self.collected_tweets: list[dict] = []
        self.tweet_ids_seen: set[str] = set()
        self.errors: list[dict] = []

        # チャンク処理設定
        self.chunk_size = 20  # 20件ごとに保存
        self.save_counter = 0
        self.total_saved = 0
        self.current_target_user = None  # 現在のターゲットユーザー名

        # ネットワーク傍受用のパターン (元の動作していたパターンを復元)
        self.tweet_patterns = [
            "TweetResultByRestId",
            "UserByRestId",
            "SearchTimeline",
            "UserTweets",  # ユーザーページ専用
            "UserTweetsAndReplies",  # ユーザーページ専用
            "UserMedia",  # ユーザーページ専用
        ]

        # 新規ツイート検知用
        self.known_tweet_ids: set[str] = set()  # 既知のツイートID
        self.target_user_id: Optional[str] = None  # 監視対象ユーザーID

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
                "--disable-features=VizDisplayCompositor",
            ],
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
            "timezone_id": "Asia/Tokyo",
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
            # ターゲットユーザーが設定されている場合、現在のページURLを確認
            if self.current_target_user:
                try:
                    current_url = self.page.url
                    expected_url = f"https://x.com/{self.current_target_user}"
                    if not current_url.startswith(expected_url):
                        self.logger.debug(
                            f"ターゲット外ページでのAPI応答をスキップ: {current_url} (期待: {expected_url})"
                        )
                        return
                except Exception as e:
                    self.logger.debug(f"ページURL確認エラー: {e}")
                    return
            try:
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        json_data = await response.json()
                        await self._process_twitter_response(url, json_data)
            except Exception as e:
                self.logger.error(f"応答処理エラー ({url}): {e}")

    async def _process_twitter_response(self, url: str, data: dict):
        """Twitter API 応答の処理"""
        try:
            # ツイートデータの抽出
            tweets = self._extract_tweets_from_response(data)

            target_tweets = 0  # ターゲットユーザーのツイート数

            for tweet in tweets:
                tweet_id = tweet.get("id_str") or tweet.get("rest_id")
                if tweet_id and tweet_id not in self.tweet_ids_seen:
                    # ターゲットユーザーのフィルタリング
                    if self.current_target_user:
                        tweet_username = self._extract_tweet_username(tweet)
                        if tweet_username and tweet_username.lower() != self.current_target_user.lower():
                            self.logger.debug(
                                f"非対象ユーザーのツイートをスキップ: @{tweet_username} (ターゲット: @{self.current_target_user})"
                            )
                            continue
                        target_tweets += 1
                        self.logger.debug(f"対象ツイートを収集: @{tweet_username} - {tweet_id}")

                    self.tweet_ids_seen.add(tweet_id)

                    # タイムスタンプを追加
                    tweet["scraped_at"] = datetime.utcnow().isoformat()
                    tweet["scraper_account"] = self.account.username

                    self.collected_tweets.append(tweet)

                    # デバッグ用：最大件数で停止
                    if self.max_tweets and self.total_saved + len(self.collected_tweets) >= self.max_tweets:
                        self.logger.info(f"デバッグ制限：{self.max_tweets}件に達したため停止")
                        await self._save_chunk()
                        return

                    # チャンク保存チェック
                    if len(self.collected_tweets) >= self.chunk_size:
                        await self._save_chunk()

            if tweets:
                if self.current_target_user:
                    self.logger.info(
                        f"レスポンス処理完了 - 全体:{len(tweets)}件, @{self.current_target_user}のツイート:{target_tweets}件"
                    )
                else:
                    self.logger.info(f"{len(tweets)}件のツイートを処理しました")

        except Exception as e:
            self.logger.error(f"Twitter応答処理エラー: {e}")

    def _extract_tweets_from_response(self, data: dict) -> list[dict]:
        """応答データからツイート情報を抽出"""
        tweets = []

        def extract_recursive(obj):
            if isinstance(obj, dict):
                # Tweet オブジェクトのみを識別（User オブジェクトを除外）
                if "rest_id" in obj and "legacy" in obj:
                    obj_type = obj.get("__typename", "Unknown")
                    if obj_type == "Tweet":
                        tweets.append(obj)
                        self.logger.debug(f"Tweet抽出: {obj.get('rest_id')} - {obj_type}")
                    else:
                        self.logger.debug(f"非Tweet除外: {obj.get('rest_id')} - {obj_type}")
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

    def _extract_tweet_username(self, tweet: dict) -> Optional[str]:
        """ツイートからユーザー名を抽出"""
        try:
            # Twitter API v2 format
            if "legacy" in tweet and "user" in tweet:
                user_data = tweet["user"]
                if "legacy" in user_data:
                    return user_data["legacy"].get("screen_name")
                return user_data.get("screen_name")

            # Twitter API v1.1 format
            if "user" in tweet:
                return tweet["user"].get("screen_name")

            # Legacy format direct access
            if "legacy" in tweet:
                legacy = tweet["legacy"]
                if "user" in legacy:
                    return legacy["user"].get("screen_name")
                # Core user data might be in legacy
                user_mentions = legacy.get("entities", {}).get("user_mentions", [])
                if user_mentions and len(user_mentions) == 1:
                    return user_mentions[0].get("screen_name")

            # Alternative paths
            if "screen_name" in tweet:
                return tweet["screen_name"]

            return None

        except Exception as e:
            self.logger.debug(f"ユーザー名抽出エラー: {e}")
            return None

    async def _scrape_specific_tweets(self, username: str, specific_tweet_ids: list[str]) -> list[dict]:
        """特定のツイートIDのみをスクレイピング"""
        try:
            collected_tweets = []

            for tweet_id in specific_tweet_ids:
                try:
                    self.logger.info(f"特定ツイートを取得中: {tweet_id}")

                    # 個別ツイートURLに直接アクセス
                    tweet_url = f"https://x.com/{username}/status/{tweet_id}"
                    await self.page.goto(tweet_url)
                    await self._random_delay(2, 4)

                    # ツイートが存在するかチェック
                    try:
                        tweet_selector = '[data-testid="tweet"]'
                        await self.page.wait_for_selector(tweet_selector, timeout=10000)

                        # 基本的なツイートデータを作成（更新目的なので最小限）
                        tweet_data = {
                            "id_str": tweet_id,
                            "scraped_at": datetime.now().isoformat(),
                            "username": username,
                            "refresh_requested": True,
                            "legacy": {
                                "id_str": tweet_id,
                                "user": {"screen_name": username},
                            },
                        }

                        collected_tweets.append(tweet_data)
                        self.collected_tweets.append(tweet_data)
                        self.logger.info(f"特定ツイート取得成功: {tweet_id}")

                    except Exception as e:
                        self.logger.warning(f"特定ツイート {tweet_id} のページ読み込み失敗: {e}")
                        continue

                except Exception as e:
                    self.logger.error(f"特定ツイート {tweet_id} の取得エラー: {e}")
                    continue

            # チャンク保存
            if self.collected_tweets:
                await self._save_chunk()

            self.logger.info(f"特定ツイート取得完了: {len(collected_tweets)}件")
            return collected_tweets

        except Exception as e:
            self.logger.error(f"特定ツイートスクレイピングエラー: {e}")
            return []

    async def login(self) -> bool:
        """X.com へのログイン"""
        try:
            self.logger.info("X.com にログインしています...")
            self._log_to_job("X.com にログイン中...")

            # まずホームページに移動してログイン状態を確認
            await self.page.goto("https://x.com/home")
            await self._random_delay(2, 3)

            # ログイン済みかチェック
            try:
                # ホームタイムラインが表示されているかチェック
                if await self.page.is_visible('[data-testid="primaryColumn"]', timeout=10000):
                    self.logger.info("既にログイン済みです")
                    self._log_to_job("ログイン済み")
                    return True
            except Exception:  # noqa: S110
                pass

            # ログインが必要な場合、ログインページに移動
            self.logger.info("ログインが必要です")
            await self.page.goto("https://x.com/login")
            await self._random_delay(2, 4)

            # ユーザー名入力
            username_selector = 'input[autocomplete="username"]'
            await self.page.wait_for_selector(username_selector, timeout=30000)
            await self.page.fill(username_selector, self.account.username)
            await self.page.keyboard.press("Enter")
            await self._random_delay(2, 3)

            # パスワード入力
            password_selector = 'input[name="password"]'  # noqa: S105
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
            except Exception as e:
                self.logger.error(f"ログインに失敗しました: {e}")
                return False

        except Exception as e:
            self.logger.error(f"ログイン処理エラー: {e}")
            return False

    async def sync_user_tweets(self, username: str, specific_tweet_ids: Optional[list[str]] = None) -> list[dict]:
        """指定ユーザーの新規ツイートのみを検知・同期"""
        self.current_target_user = username

        # 特定ツイートIDが指定されている場合は専用処理
        if specific_tweet_ids:
            self.logger.info(f"@{username} の特定ツイート再取得を開始: {specific_tweet_ids}")
            self._log_to_job(f"@{username} の特定ツイート再取得開始: {specific_tweet_ids}")
            return await self._scrape_specific_tweets(username, specific_tweet_ids)

        self.logger.info(f"@{username} の新規ツイート検知を開始")
        self._log_to_job(f"@{username} の新規ツイート検知開始")

        try:
            # 既知のツイートIDを事前に取得
            await self._load_known_tweet_ids(username)

            # ユーザーページに移動（最新数件のみ確認）
            target_url = f"https://x.com/{username}"
            self.logger.info(f"ユーザーページ確認: {target_url}")
            await self.page.goto(target_url)
            await self._random_delay(1, 2)  # 短時間で済ます

            # 新規ツイート検知待機（最大10秒）
            await self._detect_new_tweets(timeout_seconds=10)

            new_tweets = [t for t in self.collected_tweets if t.get("id_str") not in self.known_tweet_ids]

            if new_tweets:
                self.logger.info(f"@{username} の新規ツイートを検知: {len(new_tweets)}件")
                await self._save_chunk()  # 即座に保存
            else:
                self.logger.info(f"@{username} の新規ツイートはありません")

            return new_tweets

        except Exception as e:
            self.logger.error(f"新規ツイート検知エラー: {e}")
            return []

    async def _load_known_tweet_ids(self, username: str):
        """データベースから既知のツイートIDを読み込み"""
        try:
            from src.utils.data_manager import mongodb_manager

            tweets_collection = mongodb_manager.db["tweets"]

            # 対象ユーザーの既存ツイートIDを取得（新旧データ構造対応）
            cursor = tweets_collection.find(
                {
                    "$or": [
                        {"user.screen_name": username},
                        {"legacy.user_id_str": {"$exists": True}},  # 新しい構造の場合はuser_id_strで判定
                        {"core.user_results.result.core.screen_name": username},
                    ]
                },
                {"id_str": 1, "_id": 0},
            )

            self.known_tweet_ids = {doc["id_str"] for doc in cursor if doc.get("id_str")}
            self.logger.info(f"@{username} の既知ツイートID: {len(self.known_tweet_ids)}件")

        except Exception as e:
            self.logger.error(f"既知ツイートID読み込みエラー: {e}")
            self.known_tweet_ids = set()

    async def _detect_new_tweets(self, timeout_seconds: int = 10):
        """新規ツイートを検知するまで短時間待機"""
        start_time = time.time()
        initial_count = len(self.collected_tweets)

        while (time.time() - start_time) < timeout_seconds:
            await asyncio.sleep(0.5)  # 短いポーリング間隔

            # 新しいツイートが検知されたか確認
            current_count = len(self.collected_tweets)
            if current_count > initial_count:
                self.logger.debug(f"新規ツイート検知: +{current_count - initial_count}件")
                await asyncio.sleep(1)  # 少し待ってから完了
                break

        self.logger.info(f"ツイート検知完了: {len(self.collected_tweets)}件")

    async def _save_chunk(self):
        """チャンク単位でのデータ保存"""
        if not self.collected_tweets:
            return

        try:
            self.save_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # ターゲットユーザー名を使用（フォールバックとしてスクレイパーアカウント名）
            target_name = self.current_target_user or self.account.username
            filename = f"tweets_{target_name}_{timestamp}_chunk{self.save_counter:03d}.jsonl"

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
        if hasattr(self, "playwright") and self.playwright:
            await self.playwright.stop()

        self.logger.info("ブラウザリソースをクリーンアップしました")


class ScrapingSession:
    """スクレイピングセッションの管理クラス"""

    def __init__(
        self,
        max_tweets: Optional[int] = None,
        specific_tweet_ids: Optional[list[str]] = None,
    ):
        self.logger = setup_logger("scraping_session")
        self.start_time = time.time()
        self.scrapers: list[TwitterScraper] = []
        self.max_tweets = max_tweets
        self.specific_tweet_ids = specific_tweet_ids

    async def run_session(self, target_users: list[str]) -> dict[str, any]:
        """スクレイピングセッションを実行"""
        tweet_results = {}
        session_stats = {
            "total_tweets_saved": 0,
            "total_chunks": 0,
            "users_processed": [],
            "users_failed": [],
        }

        # DB連携: 利用可能なアカウントを取得
        from src.services.account_service import twitter_account_service

        available_accounts = twitter_account_service.get_available_accounts()

        if not available_accounts:
            self.logger.error("利用可能なTwitterアカウントがありません")
            return {"tweets": tweet_results, "stats": session_stats}

        self.logger.info(f"利用可能なアカウント: {len(available_accounts)}件")

        # アカウントプールからランダム選択
        self.logger.info(f"アカウント型: {type(available_accounts)}, 内容: {available_accounts}")
        account = random.choice(available_accounts)
        self.logger.info(f"選択されたアカウント: @{account.username} (型: {type(account)})")

        try:
            async with TwitterScraper(account, max_tweets=self.max_tweets) as scraper:
                # ジョブIDを設定（main.pyから呼ばれる場合）
                if hasattr(self, "_current_job_id"):
                    scraper.current_job_id = self._current_job_id
                # ログイン
                self.logger.info(f"アカウント @{account.username} でログイン試行中...")
                if not await scraper.login():
                    self.logger.error(f"アカウント @{account.username} のログインに失敗しました")
                    return {"tweets": tweet_results, "stats": session_stats}

                self.logger.info(f"アカウント @{account.username} のログインに成功しました")

                # 各ターゲットユーザーの新規ツイートを検知
                for username in target_users:
                    try:
                        self.logger.info(f"ユーザー @{username} の新規ツイートを検知中...")
                        new_tweets = await scraper.sync_user_tweets(username, self.specific_tweet_ids)
                        tweet_results[username] = new_tweets

                        # 正確な統計情報を収集
                        new_count = len(new_tweets)
                        total_saved = scraper.total_saved + new_count
                        chunks_created = scraper.save_counter

                        # セッション統計を更新
                        session_stats["total_tweets_saved"] += total_saved
                        session_stats["total_chunks"] += chunks_created
                        session_stats["users_processed"].append(username)

                        self.logger.info(
                            f"ユーザー @{username}: 総取得数 {total_saved}件 (チャンク保存{chunks_created}回)"
                        )
                        print(f"\n[完了] @{username}")
                        print(f"  総取得数: {total_saved}件")
                        print(f"  チャンク保存: {chunks_created}回")
                        print("  保存場所: data/raw/")

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

        self.logger.info(
            f"セッション完了: {session_stats['total_tweets_saved']}件のツイートを収集 ({session_duration:.2f}秒)"
        )

        return {"tweets": tweet_results, "stats": session_stats}
