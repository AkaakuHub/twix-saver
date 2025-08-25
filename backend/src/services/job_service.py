"""
スクレイピングジョブ管理サービス
ジョブの実行、監視、統計情報を管理
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.models.database import ScrapingJob, ScrapingJobStats, ScrapingJobStatus
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger


def get_jst_now():
    """JST（日本標準時）の現在時刻を取得"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst)


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
        target_usernames: list[str],
        scraper_account: Optional[str] = None,
        process_articles: bool = True,
        max_tweets: Optional[int] = None,
        specific_tweet_ids: Optional[list[str]] = None,
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
                specific_tweet_ids=specific_tweet_ids,
                created_at=datetime.utcnow(),
            )

            self.collection.insert_one(job.to_dict())
            self.logger.info(f"新しいスクレイピングジョブを作成: {job_id} (ターゲット: {', '.join(target_usernames)})")

            return job_id

        except PyMongoError as e:
            self.logger.error(f"ジョブ作成エラー: {e}")
            return None

    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """指定ジョブを取得"""
        try:
            doc = self.collection.find_one({"job_id": job_id})
            if doc:
                doc.pop("_id", None)
                return ScrapingJob.from_dict(doc)
            return None

        except PyMongoError as e:
            self.logger.error(f"ジョブ取得エラー ({job_id}): {e}")
            return None

    def get_jobs(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[ScrapingJob]:
        """ジョブ一覧を取得"""
        try:
            query = {}
            if status:
                query["status"] = status

            cursor = self.collection.find(query).sort("created_at", -1).skip(offset).limit(limit)

            jobs = []
            for doc in cursor:
                doc.pop("_id", None)
                jobs.append(ScrapingJob.from_dict(doc))

            return jobs

        except PyMongoError as e:
            self.logger.error(f"ジョブ一覧取得エラー: {e}")
            return []

    def get_recent_jobs(self, hours: int = 24) -> list[ScrapingJob]:
        """指定時間内の最近のジョブを取得"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            cursor = self.collection.find({"created_at": {"$gte": since}}).sort("created_at", -1)

            jobs = []
            for doc in cursor:
                doc.pop("_id", None)
                jobs.append(ScrapingJob.from_dict(doc))

            return jobs

        except PyMongoError as e:
            self.logger.error(f"最近のジョブ取得エラー: {e}")
            return []

    def get_running_jobs(self) -> list[ScrapingJob]:
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
                        "started_at": datetime.utcnow(),
                    },
                    "$push": {"logs": f"[{get_jst_now().strftime('%H:%M:%S')}] スクレイピングジョブを開始しました"},
                },
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
        final_logs: Optional[list[str]] = None,
    ) -> bool:
        """ジョブを完了状態に更新"""
        try:
            update_data = {
                "status": ScrapingJobStatus.COMPLETED.value,
                "completed_at": datetime.utcnow(),
                "stats": stats.__dict__
                if hasattr(stats, "__dict__")
                else stats.to_dict()
                if hasattr(stats, "to_dict")
                else vars(stats),
            }

            # 処理時間を計算
            job = self.get_job(job_id)
            if job and job.started_at:
                duration = (datetime.utcnow() - job.started_at).total_seconds()
                update_data["stats"]["processing_time_seconds"] = duration

            # 完了ログを追加
            completion_log = (
                f"[{get_jst_now().strftime('%H:%M:%S')}] "
                f"スクレイピングジョブが完了しました "
                f"(ツイート: {stats.tweets_collected}件, "
                f"記事: {stats.articles_extracted}件)"
            )

            update_operation = {"$set": update_data, "$push": {"logs": completion_log}}

            if final_logs:
                update_operation["$push"]["logs"] = {"$each": final_logs}

            result = self.collection.update_one({"job_id": job_id}, update_operation)

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
            error_log = f"[{get_jst_now().strftime('%H:%M:%S')}] エラー: {error_message}"

            result = self.collection.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": ScrapingJobStatus.FAILED.value,
                        "completed_at": datetime.utcnow(),
                    },
                    "$push": {"errors": error_log, "logs": error_log},
                    "$inc": {"stats.errors_count": 1},
                },
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
            cancel_log = f"[{get_jst_now().strftime('%H:%M:%S')}] ジョブがキャンセルされました"

            result = self.collection.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": ScrapingJobStatus.CANCELLED.value,
                        "completed_at": datetime.utcnow(),
                    },
                    "$push": {"logs": cancel_log},
                },
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

    def delete_job(self, job_id: str) -> bool:
        """ジョブを完全に削除"""
        try:
            result = self.collection.delete_one({"job_id": job_id})

            if result.deleted_count > 0:
                self.logger.info(f"ジョブを削除しました: {job_id}")
                return True
            else:
                self.logger.warning(f"削除対象のジョブが見つかりませんでした: {job_id}")
                return False

        except PyMongoError as e:
            self.logger.error(f"ジョブ削除エラー: {e}")
            return False

    def add_job_log(self, job_id: str, message: str) -> bool:
        """ジョブにログメッセージを追加"""
        try:
            log_entry = f"[{get_jst_now().strftime('%H:%M:%S')}] {message}"

            result = self.collection.update_one({"job_id": job_id}, {"$push": {"logs": log_entry}})

            return result.matched_count > 0

        except PyMongoError as e:
            self.logger.error(f"ジョブログ追加エラー ({job_id}): {e}")
            return False

    def get_job_logs(self, job_id: str, last_timestamp: Optional[str] = None) -> dict[str, Any]:
        """ジョブのログを取得（リアルタイム表示用）"""
        try:
            job_doc = self.collection.find_one({"job_id": job_id}, {"logs": 1, "status": 1})

            if not job_doc:
                return {"logs": [], "last_timestamp": None, "has_more": False}

            logs = job_doc.get("logs", [])

            # タイムスタンプでフィルタリング
            if last_timestamp:
                try:
                    # ログの形式: [HH:MM:SS] メッセージ
                    filtered_logs = []
                    for log in logs:
                        if log.startswith("[") and "]" in log:
                            timestamp_part = log.split("]")[0][1:]  # [HH:MM:SS] から HH:MM:SS を抽出
                            if timestamp_part > last_timestamp:
                                filtered_logs.append(log)
                        else:
                            # タイムスタンプがない場合は含める
                            filtered_logs.append(log)
                    logs = filtered_logs
                except Exception:  # noqa: S110
                    # エラーの場合はすべてのログを返す
                    pass

            # 最新のタイムスタンプを取得
            latest_timestamp = None
            if logs:
                for log in reversed(logs):  # 最新から検索
                    if log.startswith("[") and "]" in log:
                        latest_timestamp = log.split("]")[0][1:]
                        break

            return {
                "logs": logs,
                "last_timestamp": latest_timestamp,
                "has_more": len(logs) > 0,
            }

        except PyMongoError as e:
            self.logger.error(f"ジョブログ取得エラー ({job_id}): {e}")
            return {"logs": [], "last_timestamp": None, "has_more": False}

    def update_job_stats(
        self,
        job_id: str,
        tweets_collected: int = 0,
        articles_extracted: int = 0,
        media_downloaded: int = 0,
        pages_scrolled: int = 0,
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
                },
            )

            return result.matched_count > 0

        except PyMongoError as e:
            self.logger.error(f"ジョブ統計更新エラー ({job_id}): {e}")
            return False

    def get_job_statistics(self, days: int = 30) -> dict[str, Any]:
        """ジョブ統計情報を取得"""
        try:
            since = datetime.utcnow() - timedelta(days=days)

            # 基本統計
            pipeline = [
                {"$match": {"created_at": {"$gte": since.isoformat()}}},
                {
                    "$group": {
                        "_id": None,
                        "total_jobs": {"$sum": 1},
                        "completed_jobs": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$eq": [
                                            "$status",
                                            ScrapingJobStatus.COMPLETED.value,
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                        "failed_jobs": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$eq": [
                                            "$status",
                                            ScrapingJobStatus.FAILED.value,
                                        ]
                                    },
                                    1,
                                    0,
                                ]
                            }
                        },
                        "total_tweets": {"$sum": "$stats.tweets_collected"},
                        "total_articles": {"$sum": "$stats.articles_extracted"},
                        "total_processing_time": {"$sum": "$stats.processing_time_seconds"},
                    }
                },
            ]

            result = list(self.collection.aggregate(pipeline))

            if result:
                stats = result[0]
                stats.pop("_id", None)

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
                                    "date": "$created_at",
                                }
                            },
                            "jobs_count": {"$sum": 1},
                            "tweets_count": {"$sum": "$stats.tweets_collected"},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ]

                daily_stats = list(self.collection.aggregate(daily_pipeline))
                stats["daily_stats"] = {
                    item["_id"]: {
                        "jobs": item["jobs_count"],
                        "tweets": item["tweets_count"],
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
                "daily_stats": {},
            }

        except PyMongoError as e:
            self.logger.error(f"ジョブ統計取得エラー: {e}")
            return {}

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """古いジョブを削除"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = self.collection.delete_many(
                {
                    "created_at": {"$lt": cutoff_date},
                    "status": {
                        "$in": [
                            ScrapingJobStatus.COMPLETED.value,
                            ScrapingJobStatus.FAILED.value,
                        ]
                    },
                }
            )

            deleted_count = result.deleted_count
            if deleted_count > 0:
                self.logger.info(f"古いジョブを削除: {deleted_count}件")

            return deleted_count

        except PyMongoError as e:
            self.logger.error(f"ジョブクリーンアップエラー: {e}")
            return 0


# グローバルインスタンス
job_service = JobService()
