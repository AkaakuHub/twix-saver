"""
システム設定管理サービス
"""

from datetime import datetime
from typing import Any, Optional

from src.models.database import DEFAULT_SYSTEM_CONFIGS, SystemConfig
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger

logger = setup_logger("config_service")


class ConfigService:
    """システム設定管理サービス"""

    def __init__(self):
        self.collection = mongodb_manager.get_collection("system_configs")
        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """デフォルト設定を初期化"""
        existing_keys = set()
        for config in self.collection.find({}, {"key": 1}):
            existing_keys.add(config["key"])

        # デフォルト設定で存在しないものを追加
        for default_config in DEFAULT_SYSTEM_CONFIGS:
            if default_config.key not in existing_keys:
                self.collection.insert_one(default_config.to_dict())
                logger.info(f"デフォルト設定を追加しました: {default_config.key}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        data = self.collection.find_one({"key": key})
        if data:
            config = SystemConfig.from_dict(data)
            return config.value
        return default

    def get_config_object(self, key: str) -> Optional[SystemConfig]:
        """設定オブジェクトを取得"""
        data = self.collection.find_one({"key": key})
        if data:
            return SystemConfig.from_dict(data)
        return None

    def set_config(self, key: str, value: Any, description: str = None, category: str = "general") -> bool:
        """設定値を設定"""
        existing_config = self.get_config_object(key)

        if existing_config:
            # 既存設定を更新
            existing_config.value = value
            existing_config.updated_at = datetime.utcnow()
            if description:
                existing_config.description = description

            result = self.collection.update_one({"key": key}, {"$set": existing_config.to_dict()})
            success = result.modified_count > 0
        else:
            # 新しい設定を作成
            new_config = SystemConfig(key=key, value=value, description=description, category=category)
            result = self.collection.insert_one(new_config.to_dict())
            success = bool(result.inserted_id)

        if success:
            logger.info(f"設定を更新しました: {key} = {value}")

        return success

    def get_configs_by_category(self, category: str) -> dict[str, Any]:
        """カテゴリ別に設定を取得"""
        configs = {}
        for data in self.collection.find({"category": category}):
            config = SystemConfig.from_dict(data)
            configs[config.key] = config.value
        return configs

    def get_all_configs(self) -> dict[str, Any]:
        """全設定を取得"""
        configs = {}
        for data in self.collection.find({}):
            config = SystemConfig.from_dict(data)
            configs[config.key] = config.value
        return configs

    def get_all_config_objects(self) -> list[SystemConfig]:
        """全設定オブジェクトを取得"""
        configs = []
        for data in self.collection.find({}).sort("category", 1):
            configs.append(SystemConfig.from_dict(data))
        return configs

    def update_configs(self, config_updates: dict[str, Any]) -> bool:
        """複数の設定を一括更新"""
        success_count = 0

        for key, value in config_updates.items():
            if self.set_config(key, value):
                success_count += 1

        logger.info(f"設定を一括更新しました: {success_count}/{len(config_updates)}件")
        return success_count == len(config_updates)

    def delete_config(self, key: str) -> bool:
        """設定を削除"""
        result = self.collection.delete_one({"key": key})

        if result.deleted_count > 0:
            logger.info(f"設定を削除しました: {key}")
            return True
        return False

    def reset_to_defaults(self) -> bool:
        """設定をデフォルトにリセット"""
        try:
            # 既存の設定をクリア
            self.collection.delete_many({})

            # デフォルト設定を挿入
            for default_config in DEFAULT_SYSTEM_CONFIGS:
                self.collection.insert_one(default_config.to_dict())

            logger.info("設定をデフォルトにリセットしました")
            return True
        except Exception as e:
            logger.error(f"設定リセットエラー: {e}")
            return False

    # 便利メソッド: よく使う設定へのアクセサー（グローバル実行間隔は削除済み）
    def get_max_tweets_per_session(self) -> int:
        """セッションあたり最大ツイート数を取得"""
        return self.get_config("max_tweets_per_session", 100)

    def get_random_delay_max(self) -> int:
        """ランダム遅延最大値を取得"""
        return self.get_config("random_delay_max_seconds", 120)

    def is_headless_mode(self) -> bool:
        """ヘッドレスモードかチェック"""
        return self.get_config("headless_mode", True)

    def is_proxy_enabled(self) -> bool:
        """プロキシが有効かチェック"""
        return self.get_config("proxy_enabled", False)

    def get_proxy_config(self) -> dict[str, str]:
        """プロキシ設定を取得"""
        if not self.is_proxy_enabled():
            return {}

        return {
            "server": self.get_config("proxy_server", ""),
            "username": self.get_config("proxy_username", ""),
            "password": self.get_config("proxy_password", ""),
        }

    def get_log_level(self) -> str:
        """ログレベルを取得"""
        return self.get_config("log_level", "INFO")


# グローバルサービスインスタンス
config_service = ConfigService()
