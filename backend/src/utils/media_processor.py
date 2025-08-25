"""
統合メディア処理システム
ツイート添付画像とリンク先画像を統一的に処理
"""

import asyncio
import mimetypes
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiohttp

from src.config.settings import settings
from src.utils.logger import setup_logger


class MediaProcessor:
    """メディア処理の統合クラス"""

    def __init__(self):
        self.logger = setup_logger("media_processor")
        self.session = None

    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()

    def is_image_url(self, url: str) -> bool:
        """URLが画像ファイルを指しているかチェック"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            image_extensions = {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".bmp",
                ".svg",
            }
            return any(path.endswith(ext) for ext in image_extensions)
        except Exception:
            return False

    async def download_image(self, url: str) -> Optional[tuple[bytes, str]]:
        """画像をダウンロードして (バイナリデータ, MIMEタイプ) を返す"""
        try:
            if not self.session:
                raise RuntimeError("セッションが初期化されていません")

            self.logger.debug(f"画像ダウンロード開始: {url}")

            async with self.session.get(url) as response:
                if response.status != 200:
                    self.logger.warning(f"画像ダウンロード失敗 (HTTP {response.status}): {url}")
                    return None

                content = await response.read()

                # MIMEタイプを取得
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    # URLから推測
                    mime_type, _ = mimetypes.guess_type(url)
                    if not mime_type or not mime_type.startswith("image/"):
                        mime_type = "image/jpeg"  # デフォルト
                else:
                    mime_type = content_type.split(";")[0]  # パラメータを除去

                # サイズチェック（10MBまで）
                if len(content) > 10 * 1024 * 1024:
                    self.logger.warning(f"画像サイズが大きすぎます ({len(content)} bytes): {url}")
                    return None

                self.logger.debug(f"画像ダウンロード完了: {url} ({len(content)} bytes, {mime_type})")
                return content, mime_type

        except asyncio.TimeoutError:
            self.logger.warning(f"画像ダウンロードタイムアウト: {url}")
        except Exception as e:
            self.logger.warning(f"画像ダウンロードエラー: {url} - {e}")

        return None

    def save_image_to_db(self, image_data: bytes, mime_type: str, db_manager) -> str:
        """画像をファイルとして保存し、DBにメタデータを保存、メディアIDを返す"""
        try:
            media_id = str(uuid.uuid4())

            # ファイル拡張子を取得
            file_extension = mimetypes.guess_extension(mime_type) or ".jpg"
            filename = f"{media_id}{file_extension}"

            # 画像保存ディレクトリのパス
            images_dir = Path(settings.images_dir)
            images_dir.mkdir(parents=True, exist_ok=True)

            # ファイルパス
            file_path = images_dir / filename

            # ファイルに書き込み
            with open(file_path, "wb") as f:
                f.write(image_data)

            # DBにメタデータを保存
            media_doc = {
                "_id": media_id,
                "file_path": filename,  # 相対パス
                "content_type": mime_type,
                "size": len(image_data),
                "created_at": db_manager.get_jst_now(),
            }

            db_manager.db.media_files.insert_one(media_doc)
            self.logger.debug(f"画像をファイルに保存: {media_id} ({len(image_data)} bytes, {mime_type}) -> {filename}")

            return media_id

        except Exception as e:
            self.logger.error(f"画像ファイル保存エラー: {e}")
            return None

    async def process_tweet_media(self, tweet: dict, db_manager) -> dict:
        """ツイートのすべてのメディア（添付画像+リンク先画像）を統合された順番で処理"""
        try:
            all_media = []
            processed_urls = set()  # 重複チェック用

            # Step 1: 添付画像を処理（Twitter画像、extended_entities.mediaまたはentities.media）
            media_sources = []
            if "legacy" in tweet:
                # extended_entities が存在する場合はそれを優先
                if "extended_entities" in tweet["legacy"] and "media" in tweet["legacy"]["extended_entities"]:
                    media_sources = tweet["legacy"]["extended_entities"]["media"]
                # extended_entities がない場合のみ entities.media を使用
                elif "entities" in tweet["legacy"] and "media" in tweet["legacy"]["entities"]:
                    media_sources = tweet["legacy"]["entities"]["media"]

            # 添付画像の処理（indices情報で順番を保持）
            for media in media_sources:
                if media.get("type") == "photo":
                    media_url = media.get("media_url_https") or media.get("media_url")
                    if media_url and media_url not in processed_urls:
                        processed_urls.add(media_url)
                        result = await self.download_image(media_url)
                        if result:
                            image_data, mime_type = result
                            media_id = self.save_image_to_db(image_data, mime_type, db_manager)

                            if media_id:
                                # indices情報を取得して順番を保持
                                indices = media.get("indices", [0, 0])  # デフォルトは[0, 0]
                                all_media.append(
                                    {
                                        "media_id": media_id,
                                        "original_url": media_url,
                                        "type": "photo",
                                        "mime_type": mime_type,
                                        "size": len(image_data),
                                        "position": indices[0],  # テキスト内での開始位置
                                        "order_type": "attachment",  # 添付画像
                                    }
                                )

            # Step 2: リンク先画像を処理（URL entities、indices情報で順番を保持）
            if "legacy" in tweet and "entities" in tweet["legacy"] and "urls" in tweet["legacy"]["entities"]:
                for url_entity in tweet["legacy"]["entities"]["urls"]:
                    expanded_url = url_entity.get("expanded_url")
                    if expanded_url and self.is_image_url(expanded_url) and expanded_url not in processed_urls:
                        processed_urls.add(expanded_url)
                        result = await self.download_image(expanded_url)
                        if result:
                            image_data, mime_type = result
                            media_id = self.save_image_to_db(image_data, mime_type, db_manager)

                            if media_id:
                                # indices情報を取得して順番を保持
                                indices = url_entity.get("indices", [0, 0])  # デフォルトは[0, 0]
                                all_media.append(
                                    {
                                        "media_id": media_id,
                                        "original_url": expanded_url,
                                        "type": "linked_image",
                                        "mime_type": mime_type,
                                        "size": len(image_data),
                                        "position": indices[0],  # テキスト内での開始位置
                                        "order_type": "link",  # リンク先画像
                                    }
                                )

            # Step 3: position（テキスト内の位置）で順番をソート
            # 添付画像を優先し、同じposition内では添付画像 → リンク画像の順
            all_media.sort(key=lambda x: (x["position"], x["order_type"] == "link"))

            if all_media:
                # ツイートにdownloaded_mediaフィールドを追加
                tweet["downloaded_media"] = all_media
                self.logger.info(
                    f"ツイート {tweet.get('id_str', 'unknown')} のメディア処理完了: {len(all_media)}件（順番保持）"
                )

        except Exception as e:
            self.logger.error(f"ツイートメディア処理エラー: {e}")

        return tweet


# グローバルインスタンス
media_processor = MediaProcessor()
