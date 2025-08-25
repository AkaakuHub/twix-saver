"""
メディアファイル取得API
保存された画像データを提供
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Response

from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger
from src.config.settings import settings

router = APIRouter(prefix="/media", tags=["media"])
logger = setup_logger("api.media")


@router.get("/{media_id}")
async def get_media(media_id: str) -> Response:
    """指定されたメディアIDの画像データを取得"""
    try:
        # MongoDB から画像データを取得
        media_doc = mongodb_manager.db.media_files.find_one({"_id": media_id})

        if not media_doc:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたメディアが見つかりません: {media_id}"
            )

        # ファイルパスを取得してファイルを読み込み
        file_path_name = media_doc.get("file_path")
        if not file_path_name:
            raise HTTPException(
                status_code=500,
                detail="メディアファイルパスが無効です"
            )
        
        # 完全なファイルパス
        full_file_path = Path(settings.images_dir) / file_path_name

        try:
            if not full_file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"メディアファイルが見つかりません: {file_path_name}"
                )

            with open(full_file_path, 'rb') as f:
                image_bytes = f.read()
        except Exception as e:
            logger.error(f"ファイル読み込みエラー ({media_id}): {e}")
            raise HTTPException(
                status_code=500,
                detail="画像ファイルの読み込みに失敗しました"
            )

        # MIMEタイプを取得
        content_type = media_doc.get("content_type", "image/jpeg")
        
        # 画像レスポンスを返す
        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 1日キャッシュ
                "Content-Length": str(len(image_bytes))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"メディア取得エラー ({media_id}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"メディア取得に失敗しました: {str(e)}"
        )


@router.get("/{media_id}/info")
async def get_media_info(media_id: str) -> dict:
    """指定されたメディアIDの情報を取得"""
    try:
        media_doc = mongodb_manager.db.media_files.find_one(
            {"_id": media_id},
            {"_id": 1, "content_type": 1, "size": 1, "created_at": 1}
        )

        if not media_doc:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたメディアが見つかりません: {media_id}"
            )
        
        return {
            "media_id": media_doc["_id"],
            "content_type": media_doc.get("content_type"),
            "size": media_doc.get("size"),
            "created_at": media_doc.get("created_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"メディア情報取得エラー ({media_id}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"メディア情報取得に失敗しました: {str(e)}"
        )