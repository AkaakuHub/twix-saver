"""
スクレイピングジョブ管理サービス
ジョブの実行、監視、統計情報を管理
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.models.database import ScrapingJob, ScrapingJobStatus, ScrapingJobStats
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger


class JobService:
    """スクレイピングジョブ管理サービス"""
    
    def __init__(self):
        self.logger = setup_logger("job_service")
        self.collection: Collection = mongodb_manager.db["scraping_jobs"]
        
        # インデックス作成
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """必要なインデックスを作成"""
        try:
            self.collection.create_index("job_id", unique=True)
            self.collection.create_index("status")
            self.collection.create_index("created_at")
            self.collection.create_index("target_usernames")
            self.collection.create_index([("status", 1), ("created_at", -1)])
            
            self.logger.info("スクレイピングジョブインデックスを作成しました")
        except PyMongoError as e:
            self.logger.error(f"インデックス作成エラー: {e}")
    
    def create_job(
        self,
        target_usernames: List[str],
        scraper_account: Optional[str] = None,
        process_articles: bool = True,
        max_tweets: Optional[int] = None
    ) -> Optional[str]:
        """新しいスクレイピングジョブを作成"""
        try:
            job_id = str(uuid.uuid4())
            
            job = ScrapingJob(
                job_id=job_id,
                target_usernames=target_usernames,
                scraper_account=scraper_account,
                process_articles=process_articles,
                max_tweets=max_tweets,
                created_at=datetime.utcnow()
            )
            
            self.collection.insert_one(job.to_dict())
            self.logger.info(f"新しいスクレイピングジョブを作成: {job_id} "
                           f"(ターゲット: {', '.join(target_usernames)})")
            
            return job_id
            
        except PyMongoError as e:
            self.logger.error(f"ジョブ作成エラー: {e}")
            return None
    
    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """指定ジョブを取得"""
        try:
            doc = self.collection.find_one({"job_id": job_id})
            if doc:
                doc.pop('_id', None)
                return ScrapingJob.from_dict(doc)
            return None
            
        except PyMongoError as e:
            self.logger.error(f"ジョブ取得エラー ({job_id}): {e}")
            return None
    
    def get_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapingJob]:
        """ジョブ一覧を取得"""
        try:
            query = {}
            if status:
                query["status"] = status
            
            cursor = (self.collection
                     .find(query)
                     .sort("created_at", -1)
                     .skip(offset)
                     .limit(limit))
            
            jobs = []
            for doc in cursor:
                doc.pop('_id', None)
                jobs.append(ScrapingJob.from_dict(doc))
            
            return jobs
            
        except PyMongoError as e:
            self.logger.error(f"ジョブ一覧取得エラー: {e}")
            return []
    
    def get_recent_jobs(self, hours: int = 24) -> List[ScrapingJob]:
        """指定時間内の最近のジョブを取得"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            cursor = (self.collection
                     .find({"created_at": {"$gte": since}})
                     .sort("created_at", -1))
            
            jobs = []
            for doc in cursor:
                doc.pop('_id', None)
                jobs.append(ScrapingJob.from_dict(doc))
            
            return jobs
            
        except PyMongoError as e:
            self.logger.error(f"最近のジョブ取得エラー: {e}")
            return []
    
    def get_running_jobs(self) -> List[ScrapingJob]:
        """実行中のジョブを取得"""
        return self.get_jobs(status=ScrapingJobStatus.RUNNING.value)
    
    def start_job(self, job_id: str) -> bool:
        """ジョブを開始状態に更新"""
        try:
            result = self.collection.update_one(
                {"job_id": job_id, "status": ScrapingJobStatus.PENDING.value},
                {
                    "$set": {
                        "status": ScrapingJobStatus.RUNNING.value,
                        "started_at": datetime.utcnow()
                    },
                    "$push": {
                        "logs": f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                               "スクレイピングジョブを開始しました"
                    }
                }
            )
            
            if result.matched_count > 0:
                self.logger.info(f"ジョブを開始: {job_id}")
                return True
            else:
                self.logger.warning(f"開始可能なジョブが見つかりません: {job_id}")
                return False
                
        except PyMongoError as e:
            self.logger.error(f"ジョブ開始エラー ({job_id}): {e}")
            return False
    
    def complete_job(
        self,
        job_id: str,
        stats: ScrapingJobStats,
        final_logs: Optional[List[str]] = None
    ) -> bool:
        """ジョブを完了状態に更新"""
        try:
            update_data = {
                "status": ScrapingJobStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
                "stats": stats.__dict__ if hasattr(stats, '__dict__') else stats.to_dict() if hasattr(stats, 'to_dict') else vars(stats)
            }
            
            # 処理時間を計算
            job = self.get_job(job_id)
            if job and job.started_at:
                duration = (datetime.utcnow() - job.started_at).total_seconds()
                update_data["stats"]["processing_time_seconds"] = duration
            
            # 完了ログを追加
            completion_log = (f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                             f"スクレイピングジョブが完了しました "
                             f"(ツイート: {stats.tweets_collected}件, "
                             f"記事: {stats.articles_extracted}件)")
            
            update_operation = {
                "$set": update_data,
                "$push": {"logs": completion_log}
            }
            
            if final_logs:
                update_operation["$push"]["logs"] = {"$each": final_logs}
            
            result = self.collection.update_one(
                {"job_id": job_id},
                update_operation
            )
            
            if result.matched_count > 0:
                self.logger.info(f"ジョブを完了: {job_id}")
                return True
            else:
                self.logger.warning(f"完了対象ジョブが見つかりません: {job_id}")
                return False
                
        except PyMongoError as e:
            self.logger.error(f"ジョブ完了エラー ({job_id}): {e}")
            return False
    
    def fail_job(self, job_id: str, error_message: str) -> bool:
        """ジョブを失敗状態に更新"""
        try:
            error_log = (f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                        f"エラー: {error_message}")
            
            result = self.collection.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": ScrapingJobStatus.FAILED.value,
                        "completed_at": datetime.utcnow()
                    },
                    "$push": {
                        "errors": error_log,
                        "logs": error_log
                    },
                    "$inc": {"stats.errors_count": 1}
                }
            )
            
            if result.matched_count > 0:
                self.logger.info(f"ジョブを失敗状態に更新: {job_id}")
                return True
            else:
                self.logger.warning(f"失敗対象ジョブが見つかりません: {job_id}")
                return False
                
        except PyMongoError as e:
            self.logger.error(f"ジョブ失敗更新エラー ({job_id}): {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル状態に更新"""
        try:
            cancel_log = (f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                         f"ジョブがキャンセルされました")
            
            result = self.collection.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": ScrapingJobStatus.CANCELLED.value,
                        "completed_at": datetime.utcnow()
                    },
                    "$push": {
                        "logs": cancel_log
                    }
                }
            )
            
            if result.matched_count > 0:
                self.logger.info(f"ジョブをキャンセル: {job_id}")
                return True
            else:
                self.logger.warning(f"キャンセル対象ジョブが見つかりません: {job_id}")
                return False
                
        except PyMongoError as e:
            self.logger.error(f"ジョブキャンセルエラー ({job_id}): {e}")
            return False
    
    def add_job_log(self, job_id: str, message: str) -> bool:
        """ジョブにログメッセージを追加"""
        try:
            log_entry = f"[{datetime.utcnow().strftime('%H:%M:%S')}] {message}"
            
            result = self.collection.update_one(
                {"job_id": job_id},
                {"$push": {"logs": log_entry}}
            )
            
            return result.matched_count > 0
            
        except PyMongoError as e:
            self.logger.error(f"ジョブログ追加エラー ({job_id}): {e}")
            return False
    
    def update_job_stats(
        self,
        job_id: str,
        tweets_collected: int = 0,
        articles_extracted: int = 0,
        media_downloaded: int = 0,
        pages_scrolled: int = 0
    ) -> bool:
        """ジョブ統計を更新"""
        try:
            result = self.collection.update_one(
                {"job_id": job_id},
                {
                    "$inc": {
                        "stats.tweets_collected": tweets_collected,
                        "stats.articles_extracted": articles_extracted,
                        "stats.media_downloaded": media_downloaded,
                        "stats.pages_scrolled": pages_scrolled,
                    }
                }
            )
            
            return result.matched_count > 0
            
        except PyMongoError as e:
            self.logger.error(f"ジョブ統計更新エラー ({job_id}): {e}")
            return False
    
    def get_job_statistics(self, days: int = 30) -> Dict[str, Any]:
        """ジョブ統計情報を取得"""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            
            # 基本統計
            pipeline = [
                {"$match": {"created_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": None,
                        "total_jobs": {"$sum": 1},
                        "completed_jobs": {
                            "$sum": {"$cond": [
                                {"$eq": ["$status", ScrapingJobStatus.COMPLETED.value]}, 1, 0
                            ]}
                        },
                        "failed_jobs": {
                            "$sum": {"$cond": [
                                {"$eq": ["$status", ScrapingJobStatus.FAILED.value]}, 1, 0
                            ]}
                        },
                        "total_tweets": {"$sum": "$stats.tweets_collected"},
                        "total_articles": {"$sum": "$stats.articles_extracted"},
                        "total_processing_time": {"$sum": "$stats.processing_time_seconds"}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                stats.pop('_id', None)
                
                # 成功率を計算
                if stats["total_jobs"] > 0:
                    stats["success_rate"] = stats["completed_jobs"] / stats["total_jobs"] * 100
                else:
                    stats["success_rate"] = 0
                
                # 平均処理時間を計算
                if stats["completed_jobs"] > 0:
                    stats["avg_processing_time"] = stats["total_processing_time"] / stats["completed_jobs"]
                else:
                    stats["avg_processing_time"] = 0
                
                # 日別統計
                daily_pipeline = [
                    {"$match": {"created_at": {"$gte": since}}},
                    {
                        "$group": {
                            "_id": {
                                "$dateToString": {
                                    "format": "%Y-%m-%d",
                                    "date": "$created_at"
                                }
                            },
                            "jobs_count": {"$sum": 1},
                            "tweets_count": {"$sum": "$stats.tweets_collected"}
                        }
                    },
                    {"$sort": {"_id": 1}}
                ]
                
                daily_stats = list(self.collection.aggregate(daily_pipeline))
                stats["daily_stats"] = {
                    item["_id"]: {
                        "jobs": item["jobs_count"],
                        "tweets": item["tweets_count"]
                    }
                    for item in daily_stats
                }
                
                return stats
            
            return {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "total_tweets": 0,
                "total_articles": 0,
                "success_rate": 0,
                "avg_processing_time": 0,
                "daily_stats": {}
            }
            
        except PyMongoError as e:
            self.logger.error(f"ジョブ統計取得エラー: {e}")
            return {}
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """古いジョブを削除"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = self.collection.delete_many({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": [
                    ScrapingJobStatus.COMPLETED.value,
                    ScrapingJobStatus.FAILED.value
                ]}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                self.logger.info(f"古いジョブを削除: {deleted_count}件")
            
            return deleted_count
            
        except PyMongoError as e:
            self.logger.error(f"ジョブクリーンアップエラー: {e}")
            return 0


# グローバルインスタンス
job_service = JobService()