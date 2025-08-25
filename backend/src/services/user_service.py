"""
ターゲットユーザー管理サービス
データベース操作とビジネスロジックを提供
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.models.database import TargetUser, UserPriority
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger


class UserService:
    """ターゲットユーザー管理サービス"""

    def __init__(self):
        self.logger = setup_logger("user_service")
        self.collection: Collection = mongodb_manager.db["target_users"]

        # インデックス作成
        self._ensure_indexes()

    def _ensure_indexes(self):
        """必要なインデックスを作成"""
        try:
            self.collection.create_index("username", unique=True)
            self.collection.create_index("active")
            self.collection.create_index("priority")
            self.collection.create_index("last_scraped_at")
            self.collection.create_index([("active", 1), ("priority", -1)])

            self.logger.info("ターゲットユーザーインデックスを作成しました")
        except PyMongoError as e:
            self.logger.error(f"インデックス作成エラー: {e}")

    def get_all_users(self, include_inactive: bool = False) -> list[TargetUser]:
        """全ユーザーを取得"""
        try:
            query = {} if include_inactive else {"active": True}
            cursor = self.collection.find(query).sort([("priority", -1), ("username", 1)])

            users = []
            for doc in cursor:
                doc.pop("_id", None)  # MongoDBの_idを除去
                users.append(TargetUser.from_dict(doc))

            self.logger.info(f"ユーザーを取得: {len(users)}件")
            return users

        except PyMongoError as e:
            self.logger.error(f"ユーザー取得エラー: {e}")
            return []

    def get_active_users(self) -> list[TargetUser]:
        """アクティブなユーザーのみを取得"""
        return self.get_all_users(include_inactive=False)

    def get_user(self, username: str) -> Optional[TargetUser]:
        """指定ユーザーを取得"""
        try:
            doc = self.collection.find_one({"username": username})
            if doc:
                doc.pop("_id", None)
                return TargetUser.from_dict(doc)
            return None

        except PyMongoError as e:
            self.logger.error(f"ユーザー取得エラー ({username}): {e}")
            return None

    def add_user(
        self,
        username: str,
        display_name: Optional[str] = None,
        priority: int = UserPriority.NORMAL.value,
        active: bool = True,
    ) -> bool:
        """新しいユーザーを追加"""
        try:
            # 既存チェック
            if self.get_user(username):
                self.logger.warning(f"ユーザーは既に存在します: {username}")
                return False

            user = TargetUser(
                username=username,
                display_name=display_name,
                priority=priority,
                active=active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.collection.insert_one(user.to_dict())
            self.logger.info(f"新しいユーザーを追加: {username}")
            return True

        except PyMongoError as e:
            self.logger.error(f"ユーザー追加エラー ({username}): {e}")
            return False

    def update_user(self, username: str, updates: dict[str, Any]) -> bool:
        """ユーザー情報を更新"""
        try:
            # updated_atを自動設定
            updates["updated_at"] = datetime.utcnow()

            result = self.collection.update_one({"username": username}, {"$set": updates})

            if result.matched_count > 0:
                self.logger.info(f"ユーザーを更新: {username}")
                return True
            else:
                self.logger.warning(f"更新対象ユーザーが見つかりません: {username}")
                return False

        except PyMongoError as e:
            self.logger.error(f"ユーザー更新エラー ({username}): {e}")
            return False

    def delete_user(self, username: str) -> bool:
        """ユーザーを削除"""
        try:
            result = self.collection.delete_one({"username": username})

            if result.deleted_count > 0:
                self.logger.info(f"ユーザーを削除: {username}")
                return True
            else:
                self.logger.warning(f"削除対象ユーザーが見つかりません: {username}")
                return False

        except PyMongoError as e:
            self.logger.error(f"ユーザー削除エラー ({username}): {e}")
            return False

    def activate_user(self, username: str) -> bool:
        """ユーザーを有効化"""
        return self.update_user(username, {"active": True})

    def deactivate_user(self, username: str) -> bool:
        """ユーザーを無効化"""
        return self.update_user(username, {"active": False})

    def update_user_priority(self, username: str, priority: int) -> bool:
        """ユーザーの優先度を更新"""
        if priority not in [p.value for p in UserPriority]:
            self.logger.error(f"無効な優先度: {priority}")
            return False

        return self.update_user(username, {"priority": priority})

    def update_scraping_stats(
        self,
        username: str,
        tweets_collected: int = 0,
        articles_extracted: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """スクレイピング統計を更新"""
        try:
            updates = {
                "last_scraped_at": datetime.utcnow(),
                "$inc": {
                    "total_tweets": tweets_collected,
                    "total_articles": articles_extracted,
                },
            }

            if error_message:
                updates["last_error"] = error_message

            result = self.collection.update_one({"username": username}, updates)

            if result.matched_count > 0:
                self.logger.debug(f"統計を更新: {username} (ツイート+{tweets_collected}, 記事+{articles_extracted})")
                return True

            return False

        except PyMongoError as e:
            self.logger.error(f"統計更新エラー ({username}): {e}")
            return False

    def get_users_by_priority(self, min_priority: int = UserPriority.NORMAL.value) -> list[TargetUser]:
        """指定優先度以上のアクティブユーザーを取得"""
        try:
            cursor = self.collection.find(
                {
                    "active": True,
                    "scraping_enabled": True,
                    "priority": {"$gte": min_priority},
                }
            ).sort("priority", -1)

            users = []
            for doc in cursor:
                doc.pop("_id", None)
                users.append(TargetUser.from_dict(doc))

            return users

        except PyMongoError as e:
            self.logger.error(f"優先度別ユーザー取得エラー: {e}")
            return []

    def get_user_stats(self) -> dict[str, Any]:
        """ユーザー統計情報を取得"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_users": {"$sum": 1},
                        "active_users": {"$sum": {"$cond": [{"$eq": ["$active", True]}, 1, 0]}},
                        "total_tweets": {"$sum": "$total_tweets"},
                        "total_articles": {"$sum": "$total_articles"},
                    }
                }
            ]

            result = list(self.collection.aggregate(pipeline))

            if result:
                stats = result[0]
                stats.pop("_id", None)

                # 優先度別統計
                priority_stats = list(
                    self.collection.aggregate(
                        [
                            {"$match": {"active": True}},
                            {"$group": {"_id": "$priority", "count": {"$sum": 1}}},
                            {"$sort": {"_id": -1}},
                        ]
                    )
                )

                stats["priority_distribution"] = {str(stat["_id"]): stat["count"] for stat in priority_stats}

                return stats

            return {
                "total_users": 0,
                "active_users": 0,
                "total_tweets": 0,
                "total_articles": 0,
                "priority_distribution": {},
            }

        except PyMongoError as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {}

    def search_users(self, query: str) -> list[TargetUser]:
        """ユーザー検索"""
        try:
            search_filter = {
                "$or": [
                    {"username": {"$regex": query, "$options": "i"}},
                    {"display_name": {"$regex": query, "$options": "i"}},
                ]
            }

            cursor = self.collection.find(search_filter).sort("username", 1)

            users = []
            for doc in cursor:
                doc.pop("_id", None)
                users.append(TargetUser.from_dict(doc))

            return users

        except PyMongoError as e:
            self.logger.error(f"ユーザー検索エラー: {e}")
            return []

    def migrate_scraping_interval(self, default_interval: int = 30) -> dict[str, int]:
        """既存ユーザーにscraping_interval_minutesフィールドを追加するマイグレーション"""
        try:
            # scraping_interval_minutesフィールドが存在しないユーザーを検索
            users_to_migrate = list(
                self.collection.find(
                    {"$or": [{"scraping_interval_minutes": {"$exists": False}}, {"scraping_interval_minutes": None}]}
                )
            )

            if not users_to_migrate:
                self.logger.info("マイグレーション対象のユーザーはありません")
                return {"migrated": 0, "total": 0}

            migrated_count = 0
            for user_doc in users_to_migrate:
                try:
                    # 特別なユーザーには個別設定
                    if user_doc.get("username") == "raven_koekora":
                        interval = 30  # @raven_koekoraには30分間隔
                    else:
                        interval = default_interval

                    result = self.collection.update_one(
                        {"username": user_doc["username"]},
                        {"$set": {"scraping_interval_minutes": interval, "updated_at": datetime.utcnow()}},
                    )

                    if result.modified_count > 0:
                        migrated_count += 1
                        self.logger.info(f"ユーザーをマイグレーション: {user_doc['username']} -> {interval}分")

                except PyMongoError as e:
                    self.logger.error(f"ユーザーマイグレーションエラー ({user_doc.get('username', 'unknown')}): {e}")

            self.logger.info(f"マイグレーション完了: {migrated_count}/{len(users_to_migrate)}件")

            return {"migrated": migrated_count, "total": len(users_to_migrate)}

        except PyMongoError as e:
            self.logger.error(f"マイグレーション処理エラー: {e}")
            return {"migrated": 0, "total": 0, "error": str(e)}

    def get_users_due_for_scraping(self, exclude_running_jobs: bool = True) -> list[TargetUser]:
        """実行すべきアカウントを取得（アカウント別実行間隔に基づく）"""
        try:
            current_time = datetime.utcnow()

            # アクティブでスクレイピング有効なユーザーを取得
            query = {"active": True, "scraping_enabled": True, "scraping_interval_minutes": {"$exists": True, "$gt": 0}}

            all_users = list(self.collection.find(query))
            due_users = []

            for user_doc in all_users:
                try:
                    user = TargetUser.from_dict(user_doc)

                    # 最後のスクレイピング時刻から実行間隔が経過したかチェック
                    if user.last_scraped_at is None:
                        # 初回実行の場合はすぐに実行対象
                        due_users.append(user)
                        self.logger.debug(f"初回実行対象: {user.username}")
                        continue

                    # 次回実行予定時刻を計算
                    next_run_time = user.last_scraped_at + timedelta(minutes=user.scraping_interval_minutes)

                    if current_time >= next_run_time:
                        due_users.append(user)
                        elapsed_minutes = (current_time - user.last_scraped_at).total_seconds() / 60
                        self.logger.debug(
                            f"実行対象: {user.username} "
                            f"(間隔: {user.scraping_interval_minutes}分, "
                            f"最終実行から: {elapsed_minutes:.1f}分経過)"
                        )

                except Exception as e:
                    self.logger.error(f"ユーザー実行時刻判定エラー ({user_doc.get('username', 'unknown')}): {e}")

            # 実行中ジョブの除外処理
            if exclude_running_jobs and due_users:
                due_users = self._exclude_users_with_running_jobs(due_users)

            if due_users:
                usernames = [user.username for user in due_users]
                self.logger.info(f"実行対象アカウント: {len(due_users)}件 ({', '.join(usernames)})")
            else:
                self.logger.debug("現在実行対象のアカウントはありません")

            return due_users

        except PyMongoError as e:
            self.logger.error(f"実行対象ユーザー取得エラー: {e}")
            return []

    def _exclude_users_with_running_jobs(self, users: list[TargetUser]) -> list[TargetUser]:
        """実行中ジョブがあるユーザーを除外"""
        try:
            from src.services.job_service import job_service

            # 実行中ジョブのターゲットユーザーを取得
            running_jobs = job_service.get_running_jobs()
            running_usernames = set()

            for job in running_jobs:
                running_usernames.update(job.target_usernames)

            # 実行中でないユーザーのみを返す
            filtered_users = []
            for user in users:
                if user.username not in running_usernames:
                    filtered_users.append(user)
                else:
                    self.logger.debug(f"実行中ジョブがあるため除外: {user.username}")

            return filtered_users

        except Exception as e:
            self.logger.error(f"実行中ジョブチェックエラー: {e}")
            # エラーの場合は元のリストをそのまま返す
            return users


# グローバルインスタンス
user_service = UserService()
