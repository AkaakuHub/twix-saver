"""
データアーキテクチャとストレージシステム
JSONLファイル処理とMongoDBへのデータインジェスト
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Any
from urllib.parse import urlparse

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from src.config.settings import settings
from src.utils.logger import setup_logger


class JSONLProcessor:
    """JSON Lines ファイルの処理クラス"""
    
    def __init__(self):
        self.logger = setup_logger("jsonl_processor")
    
    def write_jsonl(self, data: List[Dict], filepath: Path) -> int:
        """データをJSONL形式で書き込み"""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'a', encoding='utf-8') as f:
                for item in data:
                    json_line = json.dumps(item, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            self.logger.info(f"JSONLファイルに{len(data)}件を書き込み: {filepath}")
            return len(data)
            
        except Exception as e:
            self.logger.error(f"JSONL書き込みエラー ({filepath}): {e}")
            return 0
    
    def read_jsonl(self, filepath: Path) -> Iterator[Dict]:
        """JSONLファイルを読み込み（ジェネレータ）"""
        try:
            if not filepath.exists():
                self.logger.warning(f"JSONLファイルが存在しません: {filepath}")
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
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
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return sum(1 for line in f if line.strip())
                
        except Exception as e:
            self.logger.error(f"行数カウントエラー ({filepath}): {e}")
            return 0
    
    def validate_jsonl(self, filepath: Path) -> Dict[str, Any]:
        """JSONLファイルの検証"""
        result = {
            "valid_lines": 0,
            "invalid_lines": 0,
            "total_lines": 0,
            "errors": []
        }
        
        try:
            if not filepath.exists():
                result["errors"].append(f"ファイルが存在しません: {filepath}")
                return result
            
            with open(filepath, 'r', encoding='utf-8') as f:
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
            
            self.logger.info(f"JSONL検証完了 ({filepath}): "
                           f"有効{result['valid_lines']}件, 無効{result['invalid_lines']}件")
            
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
            self.client.admin.command('ping')
            
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
    
    @property
    def is_connected(self) -> bool:
        """接続状態のチェック"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except:
            pass
        return False
    
    def insert_tweets(self, tweets: List[Dict]) -> int:
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
                tweet_id = (tweet.get("id_str") or 
                           tweet.get("rest_id") or 
                           tweet.get("id"))
                
                if not tweet_id:
                    self.logger.warning("ツイートIDが見つかりません")
                    continue
                
                # upsert操作を作成
                filter_query = {"$or": [{"id_str": tweet_id}, {"rest_id": tweet_id}]}
                
                operations.append(
                    UpdateOne(
                        filter_query,
                        {"$set": tweet},
                        upsert=True
                    )
                )
            
            if operations:
                result = self.tweets_collection.bulk_write(operations, ordered=False)
                
                inserted = result.upserted_count
                updated = result.modified_count
                
                self.logger.info(f"ツイートデータ処理完了: 新規{inserted}件, 更新{updated}件")
                return inserted + updated
            
        except PyMongoError as e:
            self.logger.error(f"ツイート挿入エラー: {e}")
        
        return 0
    
    def insert_articles(self, articles: List[Dict]) -> int:
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
                
                operations.append(
                    UpdateOne(
                        {"url": article["url"]},
                        {"$set": article},
                        upsert=True
                    )
                )
            
            if operations:
                result = self.articles_collection.bulk_write(operations, ordered=False)
                
                inserted = result.upserted_count
                updated = result.modified_count
                
                self.logger.info(f"記事データ処理完了: 新規{inserted}件, 更新{updated}件")
                return inserted + updated
                
        except PyMongoError as e:
            self.logger.error(f"記事挿入エラー: {e}")
        
        return 0
    
    def get_tweet_stats(self) -> Dict[str, Any]:
        """ツイートコレクションの統計情報"""
        if not self.is_connected:
            return {}
        
        try:
            total_tweets = self.tweets_collection.count_documents({})
            
            # 最新ツイートの日時
            latest_tweet = self.tweets_collection.find_one(
                {}, sort=[("scraped_at", -1)]
            )
            
            # スクレイパー別統計
            scraper_stats = list(
                self.tweets_collection.aggregate([
                    {"$group": {
                        "_id": "$scraper_account",
                        "count": {"$sum": 1}
                    }},
                    {"$sort": {"count": -1}}
                ])
            )
            
            return {
                "total_tweets": total_tweets,
                "latest_scraped": latest_tweet.get("scraped_at") if latest_tweet else None,
                "scraper_stats": scraper_stats
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
    
    def process_jsonl_files(self, directory: Path = None) -> Dict[str, Any]:
        """指定ディレクトリ内のJSONLファイルを処理"""
        if directory is None:
            directory = Path(settings.raw_data_dir)
        
        if not directory.exists():
            self.logger.warning(f"ディレクトリが存在しません: {directory}")
            return {"processed_files": 0}
        
        jsonl_files = list(directory.glob("*.jsonl"))
        
        if not jsonl_files:
            self.logger.info("処理対象のJSONLファイルがありません")
            return {"processed_files": 0}
        
        self.logger.info(f"{len(jsonl_files)}個のJSONLファイルを処理開始")
        
        for filepath in jsonl_files:
            self._process_single_file(filepath)
        
        # 処理済みファイルを移動
        self._move_processed_files(jsonl_files)
        
        return {
            "processed_files": self.processed_files,
            "processed_tweets": self.processed_tweets,
            "processed_articles": self.processed_articles
        }
    
    def _process_single_file(self, filepath: Path):
        """単一JSONLファイルの処理"""
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
            
            # MongoDBに挿入
            if tweets:
                inserted_tweets = self.mongodb.insert_tweets(tweets)
                self.processed_tweets += inserted_tweets
            
            if articles:
                inserted_articles = self.mongodb.insert_articles(articles)
                self.processed_articles += inserted_articles
            
            self.processed_files += 1
            
            self.logger.info(f"ファイル処理完了: {filepath.name} "
                           f"(ツイート{len(tweets)}件, 記事{len(articles)}件)")
            
        except Exception as e:
            self.logger.error(f"ファイル処理エラー ({filepath}): {e}")
    
    def _is_tweet_data(self, item: Dict) -> bool:
        """ツイートデータかどうかを判定"""
        tweet_indicators = ["id_str", "rest_id", "legacy", "core"]
        return any(key in item for key in tweet_indicators)
    
    def _is_article_data(self, item: Dict) -> bool:
        """記事データかどうかを判定"""
        article_indicators = ["url", "cleaned_text", "title"]
        return "url" in item and any(key in item for key in article_indicators)
    
    def _move_processed_files(self, files: List[Path]):
        """処理済みファイルを移動"""
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