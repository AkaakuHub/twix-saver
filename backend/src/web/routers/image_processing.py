"""
画像処理管理API
画像処理のリトライ、状態確認、統計情報を提供
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.models.image_processing import ImageProcessingState
from src.utils.batch_processor import batch_processor
from src.utils.data_manager import data_manager
from src.utils.logger import setup_logger
from src.web.models import SuccessResponse

router = APIRouter(prefix="/image-processing", tags=["image-processing"])
logger = setup_logger("api.image_processing")


@router.post("/retry-failed", response_model=SuccessResponse)
async def retry_failed_image_processing(
    max_tweets: int = Query(100, ge=1, le=1000, description="最大処理件数"),
):
    """画像処理が失敗したツイートのリトライ"""
    try:
        logger.info(f"画像処理失敗ツイートのリトライ開始: 最大{max_tweets}件")

        retry_count, success_count = await batch_processor.retry_failed_image_processing(
            data_manager.mongodb, max_tweets
        )

        if retry_count == 0:
            return SuccessResponse(
                message="リトライ対象のツイートがありません", data={"retry_count": 0, "success_count": 0}
            )

        logger.info(f"画像処理リトライ完了: {success_count}/{retry_count}件成功")

        return SuccessResponse(
            message=f"画像処理リトライ完了: {success_count}/{retry_count}件成功",
            data={
                "retry_count": retry_count,
                "success_count": success_count,
                "failure_count": retry_count - success_count,
            },
        )

    except Exception as e:
        logger.error(f"画像処理リトライエラー: {e}")
        raise HTTPException(status_code=500, detail=f"リトライ処理エラー: {str(e)}") from None


@router.get("/stats")
async def get_image_processing_stats():
    """画像処理統計情報を取得"""
    try:
        if not data_manager.mongodb.is_connected:
            raise HTTPException(status_code=503, detail="データベースに接続できません")

        # 各状態のツイート数を取得
        db = data_manager.mongodb.db

        total_tweets = db.tweets.count_documents({})

        pending_count = db.tweets.count_documents({"image_processing_status": "pending"})

        processing_count = db.tweets.count_documents({"image_processing_status": "processing"})

        completed_count = db.tweets.count_documents({"image_processing_status": "completed"})

        failed_count = db.tweets.count_documents({"image_processing_status": "failed"})

        skipped_count = db.tweets.count_documents({"image_processing_status": "skipped"})

        # 画像処理状態がないツイート（旧データ）
        no_status_count = db.tweets.count_documents({"image_processing_status": {"$exists": False}})

        return {
            "total_tweets": total_tweets,
            "image_processing_stats": {
                "pending": pending_count,
                "processing": processing_count,
                "completed": completed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "no_status": no_status_count,
            },
            "success_rate": round((completed_count / max(1, total_tweets - no_status_count)) * 100, 2),
        }

    except Exception as e:
        logger.error(f"画像処理統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"統計取得エラー: {str(e)}") from None


@router.post("/migrate-legacy-tweets", response_model=SuccessResponse)
async def migrate_legacy_tweets(
    max_tweets: int = Query(1000, ge=1, le=10000, description="最大処理件数"),
):
    """既存のツイートに画像処理状態を追加するマイグレーション"""
    try:
        logger.info(f"レガシーツイートのマイグレーション開始: 最大{max_tweets}件")

        if not data_manager.mongodb.is_connected:
            raise HTTPException(status_code=503, detail="データベースに接続できません")

        db = data_manager.mongodb.db

        # 画像処理状態がないツイートを取得
        legacy_tweets = list(db.tweets.find({"image_processing_status": {"$exists": False}}, limit=max_tweets))

        if not legacy_tweets:
            return SuccessResponse(message="マイグレーション対象のツイートがありません", data={"migrated_count": 0})

        # 一括更新用の操作リスト
        from pymongo import UpdateOne

        operations = []
        for tweet in legacy_tweets:
            # 初期状態を作成
            initial_state = ImageProcessingState.create_initial_state()

            # 既に画像がダウンロード済みの場合は完了状態に
            if tweet.get("downloaded_media") and len(tweet["downloaded_media"]) > 0:
                media_count = len(tweet["downloaded_media"])
                initial_state = ImageProcessingState.mark_as_completed(initial_state, media_count, media_count)

            # 更新操作を追加
            operations.append(UpdateOne({"_id": tweet["_id"]}, {"$set": initial_state}))

        # 一括更新実行
        if operations:
            result = db.tweets.bulk_write(operations)
            migrated_count = result.modified_count

            logger.info(f"レガシーツイートマイグレーション完了: {migrated_count}件更新")

            return SuccessResponse(
                message=f"マイグレーション完了: {migrated_count}件のツイートを更新しました",
                data={"migrated_count": migrated_count, "total_found": len(legacy_tweets)},
            )
        else:
            return SuccessResponse(message="マイグレーション対象がありませんでした", data={"migrated_count": 0})

    except Exception as e:
        logger.error(f"マイグレーションエラー: {e}")
        raise HTTPException(status_code=500, detail=f"マイグレーションエラー: {str(e)}") from None


@router.get("/failed-tweets")
async def get_failed_tweets(
    limit: int = Query(10, ge=1, le=100, description="取得件数"),
    skip: int = Query(0, ge=0, description="スキップ件数"),
):
    """画像処理が失敗したツイートを取得"""
    try:
        if not data_manager.mongodb.is_connected:
            raise HTTPException(status_code=503, detail="データベースに接続できません")

        db = data_manager.mongodb.db

        failed_tweets = list(
            db.tweets.find(
                {"image_processing_status": "failed"},
                {
                    "id_str": 1,
                    "author_username": 1,
                    "image_processing_error": 1,
                    "image_processing_retry_count": 1,
                    "image_processing_attempted_at": 1,
                },
            )
            .skip(skip)
            .limit(limit)
        )

        total_failed = db.tweets.count_documents({"image_processing_status": "failed"})

        return {"failed_tweets": failed_tweets, "total_failed": total_failed, "limit": limit, "skip": skip}

    except Exception as e:
        logger.error(f"失敗ツイート取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"取得エラー: {str(e)}") from None


@router.post("/retry-all-image-processing", response_model=SuccessResponse)
async def retry_all_image_processing(
    username: Optional[str] = Query(None, description="特定ユーザーのみリトライ（省略時は全ユーザー）"),
    max_tweets: int = Query(1000, ge=1, le=10000, description="最大処理件数"),
    force_reprocess: bool = Query(False, description="完了済みも含めて強制再処理"),
):
    """全体の画像処理リトライ（完了済みを除く、または強制再処理）"""
    try:
        if not data_manager.mongodb.is_connected:
            raise HTTPException(status_code=503, detail="データベースに接続できません")

        db = data_manager.mongodb.db

        # フィルター条件を構築
        filter_conditions = {}

        # ユーザー指定がある場合
        if username:
            filter_conditions["author_username"] = username

        # 処理対象の条件
        if force_reprocess:
            # 強制再処理：すべてのツイート
            logger.info(f"全ツイートの画像処理強制再実行開始 (ユーザー: {username or '全員'})")
        else:
            # 通常：未完了のみ
            filter_conditions.update(ImageProcessingState.get_pending_tweets_filter())
            logger.info(f"未完了ツイートの画像処理リトライ開始 (ユーザー: {username or '全員'})")

        # 対象ツイートを取得
        target_tweets = list(db.tweets.find(filter_conditions).limit(max_tweets))

        if not target_tweets:
            return SuccessResponse(
                message="処理対象のツイートがありません",
                data={
                    "processed_count": 0,
                    "success_count": 0,
                    "filter": f"user: {username or 'all'}, force: {force_reprocess}",
                },
            )

        logger.info(f"画像処理対象: {len(target_tweets)}件のツイート")

        # 強制再処理の場合、状態をリセット
        if force_reprocess:
            from pymongo import UpdateOne

            reset_operations = []
            for tweet in target_tweets:
                reset_state = ImageProcessingState.create_initial_state()
                reset_operations.append(UpdateOne({"_id": tweet["_id"]}, {"$set": reset_state}))

            if reset_operations:
                db.tweets.bulk_write(reset_operations)
                logger.info(f"{len(reset_operations)}件のツイート状態をリセット")

        # バッチ処理で画像処理実行
        processed_count, success_count, failed_count = await batch_processor.process_tweets_with_images_batch(
            target_tweets, data_manager.mongodb
        )

        logger.info(f"全体画像処理リトライ完了: {success_count}/{processed_count}件成功")

        return SuccessResponse(
            message=f"画像処理完了: {success_count}/{processed_count}件成功 (失敗: {failed_count}件)",
            data={
                "processed_count": processed_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "username": username,
                "force_reprocess": force_reprocess,
            },
        )

    except Exception as e:
        logger.error(f"全体画像処理リトライエラー: {e}")
        raise HTTPException(status_code=500, detail=f"全体リトライエラー: {str(e)}") from None
