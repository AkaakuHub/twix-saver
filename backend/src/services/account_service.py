"""
Twitterアカウント管理サービス
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from src.models.database import TwitterAccount, TwitterAccountStatus
from src.utils.data_manager import mongodb_manager
from src.utils.encryption import encrypt_password
from src.utils.logger import setup_logger

logger = setup_logger("account_service")


class TwitterAccountService:
    """Twitterアカウント管理サービス"""

    def __init__(self):
        self.collection = mongodb_manager.get_collection("twitter_accounts")

    def create_account(
        self,
        username: str,
        email: str,
        password: str,
        display_name: str = None,
        notes: str = None,
    ) -> TwitterAccount:
        """新しいTwitterアカウントを作成"""
        account_id = str(uuid.uuid4())

        account = TwitterAccount(
            account_id=account_id,
            username=username.lstrip("@"),  # @を削除
            email=email,
            password_encrypted=encrypt_password(password),
            display_name=display_name,
            notes=notes,
        )

        # データベースに保存
        result = self.collection.insert_one(account.to_dict(include_password=True))
        if result.inserted_id:
            logger.info(f"新しいTwitterアカウントを作成しました: {username}")
            return account
        else:
            raise Exception("アカウントの作成に失敗しました")

    def get_account(self, account_id: str) -> Optional[TwitterAccount]:
        """アカウントIDでアカウントを取得"""
        data = self.collection.find_one({"account_id": account_id})
        if data:
            return TwitterAccount.from_dict(data)
        return None

    def get_account_by_username(self, username: str) -> Optional[TwitterAccount]:
        """ユーザー名でアカウントを取得"""
        data = self.collection.find_one({"username": username.lstrip("@")})
        if data:
            return TwitterAccount.from_dict(data)
        return None

    def get_all_accounts(self, include_inactive: bool = False) -> list[TwitterAccount]:
        """全アカウントを取得"""
        query = {} if include_inactive else {"active": True}
        accounts = []

        for data in self.collection.find(query).sort("created_at", -1):
            accounts.append(TwitterAccount.from_dict(data))

        return accounts

    def get_available_accounts(self) -> list[TwitterAccount]:
        """使用可能なアカウントを取得"""
        accounts = self.get_all_accounts(include_inactive=False)
        return [account for account in accounts if account.is_available()]

    def update_account(self, account: TwitterAccount) -> bool:
        """アカウント情報を更新"""
        account.updated_at = datetime.utcnow()

        result = self.collection.update_one(
            {"account_id": account.account_id},
            {"$set": account.to_dict(include_password=True)},
        )

        if result.modified_count > 0:
            logger.info(f"Twitterアカウントを更新しました: {account.username}")
            return True
        return False

    def update_password(self, account_id: str, new_password: str) -> bool:
        """パスワードを更新"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.update_password(new_password)
        return self.update_account(account)

    def delete_account(self, account_id: str) -> bool:
        """アカウントを削除"""
        result = self.collection.delete_one({"account_id": account_id})

        if result.deleted_count > 0:
            logger.info(f"Twitterアカウントを削除しました: {account_id}")
            return True
        return False

    def mark_account_used(self, account_id: str) -> bool:
        """アカウントの使用記録を更新"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.mark_used()
        return self.update_account(account)

    def mark_job_success(self, account_id: str) -> bool:
        """ジョブ成功を記録"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.mark_job_success()
        return self.update_account(account)

    def mark_job_failure(self, account_id: str, error_type: str = None) -> bool:
        """ジョブ失敗を記録"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.mark_job_failure(error_type)
        return self.update_account(account)

    def set_rate_limited(self, account_id: str, until: Optional[datetime] = None) -> bool:
        """レート制限を設定"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.set_rate_limited(until)
        return self.update_account(account)

    def activate_account(self, account_id: str) -> bool:
        """アカウントを有効化"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.active = True
        account.status = TwitterAccountStatus.ACTIVE.value
        return self.update_account(account)

    def deactivate_account(self, account_id: str) -> bool:
        """アカウントを無効化"""
        account = self.get_account(account_id)
        if not account:
            return False

        account.active = False
        account.status = TwitterAccountStatus.INACTIVE.value
        return self.update_account(account)

    def get_account_stats(self) -> dict[str, Any]:
        """アカウント統計を取得"""
        total_accounts = self.collection.count_documents({})
        active_accounts = self.collection.count_documents({"active": True})
        available_accounts = len(self.get_available_accounts())

        # ステータス別の統計
        status_stats = {}
        for status in TwitterAccountStatus:
            count = self.collection.count_documents({"status": status.value})
            status_stats[status.value] = count

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "available_accounts": available_accounts,
            "status_breakdown": status_stats,
        }


# グローバルサービスインスタンス
twitter_account_service = TwitterAccountService()
