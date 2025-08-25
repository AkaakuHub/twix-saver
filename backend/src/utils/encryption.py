"""
パスワード暗号化/復号化ユーティリティ
"""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.utils.logger import setup_logger

logger = setup_logger("encryption")


class PasswordEncryption:
    """パスワード暗号化/復号化クラス"""

    def __init__(self):
        self.encryption_key = os.getenv("PASSWORD_ENCRYPTION_KEY")
        if not self.encryption_key:
            raise ValueError("PASSWORD_ENCRYPTION_KEY環境変数が設定されていません")

        # キーから暗号化用のFernetキーを生成
        self._fernet_key = self._derive_key(self.encryption_key.encode())
        self._fernet = Fernet(self._fernet_key)

    def _derive_key(self, password: bytes, salt: bytes = b"twitter_scraper_salt") -> bytes:
        """パスワードからFernet用のキーを派生"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt_password(self, password: str) -> str:
        """パスワードを暗号化"""
        try:
            encrypted_bytes = self._fernet.encrypt(password.encode())
            encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode()
            logger.debug("パスワードを暗号化しました")
            return encrypted_str
        except Exception as e:
            logger.error(f"パスワード暗号化エラー: {e}")
            raise

    def decrypt_password(self, encrypted_password: str) -> str:
        """暗号化されたパスワードを復号化"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            decrypted_password = decrypted_bytes.decode()
            logger.debug("パスワードを復号化しました")
            return decrypted_password
        except Exception as e:
            logger.error(f"パスワード復号化エラー: {e}")
            raise


# グローバルインスタンス
try:
    password_encryption = PasswordEncryption()
except ValueError as e:
    logger.warning(f"パスワード暗号化初期化失敗: {e}")
    password_encryption = None


def encrypt_password(password: str) -> str:
    """パスワードを暗号化（ヘルパー関数）"""
    if not password_encryption:
        raise ValueError("パスワード暗号化が初期化されていません")
    return password_encryption.encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """パスワードを復号化（ヘルパー関数）"""
    if not password_encryption:
        raise ValueError("パスワード暗号化が初期化されていません")
    return password_encryption.decrypt_password(encrypted_password)
