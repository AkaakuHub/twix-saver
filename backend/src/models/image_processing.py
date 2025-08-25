"""
ツイート画像処理状態管理
"""

from datetime import datetime
from enum import Enum
from typing import Any


class ImageProcessingStatus(Enum):
    """画像処理状態"""

    PENDING = "pending"  # 未処理
    PROCESSING = "processing"  # 処理中
    COMPLETED = "completed"  # 完了
    FAILED = "failed"  # 失敗
    SKIPPED = "skipped"  # スキップ（画像なし）


class ImageProcessingState:
    """ツイートの画像処理状態管理クラス"""

    @staticmethod
    def create_initial_state() -> dict[str, Any]:
        """初期状態を作成"""
        return {
            "image_processing_status": ImageProcessingStatus.PENDING.value,
            "image_processing_attempted_at": None,
            "image_processing_completed_at": None,
            "image_processing_retry_count": 0,
            "image_processing_error": None,
            "image_processing_media_count": 0,  # 処理対象画像数
            "image_processing_success_count": 0,  # 成功した画像数
        }

    @staticmethod
    def mark_as_processing(state: dict[str, Any]) -> dict[str, Any]:
        """処理中状態に更新"""
        state.update(
            {
                "image_processing_status": ImageProcessingStatus.PROCESSING.value,
                "image_processing_attempted_at": datetime.utcnow().isoformat(),
            }
        )
        return state

    @staticmethod
    def mark_as_completed(state: dict[str, Any], media_count: int, success_count: int) -> dict[str, Any]:
        """完了状態に更新"""
        state.update(
            {
                "image_processing_status": ImageProcessingStatus.COMPLETED.value,
                "image_processing_completed_at": datetime.utcnow().isoformat(),
                "image_processing_media_count": media_count,
                "image_processing_success_count": success_count,
                "image_processing_error": None,
            }
        )
        return state

    @staticmethod
    def mark_as_failed(state: dict[str, Any], error_msg: str) -> dict[str, Any]:
        """失敗状態に更新"""
        state.update(
            {
                "image_processing_status": ImageProcessingStatus.FAILED.value,
                "image_processing_completed_at": datetime.utcnow().isoformat(),
                "image_processing_error": error_msg,
                "image_processing_retry_count": state.get("image_processing_retry_count", 0) + 1,
            }
        )
        return state

    @staticmethod
    def mark_as_skipped(state: dict[str, Any]) -> dict[str, Any]:
        """スキップ状態に更新（画像なし）"""
        state.update(
            {
                "image_processing_status": ImageProcessingStatus.SKIPPED.value,
                "image_processing_completed_at": datetime.utcnow().isoformat(),
                "image_processing_media_count": 0,
                "image_processing_success_count": 0,
            }
        )
        return state

    @staticmethod
    def should_retry(state: dict[str, Any], max_retries: int = 3) -> bool:
        """リトライすべきかを判定"""
        return (
            state.get("image_processing_status") == ImageProcessingStatus.FAILED.value
            and state.get("image_processing_retry_count", 0) < max_retries
        )

    @staticmethod
    def is_processing_needed(state: dict[str, Any]) -> bool:
        """画像処理が必要かを判定"""
        status = state.get("image_processing_status")
        return status in [ImageProcessingStatus.PENDING.value, ImageProcessingStatus.FAILED.value]

    @staticmethod
    def get_failed_tweets_filter() -> dict[str, Any]:
        """画像処理失敗ツイートのMongoDBフィルター"""
        return {"image_processing_status": ImageProcessingStatus.FAILED.value}

    @staticmethod
    def get_pending_tweets_filter() -> dict[str, Any]:
        """画像処理未完了ツイートのMongoDBフィルター"""
        return {
            "image_processing_status": {
                "$in": [
                    ImageProcessingStatus.PENDING.value,
                    ImageProcessingStatus.PROCESSING.value,
                    ImageProcessingStatus.FAILED.value,
                ]
            }
        }
