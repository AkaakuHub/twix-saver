"""
メディアファイル取得API
保存された画像データを提供
"""

import base64
from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from io import BytesIO

from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger

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
        
        # Base64データをバイナリに変換
        base64_data = media_doc.get("data")
        if not base64_data:
            raise HTTPException(
                status_code=500,
                detail="メディアデータが無効です"
            )
        
        try:
            image_bytes = base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Base64デコードエラー ({media_id}): {e}")
            raise HTTPException(
                status_code=500,
                detail="画像データの復元に失敗しました"
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