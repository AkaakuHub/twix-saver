"""
ターゲットユーザー管理サービス
データベース操作とビジネスロジックを提供
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
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
    
    def get_all_users(self, include_inactive: bool = False) -> List[TargetUser]:
        """全ユーザーを取得"""
        try:
            query = {} if include_inactive else {"active": True}
            cursor = self.collection.find(query).sort([
                ("priority", -1),
                ("username", 1)
            ])
            
            users = []
            for doc in cursor:
                doc.pop('_id', None)  # MongoDBの_idを除去
                users.append(TargetUser.from_dict(doc))
            
            self.logger.info(f"ユーザーを取得: {len(users)}件")
            return users
            
        except PyMongoError as e:
            self.logger.error(f"ユーザー取得エラー: {e}")
            return []
    
    def get_active_users(self) -> List[TargetUser]:
        """アクティブなユーザーのみを取得"""
        return self.get_all_users(include_inactive=False)
    
    def get_user(self, username: str) -> Optional[TargetUser]:
        """指定ユーザーを取得"""
        try:
            doc = self.collection.find_one({"username": username})
            if doc:
                doc.pop('_id', None)
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
        active: bool = True
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
                updated_at=datetime.utcnow()
            )
            
            self.collection.insert_one(user.to_dict())
            self.logger.info(f"新しいユーザーを追加: {username}")
            return True
            
        except PyMongoError as e:
            self.logger.error(f"ユーザー追加エラー ({username}): {e}")
            return False
    
    def update_user(self, username: str, updates: Dict[str, Any]) -> bool:
        """ユーザー情報を更新"""
        try:
            # updated_atを自動設定
            updates["updated_at"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"username": username},
                {"$set": updates}
            )
            
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
        error_message: Optional[str] = None
    ) -> bool:
        """スクレイピング統計を更新"""
        try:
            updates = {
                "last_scraped_at": datetime.utcnow(),
                "$inc": {
                    "total_tweets": tweets_collected,
                    "total_articles": articles_extracted
                }
            }
            
            if error_message:
                updates["last_error"] = error_message
            
            result = self.collection.update_one(
                {"username": username},
                updates
            )
            
            if result.matched_count > 0:
                self.logger.debug(f"統計を更新: {username} "
                                f"(ツイート+{tweets_collected}, 記事+{articles_extracted})")
                return True
                
            return False
            
        except PyMongoError as e:
            self.logger.error(f"統計更新エラー ({username}): {e}")
            return False
    
    def get_users_by_priority(self, min_priority: int = UserPriority.NORMAL.value) -> List[TargetUser]:
        """指定優先度以上のアクティブユーザーを取得"""
        try:
            cursor = self.collection.find({
                "active": True,
                "scraping_enabled": True,
                "priority": {"$gte": min_priority}
            }).sort("priority", -1)
            
            users = []
            for doc in cursor:
                doc.pop('_id', None)
                users.append(TargetUser.from_dict(doc))
            
            return users
            
        except PyMongoError as e:
            self.logger.error(f"優先度別ユーザー取得エラー: {e}")
            return []
    
    def get_user_stats(self) -> Dict[str, Any]:
        """ユーザー統計情報を取得"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_users": {"$sum": 1},
                        "active_users": {
                            "$sum": {"$cond": [{"$eq": ["$active", True]}, 1, 0]}
                        },
                        "total_tweets": {"$sum": "$total_tweets"},
                        "total_articles": {"$sum": "$total_articles"}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                stats.pop('_id', None)
                
                # 優先度別統計
                priority_stats = list(self.collection.aggregate([
                    {"$match": {"active": True}},
                    {"$group": {
                        "_id": "$priority",
                        "count": {"$sum": 1}
                    }},
                    {"$sort": {"_id": -1}}
                ]))
                
                stats["priority_distribution"] = {
                    str(stat["_id"]): stat["count"] 
                    for stat in priority_stats
                }
                
                return stats
            
            return {
                "total_users": 0,
                "active_users": 0,
                "total_tweets": 0,
                "total_articles": 0,
                "priority_distribution": {}
            }
            
        except PyMongoError as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {}
    
    def search_users(self, query: str) -> List[TargetUser]:
        """ユーザー検索"""
        try:
            search_filter = {
                "$or": [
                    {"username": {"$regex": query, "$options": "i"}},
                    {"display_name": {"$regex": query, "$options": "i"}}
                ]
            }
            
            cursor = self.collection.find(search_filter).sort("username", 1)
            
            users = []
            for doc in cursor:
                doc.pop('_id', None)
                users.append(TargetUser.from_dict(doc))
            
            return users
            
        except PyMongoError as e:
            self.logger.error(f"ユーザー検索エラー: {e}")
            return []


# グローバルインスタンス
user_service = UserService()