"""
データアーキテクチャとストレージシステム
JSONLファイル処理とMongoDBへのデータインジェスト
"""

import asyncio
import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from src.config.settings import settings
from src.utils.logger import setup_logger
from src.utils.media_processor import media_processor


class JSONLProcessor:
    """JSON Lines ファイルの処理クラス"""

    def __init__(self):
        self.logger = setup_logger("jsonl_processor")

    def write_jsonl(self, data: list[dict], filepath: Path) -> int:
        """データをJSONL形式で書き込み"""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "a", encoding="utf-8") as f:
                for item in data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    f.write(json_line + "\n")

            self.logger.info(f"JSONLファイルに{len(data)}件を書き込み: {filepath}")
            return len(data)

        except Exception as e:
            self.logger.error(f"JSONL書き込みエラー ({filepath}): {e}")
            return 0

    def read_jsonl(self, filepath: Path) -> Iterator[dict]:
        """JSONLファイルを読み込み（ジェネレータ）"""
        try:
            if not filepath.exists():
                self.logger.warning(f"JSONLファイルが存在しません: {filepath}")
                return

            with open(filepath, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON解析エラー ({filepath}:{line_num}): {e}")
                        continue

        except Exception as e:
            self.logger.error(f"JSONLファイル読み込みエラー ({filepath}): {e}")

    def count_lines(self, filepath: Path) -> int:
        """JSONLファイルの行数をカウント"""
        try:
            if not filepath.exists():
                return 0

            with open(filepath, encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())

        except Exception as e:
            self.logger.error(f"行数カウントエラー ({filepath}): {e}")
            return 0

    def validate_jsonl(self, filepath: Path) -> dict[str, Any]:
        """JSONLファイルの検証"""
        result = {"valid_lines": 0, "invalid_lines": 0, "total_lines": 0, "errors": []}

        try:
            if not filepath.exists():
                result["errors"].append(f"ファイルが存在しません: {filepath}")
                return result

            with open(filepath, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    result["total_lines"] += 1
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        json.loads(line)
                        result["valid_lines"] += 1
                    except json.JSONDecodeError as e:
                        result["invalid_lines"] += 1
                        result["errors"].append(f"行{line_num}: {str(e)}")

            self.logger.info(
                f"JSONL検証完了 ({filepath}): 有効{result['valid_lines']}件, 無効{result['invalid_lines']}件"
            )

        except Exception as e:
            result["errors"].append(f"ファイル読み込みエラー: {str(e)}")

        return result


class MongoDBManager:
    """MongoDB データベース管理クラス"""

    def __init__(self):
        self.logger = setup_logger("mongodb_manager")
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.tweets_collection: Optional[Collection] = None
        self.articles_collection: Optional[Collection] = None

        self._connect()

    def _connect(self):
        """MongoDB接続の確立"""
        try:
            self.client = MongoClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_database]

            # コレクション取得
            self.tweets_collection = self.db["tweets"]
            self.articles_collection = self.db["linked_articles"]

            # 接続テスト
            self.client.admin.command("ping")

            # インデックス作成
            self._ensure_indexes()

            self.logger.info(f"MongoDB接続成功: {settings.mongodb_database}")

        except PyMongoError as e:
            self.logger.error(f"MongoDB接続エラー: {e}")
            self.client = None

    def _ensure_indexes(self):
        """必要なインデックスを作成"""
        try:
            # tweets コレクションのインデックス
            self.tweets_collection.create_index("id_str", unique=True)
            self.tweets_collection.create_index("rest_id", unique=True, sparse=True)
            self.tweets_collection.create_index("scraped_at")
            self.tweets_collection.create_index("scraper_account")

            # ユーザー関連のインデックス
            self.tweets_collection.create_index("legacy.user.screen_name")
            self.tweets_collection.create_index("core.user_results.result.legacy.screen_name")

            # linked_articles コレクションのインデックス
            self.articles_collection.create_index("url", unique=True)
            self.articles_collection.create_index("retrieved_at")

            self.logger.info("MongoDBインデックスを作成しました")

        except PyMongoError as e:
            self.logger.error(f"インデックス作成エラー: {e}")

    def get_jst_now(self):
        """JST（日本標準時）の現在時刻を取得"""
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst)

    @property
    def is_connected(self) -> bool:
        """接続状態のチェック"""
        try:
            if self.client:
                self.client.admin.command("ping")
                return True
        except PyMongoError:
            # 接続エラーは正常な状態として扱う
            pass
        return False

    def insert_tweets(self, tweets: list[dict]) -> int:
        """ツイートデータの一括挿入/更新"""
        if not self.is_connected:
            self.logger.error("MongoDB接続が無効です")
            return 0

        if not tweets:
            return 0

        try:
            operations = []

            for tweet in tweets:
                # ツイートIDを取得（複数のフィールドから）
                tweet_id = tweet.get("id_str") or tweet.get("rest_id") or tweet.get("id")

                if not tweet_id:
                    self.logger.warning("ツイートIDが見つかりません")
                    continue

                # ツイートデータを正規化（id_strを確実に設定）
                normalized_tweet = tweet.copy()
                normalized_tweet["id_str"] = tweet_id
                if "rest_id" not in normalized_tweet:
                    normalized_tweet["rest_id"] = tweet_id

                # upsert操作を作成（メディアデータを適切にマージ）
                filter_query = {"$or": [{"id_str": tweet_id}, {"rest_id": tweet_id}]}

                # downloaded_mediaがある場合は専用の更新ロジック
                if "downloaded_media" in normalized_tweet:
                    downloaded_media = normalized_tweet.pop("downloaded_media")

                    # デバッグログ: メディア処理結果を記録
                    media_types = {}
                    for media in downloaded_media:
                        media_type = media.get("type", "unknown")
                        media_types[media_type] = media_types.get(media_type, 0) + 1

                    if downloaded_media:
                        self.logger.info(f"ツイート {tweet_id} のメディア保存: {media_types}")

                    # normalized_tweetにdownloaded_mediaを再追加
                    normalized_tweet["downloaded_media"] = downloaded_media

                    update_doc = {"$set": normalized_tweet}

                    operations.append(UpdateOne(filter_query, update_doc, upsert=True))
                else:
                    # 通常のツイートデータは既存の処理
                    operations.append(UpdateOne(filter_query, {"$set": normalized_tweet}, upsert=True))

            if operations:
                result = self.tweets_collection.bulk_write(operations, ordered=False)

                inserted = result.upserted_count
                updated = result.modified_count

                self.logger.info(f"ツイートデータ処理完了: 新規{inserted}件, 更新{updated}件")
                return inserted + updated

        except PyMongoError as e:
            self.logger.error(f"ツイート挿入エラー: {e}")

        return 0

    def insert_articles(self, articles: list[dict]) -> int:
        """記事データの一括挿入/更新"""
        if not self.is_connected:
            self.logger.error("MongoDB接続が無効です")
            return 0

        if not articles:
            return 0

        try:
            operations = []

            for article in articles:
                if not article.get("url"):
                    continue

                operations.append(UpdateOne({"url": article["url"]}, {"$set": article}, upsert=True))

            if operations:
                result = self.articles_collection.bulk_write(operations, ordered=False)

                inserted = result.upserted_count
                updated = result.modified_count

                self.logger.info(f"記事データ処理完了: 新規{inserted}件, 更新{updated}件")
                return inserted + updated

        except PyMongoError as e:
            self.logger.error(f"記事挿入エラー: {e}")

        return 0

    def get_tweet_stats(self) -> dict[str, Any]:
        """ツイートコレクションの統計情報"""
        if not self.is_connected:
            return {}

        try:
            total_tweets = self.tweets_collection.count_documents({})

            # 最新ツイートの日時
            latest_tweet = self.tweets_collection.find_one({}, sort=[("scraped_at", -1)])

            # スクレイパー別統計
            scraper_stats = list(
                self.tweets_collection.aggregate(
                    [
                        {"$group": {"_id": "$scraper_account", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ]
                )
            )

            return {
                "total_tweets": total_tweets,
                "latest_scraped": latest_tweet.get("scraped_at") if latest_tweet else None,
                "scraper_stats": scraper_stats,
            }

        except PyMongoError as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {}

    def get_collection(self, collection_name: str) -> Collection:
        """指定されたコレクションを取得"""
        if not self.is_connected:
            raise ConnectionError("MongoDB接続が確立されていません")

        return self.db[collection_name]

    def close(self):
        """接続を閉じる"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB接続を閉じました")


class DataIngestService:
    """データインジェストサービス
    JSONLファイルからMongoDBへのデータ移行を管理
    """

    def __init__(self):
        self.logger = setup_logger("data_ingest")
        self.jsonl_processor = JSONLProcessor()
        self.mongodb = MongoDBManager()

        # 処理統計
        self.processed_files = 0
        self.processed_tweets = 0
        self.processed_articles = 0

    def process_jsonl_files(self, directory: Path = None) -> dict[str, Any]:
        """指定ディレクトリ内のJSONLファイルを処理（非同期メディア処理対応）"""
        try:
            # 既存のイベントループがあるかチェック
            asyncio.get_running_loop()
            # 既存ループがある場合はタスクとして実行
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._async_process_jsonl_files(directory))
                return future.result()
        except RuntimeError:
            # イベントループがない場合は通常通り実行
            return asyncio.run(self._async_process_jsonl_files(directory))

    async def _async_process_jsonl_files(self, directory: Path = None) -> dict[str, Any]:
        """指定ディレクトリ内のJSONLファイルを非同期処理"""
        # 統計をリセット
        self.processed_files = 0
        self.processed_tweets = 0
        self.processed_articles = 0

        if directory is None:
            directory = Path(settings.raw_data_dir)

        if not directory.exists():
            self.logger.warning(f"ディレクトリが存在しません: {directory}")
            return {
                "processed_files": 0,
                "processed_tweets": 0,
                "processed_articles": 0,
            }

        jsonl_files = list(directory.glob("*.jsonl"))

        if not jsonl_files:
            self.logger.info("処理対象のJSONLファイルがありません")
            return {
                "processed_files": 0,
                "processed_tweets": 0,
                "processed_articles": 0,
            }

        self.logger.info(f"{len(jsonl_files)}個のJSONLファイルを処理開始")

        processed_files = []
        async with media_processor:
            for filepath in jsonl_files:
                if await self._async_process_single_file(filepath):
                    processed_files.append(filepath)

        # DB挿入成功したファイルのみ削除
        if processed_files:
            self._delete_processed_files(processed_files)

        return {
            "processed_files": self.processed_files,
            "processed_tweets": self.processed_tweets,
            "processed_articles": self.processed_articles,
        }

    async def _async_process_single_file(self, filepath: Path) -> bool:
        """単一JSONLファイルの非同期処理（メディア処理付き）"""
        try:
            self.logger.info(f"ファイル処理開始: {filepath.name}")

            tweets = []
            articles = []

            # JSONLファイルを読み込み、分類
            for item in self.jsonl_processor.read_jsonl(filepath):
                if self._is_tweet_data(item):
                    tweets.append(item)
                elif self._is_article_data(item):
                    articles.append(item)

            # ツイートのメディア処理を実行
            if tweets:
                self.logger.info(f"ツイートのメディア処理を開始: {len(tweets)}件")
                processed_tweets = []

                for tweet in tweets:
                    try:
                        # メディア処理を実行（db_managerを渡す）
                        processed_tweet = await media_processor.process_tweet_media(tweet, self.mongodb)
                        processed_tweets.append(processed_tweet)
                    except Exception as e:
                        self.logger.warning(f"ツイート {tweet.get('id_str', 'unknown')} のメディア処理エラー: {e}")
                        # エラーでも元のツイートは保存
                        processed_tweets.append(tweet)

                tweets = processed_tweets

            # MongoDBに挿入
            success = True
            if tweets:
                inserted_tweets = self.mongodb.insert_tweets(tweets)
                if inserted_tweets == 0 and len(tweets) > 0:
                    success = False
                else:
                    self.processed_tweets += inserted_tweets

            if articles:
                inserted_articles = self.mongodb.insert_articles(articles)
                if inserted_articles == 0 and len(articles) > 0:
                    success = False
                else:
                    self.processed_articles += inserted_articles

            if success:
                self.processed_files += 1
                self.logger.info(f"ファイル処理完了: {filepath.name} (ツイート{len(tweets)}件, 記事{len(articles)}件)")
                return True
            else:
                self.logger.warning(f"ファイル処理失敗: {filepath.name} (DB挿入エラー)")
                return False

        except Exception as e:
            self.logger.error(f"ファイル処理エラー ({filepath}): {e}")
            return False

    def _process_single_file(self, filepath: Path) -> bool:
        """単一JSONLファイルの処理（非同期版のラッパー）"""
        return asyncio.run(self._async_process_single_file_wrapper(filepath))

    async def _async_process_single_file_wrapper(self, filepath: Path) -> bool:
        """単一ファイル処理の非同期ラッパー"""
        async with media_processor:
            return await self._async_process_single_file(filepath)

    def _is_tweet_data(self, item: dict) -> bool:
        """ツイートデータかどうかを判定"""
        tweet_indicators = ["id_str", "rest_id", "legacy", "core"]
        return any(key in item for key in tweet_indicators)

    def _is_article_data(self, item: dict) -> bool:
        """記事データかどうかを判定"""
        article_indicators = ["url", "cleaned_text", "title"]
        return "url" in item and any(key in item for key in article_indicators)

    def _delete_processed_files(self, files: list[Path]):
        """DB挿入成功したファイルを削除"""
        for filepath in files:
            try:
                filepath.unlink()
                self.logger.info(f"処理済みファイルを削除: {filepath.name}")
            except Exception as e:
                self.logger.error(f"ファイル削除エラー ({filepath}): {e}")

    def _move_processed_files(self, files: list[Path]):
        """処理済みファイルを移動（廃止予定）"""
        processed_dir = Path(settings.processed_data_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)

        for filepath in files:
            try:
                new_path = processed_dir / filepath.name
                filepath.rename(new_path)
                self.logger.debug(f"処理済みファイルを移動: {filepath.name}")
            except Exception as e:
                self.logger.error(f"ファイル移動エラー ({filepath}): {e}")


# グローバルインスタンス
jsonl_processor = JSONLProcessor()
mongodb_manager = MongoDBManager()
data_ingest_service = DataIngestService()
