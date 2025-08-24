"""
Twitterアカウント管理ルーター
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.account_service import twitter_account_service
from src.models.database import TwitterAccount, TwitterAccountStatus
from src.utils.logger import setup_logger

logger = setup_logger("accounts_router")
router = APIRouter()

# Pydanticモデル定義
class TwitterAccountCreate(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None
    notes: Optional[str] = None

class TwitterAccountUpdate(BaseModel):
    display_name: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    priority: Optional[int] = None

class TwitterAccountResponse(BaseModel):
    account_id: str
    username: str
    email: str
    display_name: Optional[str]
    status: str
    active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    last_used_at: Optional[str]
    total_jobs_run: int
    successful_jobs: int
    failed_jobs: int
    rate_limit_until: Optional[str]
    login_attempts: int
    priority: int
    notes: Optional[str]

class TwitterAccountStats(BaseModel):
    total_accounts: int
    active_accounts: int
    available_accounts: int
    status_breakdown: dict


@router.get("/accounts", response_model=List[TwitterAccountResponse])
async def get_accounts(
    include_inactive: bool = Query(False, description="非アクティブなアカウントも含める"),
    available_only: bool = Query(False, description="使用可能なアカウントのみ")
):
    """Twitterアカウント一覧を取得"""
    try:
        if available_only:
            accounts = twitter_account_service.get_available_accounts()
        else:
            accounts = twitter_account_service.get_all_accounts(include_inactive=include_inactive)
        
        # レスポンス形式に変換（パスワードは含めない）
        account_responses = []
        for account in accounts:
            account_dict = account.to_dict(include_password=False)
            account_responses.append(TwitterAccountResponse(**account_dict))
        
        logger.info(f"Twitterアカウント一覧を取得: {len(account_responses)}件")
        return account_responses
        
    except Exception as e:
        logger.error(f"アカウント一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント一覧取得に失敗しました: {str(e)}")


@router.post("/accounts", response_model=TwitterAccountResponse)
async def create_account(account_data: TwitterAccountCreate):
    """新しいTwitterアカウントを作成"""
    try:
        # 既存のユーザー名チェック
        existing_account = twitter_account_service.get_account_by_username(account_data.username)
        if existing_account:
            raise HTTPException(status_code=400, detail="このユーザー名のアカウントは既に存在します")
        
        # アカウント作成
        account = twitter_account_service.create_account(
            username=account_data.username,
            email=account_data.email,
            password=account_data.password,
            display_name=account_data.display_name,
            notes=account_data.notes
        )
        
        account_dict = account.to_dict(include_password=False)
        response = TwitterAccountResponse(**account_dict)
        
        logger.info(f"新しいTwitterアカウントを作成しました: {account_data.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント作成に失敗しました: {str(e)}")


@router.get("/accounts/{account_id}", response_model=TwitterAccountResponse)
async def get_account(account_id: str):
    """特定のTwitterアカウントを取得"""
    try:
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        account_dict = account.to_dict(include_password=False)
        return TwitterAccountResponse(**account_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント取得に失敗しました: {str(e)}")


@router.put("/accounts/{account_id}", response_model=TwitterAccountResponse)
async def update_account(account_id: str, account_update: TwitterAccountUpdate):
    """Twitterアカウント情報を更新"""
    try:
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        # 更新可能なフィールドを適用
        if account_update.display_name is not None:
            account.display_name = account_update.display_name
        if account_update.notes is not None:
            account.notes = account_update.notes
        if account_update.active is not None:
            account.active = account_update.active
            if account_update.active:
                account.status = TwitterAccountStatus.ACTIVE.value
            else:
                account.status = TwitterAccountStatus.INACTIVE.value
        if account_update.priority is not None:
            account.priority = account_update.priority
        
        # 更新実行
        success = twitter_account_service.update_account(account)
        if not success:
            raise HTTPException(status_code=500, detail="アカウント更新に失敗しました")
        
        account_dict = account.to_dict(include_password=False)
        return TwitterAccountResponse(**account_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント更新に失敗しました: {str(e)}")


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """Twitterアカウントを削除"""
    try:
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        success = twitter_account_service.delete_account(account_id)
        if not success:
            raise HTTPException(status_code=500, detail="アカウント削除に失敗しました")
        
        logger.info(f"Twitterアカウントを削除しました: {account.username}")
        return {"success": True, "message": "アカウントを削除しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント削除エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント削除に失敗しました: {str(e)}")


@router.post("/accounts/{account_id}/activate")
async def activate_account(account_id: str):
    """Twitterアカウントを有効化"""
    try:
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        success = twitter_account_service.activate_account(account_id)
        if not success:
            raise HTTPException(status_code=500, detail="アカウント有効化に失敗しました")
        
        return {"success": True, "message": "アカウントを有効化しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント有効化エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント有効化に失敗しました: {str(e)}")


@router.post("/accounts/{account_id}/deactivate")
async def deactivate_account(account_id: str):
    """Twitterアカウントを無効化"""
    try:
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        success = twitter_account_service.deactivate_account(account_id)
        if not success:
            raise HTTPException(status_code=500, detail="アカウント無効化に失敗しました")
        
        return {"success": True, "message": "アカウントを無効化しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アカウント無効化エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント無効化に失敗しました: {str(e)}")


@router.put("/accounts/{account_id}/password")
async def update_password(account_id: str, new_password: dict):
    """Twitterアカウントのパスワードを更新"""
    try:
        if "password" not in new_password:
            raise HTTPException(status_code=400, detail="パスワードが必要です")
        
        account = twitter_account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="アカウントが見つかりません")
        
        success = twitter_account_service.update_password(account_id, new_password["password"])
        if not success:
            raise HTTPException(status_code=500, detail="パスワード更新に失敗しました")
        
        return {"success": True, "message": "パスワードを更新しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"パスワード更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"パスワード更新に失敗しました: {str(e)}")


@router.get("/accounts/stats", response_model=TwitterAccountStats)
async def get_account_stats():
    """Twitterアカウント統計を取得"""
    try:
        stats = twitter_account_service.get_account_stats()
        return TwitterAccountStats(**stats)
        
    except Exception as e:
        logger.error(f"アカウント統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント統計取得に失敗しました: {str(e)}")