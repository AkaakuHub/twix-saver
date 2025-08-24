"""
ターゲットユーザー管理API
CRUD操作と統計情報を提供
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pymongo.errors import PyMongoError

from src.web.models import (
    TargetUserCreate, TargetUserUpdate, TargetUserResponse,
    UserStatistics, SuccessResponse, ErrorResponse
)
from src.services.user_service import user_service
from src.utils.logger import setup_logger

router = APIRouter(prefix="/users", tags=["users"])
logger = setup_logger("api.users")


@router.get("/", response_model=List[TargetUserResponse])
async def get_users(
    include_inactive: bool = Query(False, description="非アクティブユーザーも含める"),
    search: Optional[str] = Query(None, description="検索クエリ")
):
    """全ユーザーを取得"""
    try:
        if search:
            users = user_service.search_users(search)
        else:
            users = user_service.get_all_users(include_inactive=include_inactive)
        
        # TargetUserResponseに変換
        response_users = []
        for user in users:
            user_dict = user.to_dict()
            response_users.append(TargetUserResponse(**user_dict))
        
        logger.info(f"ユーザー一覧を取得: {len(response_users)}件")
        return response_users
        
    except Exception as e:
        logger.error(f"ユーザー取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー取得に失敗しました: {str(e)}")


@router.get("/active", response_model=List[TargetUserResponse])
async def get_active_users():
    """アクティブなユーザーのみを取得"""
    try:
        users = user_service.get_active_users()
        
        response_users = []
        for user in users:
            user_dict = user.to_dict()
            response_users.append(TargetUserResponse(**user_dict))
        
        logger.info(f"アクティブユーザーを取得: {len(response_users)}件")
        return response_users
        
    except Exception as e:
        logger.error(f"アクティブユーザー取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アクティブユーザー取得に失敗しました: {str(e)}")


@router.get("/{username}", response_model=TargetUserResponse)
async def get_user(username: str):
    """指定ユーザーを取得"""
    try:
        user = user_service.get_user(username)
        
        if not user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        user_dict = user.to_dict()
        return TargetUserResponse(**user_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー取得エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー取得に失敗しました: {str(e)}")


@router.post("/", response_model=SuccessResponse)
async def create_user(user_data: TargetUserCreate):
    """新しいユーザーを追加"""
    try:
        # ユーザー名の形式チェック（@記号を除去）
        username = user_data.username.lstrip('@').lower()
        
        # 既存ユーザーチェック
        existing_user = user_service.get_user(username)
        if existing_user:
            raise HTTPException(status_code=400, detail=f"ユーザーは既に存在します: {username}")
        
        success = user_service.add_user(
            username=username,
            display_name=user_data.display_name,
            priority=user_data.priority,
            active=user_data.active
        )
        
        if success:
            logger.info(f"新しいユーザーを追加: {username}")
            return SuccessResponse(
                message=f"ユーザー '{username}' を追加しました",
                data={"username": username}
            )
        else:
            raise HTTPException(status_code=400, detail="ユーザーの追加に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー作成に失敗しました: {str(e)}")


@router.put("/{username}", response_model=SuccessResponse)
async def update_user(username: str, user_data: TargetUserUpdate):
    """ユーザー情報を更新"""
    try:
        # 既存ユーザーチェック
        existing_user = user_service.get_user(username)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        # 更新データを構築（None でない値のみ）
        update_data = {}
        for field, value in user_data.model_dump(exclude_none=True).items():
            update_data[field] = value
        
        if not update_data:
            raise HTTPException(status_code=400, detail="更新するデータがありません")
        
        success = user_service.update_user(username, update_data)
        
        if success:
            logger.info(f"ユーザーを更新: {username}")
            return SuccessResponse(
                message=f"ユーザー '{username}' を更新しました",
                data={"username": username, "updated_fields": list(update_data.keys())}
            )
        else:
            raise HTTPException(status_code=400, detail="ユーザーの更新に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー更新エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー更新に失敗しました: {str(e)}")


@router.delete("/{username}", response_model=SuccessResponse)
async def delete_user(username: str):
    """ユーザーを削除"""
    try:
        # 既存ユーザーチェック
        existing_user = user_service.get_user(username)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        success = user_service.delete_user(username)
        
        if success:
            logger.info(f"ユーザーを削除: {username}")
            return SuccessResponse(
                message=f"ユーザー '{username}' を削除しました",
                data={"username": username}
            )
        else:
            raise HTTPException(status_code=400, detail="ユーザーの削除に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー削除エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー削除に失敗しました: {str(e)}")


@router.post("/{username}/activate", response_model=SuccessResponse)
async def activate_user(username: str):
    """ユーザーを有効化"""
    try:
        existing_user = user_service.get_user(username)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        success = user_service.activate_user(username)
        
        if success:
            logger.info(f"ユーザーを有効化: {username}")
            return SuccessResponse(
                message=f"ユーザー '{username}' を有効化しました",
                data={"username": username, "active": True}
            )
        else:
            raise HTTPException(status_code=400, detail="ユーザーの有効化に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー有効化エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー有効化に失敗しました: {str(e)}")


@router.post("/{username}/deactivate", response_model=SuccessResponse)
async def deactivate_user(username: str):
    """ユーザーを無効化"""
    try:
        existing_user = user_service.get_user(username)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        success = user_service.deactivate_user(username)
        
        if success:
            logger.info(f"ユーザーを無効化: {username}")
            return SuccessResponse(
                message=f"ユーザー '{username}' を無効化しました",
                data={"username": username, "active": False}
            )
        else:
            raise HTTPException(status_code=400, detail="ユーザーの無効化に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー無効化エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー無効化に失敗しました: {str(e)}")


@router.put("/{username}/priority", response_model=SuccessResponse)
async def update_user_priority(username: str, priority: int = Query(..., ge=1, le=4)):
    """ユーザーの優先度を更新"""
    try:
        existing_user = user_service.get_user(username)
        if not existing_user:
            raise HTTPException(status_code=404, detail=f"ユーザーが見つかりません: {username}")
        
        success = user_service.update_user_priority(username, priority)
        
        if success:
            priority_labels = {1: "低", 2: "標準", 3: "高", 4: "緊急"}
            logger.info(f"ユーザー優先度を更新: {username} -> {priority}")
            return SuccessResponse(
                message=f"ユーザー '{username}' の優先度を '{priority_labels[priority]}' に更新しました",
                data={"username": username, "priority": priority}
            )
        else:
            raise HTTPException(status_code=400, detail="優先度の更新に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"優先度更新エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"優先度更新に失敗しました: {str(e)}")


@router.get("/stats/summary", response_model=UserStatistics)
async def get_user_statistics():
    """ユーザー統計情報を取得"""
    try:
        stats = user_service.get_user_stats()
        
        return UserStatistics(
            total_users=stats.get("total_users", 0),
            active_users=stats.get("active_users", 0),
            total_tweets=stats.get("total_tweets", 0),
            total_articles=stats.get("total_articles", 0),
            priority_distribution=stats.get("priority_distribution", {})
        )
        
    except Exception as e:
        logger.error(f"ユーザー統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"統計取得に失敗しました: {str(e)}")


@router.get("/priority/{min_priority}", response_model=List[TargetUserResponse])
async def get_users_by_priority(min_priority: int = Query(..., ge=1, le=4)):
    """指定優先度以上のユーザーを取得"""
    try:
        users = user_service.get_users_by_priority(min_priority)
        
        response_users = []
        for user in users:
            user_dict = user.to_dict()
            response_users.append(TargetUserResponse(**user_dict))
        
        logger.info(f"優先度{min_priority}以上のユーザーを取得: {len(response_users)}件")
        return response_users
        
    except Exception as e:
        logger.error(f"優先度別ユーザー取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"優先度別ユーザー取得に失敗しました: {str(e)}")