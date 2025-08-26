"""
記事コンテンツ抽出システム
readability-lxml を使用したリンク先記事の抽出とクリーニング
"""

import asyncio
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from readability import Document

from src.config.settings import settings
from src.utils.anti_detection import anti_detection
from src.utils.logger import setup_logger


class ArticleExtractor:
    """記事コンテンツの抽出クラス"""

    def __init__(self):
        self.logger = setup_logger("article_extractor")
        self.session = requests.Session()

        # 記事として処理するドメインのパターン
        self.article_domains = {
            "news",
            "blog",
            "medium",
            "qiita",
            "zenn",
            "note",
            "wikipedia",
            "github",
            "stackoverflow",
        }

        # 除外するドメインパターン
        self.excluded_domains = {
            "twitter.com",
            "x.com",
            "t.co",
            "pic.twitter.com",
            "youtube.com",
            "youtu.be",
            "instagram.com",
            "facebook.com",
            "tiktok.com",
        }

        # 記事として処理するファイル拡張子
        self.article_extensions = {".html", ".htm", ".php", ".asp", ".jsp"}

        # 処理済みURL（重複回避用）
        self.processed_urls: set[str] = set()

        self.logger.info("記事抽出システムを初期化しました")

    def extract_links_from_tweet(self, tweet_data: dict) -> list[str]:
        """ツイートデータからリンクを抽出"""
        links = []

        try:
            # legacy形式のツイートからURL抽出
            if "legacy" in tweet_data and "entities" in tweet_data["legacy"]:
                entities = tweet_data["legacy"]["entities"]

                # urls から展開されたURLを取得
                if "urls" in entities:
                    for url_entity in entities["urls"]:
                        expanded_url = url_entity.get("expanded_url") or url_entity.get("url")
                        if expanded_url:
                            links.append(expanded_url)

                # media URLs（画像・動画）
                if "media" in entities:
                    for media_entity in entities["media"]:
                        expanded_url = media_entity.get("expanded_url")
                        if expanded_url:
                            links.append(expanded_url)

            # 新しい形式のツイートデータからも抽出を試行
            self._extract_links_recursive(tweet_data, links)

        except Exception as e:
            self.logger.error(f"リンク抽出エラー: {e}")

        # 重複除去とフィルタリング
        unique_links = list(set(links))
        filtered_links = [link for link in unique_links if self._should_process_link(link)]

        if filtered_links:
            self.logger.debug(f"抽出リンク数: {len(filtered_links)}")

        return filtered_links

    def _extract_links_recursive(self, obj, links: list[str]):
        """再帰的にオブジェクトからURLを抽出"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ["url", "expanded_url", "display_url"] and isinstance(value, str):
                    if value.startswith("http"):
                        links.append(value)
                else:
                    self._extract_links_recursive(value, links)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_links_recursive(item, links)

    def _should_process_link(self, url: str) -> bool:
        """リンクを処理すべきかどうかを判定"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()

            # 既に処理済みのURL
            if url in self.processed_urls:
                return False

            # 除外ドメイン
            if any(excluded in domain for excluded in self.excluded_domains):
                return False

            # ファイル拡張子チェック
            file_ext = Path(path).suffix
            if file_ext and file_ext not in self.article_extensions:
                # 画像・動画・PDFなどは別途処理
                return False

            # 記事ドメインの場合は優先的に処理
            if any(article_domain in domain for article_domain in self.article_domains):
                return True

            # 一般的なウェブページは処理対象
            return True

        except Exception as e:
            self.logger.debug(f"リンク判定エラー ({url}): {e}")
            return False

    async def extract_article_content(self, url: str, use_playwright: bool = False) -> Optional[dict]:
        """記事コンテンツの抽出"""
        if url in self.processed_urls:
            return None

        try:
            self.processed_urls.add(url)

            if use_playwright:
                content = await self._extract_with_playwright(url)
            else:
                content = self._extract_with_requests(url)

            if content:
                self.logger.info(f"記事抽出成功: {url}")
                return content

        except Exception as e:
            self.logger.error(f"記事抽出エラー ({url}): {e}")

        return None

    def _extract_with_requests(self, url: str) -> Optional[dict]:
        """requests を使用した記事抽出"""
        try:
            # User-Agentをランダムに設定
            headers = {
                "User-Agent": anti_detection.get_random_user_agent(use_fake_useragent=True),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            # タイムアウト設定
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Content-Type チェック
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                self.logger.debug(f"HTML以外のコンテンツ ({url}): {content_type}")
                return None

            # readability による記事抽出
            doc = Document(response.content, url=url)

            article = {
                "url": url,
                "title": doc.title(),
                "content": doc.summary(),
                "text_content": self._html_to_text(doc.summary()),
                "retrieved_at": datetime.utcnow().isoformat(),
                "content_type": content_type,
                "status_code": response.status_code,
                "extraction_method": "requests",
            }

            # メタデータの抽出
            try:
                # エンコーディングを安全に取得
                encoding = response.encoding or "utf-8"
                if (
                    encoding.lower() in ["iso-8859-1", "windows-1252"]
                    and "charset=" not in response.headers.get("content-type", "").lower()
                ):
                    # デフォルトエンコーディングが設定されている場合はutf-8を試す
                    encoding = "utf-8"

                html_content = response.content.decode(encoding, errors="replace")
                self._extract_metadata(html_content, article)
            except (UnicodeDecodeError, LookupError) as e:
                self.logger.warning(f"エンコーディングエラー ({url}): {e}, fallback to utf-8")
                try:
                    html_content = response.content.decode("utf-8", errors="replace")
                    self._extract_metadata(html_content, article)
                except Exception:
                    self.logger.warning(f"メタデータ抽出をスキップ: {url}")
            except Exception as e:
                self.logger.warning(f"メタデータ抽出エラー ({url}): {e}")

            return article

        except Exception as e:
            self.logger.error(f"requests抽出エラー ({url}): {e}")
            return None

    async def _extract_with_playwright(self, url: str) -> Optional[dict]:
        """Playwright を使用した記事抽出（JavaScript必須サイト用）"""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                context_options = {"user_agent": anti_detection.get_random_user_agent()}

                # プロキシ設定
                proxy_config = settings.get_proxy_config()
                if proxy_config:
                    context_options["proxy"] = proxy_config

                context = await browser.new_context(**context_options)
                page = await context.new_page()

                # ページに移動
                await page.goto(url, wait_until="networkidle")

                # HTML取得
                html_content = await page.content()

                await context.close()
                await browser.close()

                # readability による記事抽出
                doc = Document(html_content, url=url)

                article = {
                    "url": url,
                    "title": doc.title(),
                    "content": doc.summary(),
                    "text_content": self._html_to_text(doc.summary()),
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "extraction_method": "playwright",
                }

                # メタデータの抽出
                self._extract_metadata(html_content, article)

                return article

        except Exception as e:
            self.logger.error(f"Playwright抽出エラー ({url}): {e}")
            return None

    def _html_to_text(self, html_content: str) -> str:
        """HTMLからプレーンテキストを抽出"""
        try:
            import re
            from html import unescape

            # HTMLタグを除去
            text = re.sub(r"<[^>]+>", "", html_content)
            # HTMLエンティティをデコード
            text = unescape(text)
            # 余分な空白を除去
            text = re.sub(r"\s+", " ", text).strip()

            return text

        except Exception as e:
            self.logger.error(f"テキスト抽出エラー: {e}")
            return ""

    def _extract_metadata(self, html_content: str, article: dict):
        """HTMLからメタデータを抽出"""
        try:
            # 型チェック：bytesオブジェクトの場合はデコード
            if isinstance(html_content, bytes):
                html_content = html_content.decode("utf-8", errors="replace")
            # 基本的なメタタグの抽出
            meta_patterns = {
                "description": [
                    r'<meta\s+name="description"\s+content="([^"]+)"',
                    r'<meta\s+property="og:description"\s+content="([^"]+)"',
                ],
                "author": [
                    r'<meta\s+name="author"\s+content="([^"]+)"',
                    r'<meta\s+property="article:author"\s+content="([^"]+)"',
                ],
                "published_time": [r'<meta\s+property="article:published_time"\s+content="([^"]+)"'],
                "keywords": [r'<meta\s+name="keywords"\s+content="([^"]+)"'],
            }

            for field, patterns in meta_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        article[field] = match.group(1).strip()
                        break

            # 文字数統計
            if article.get("text_content"):
                article["character_count"] = len(article["text_content"])
                article["word_count"] = len(article["text_content"].split())

        except Exception as e:
            self.logger.debug(f"メタデータ抽出エラー: {e}")


class MediaDownloader:
    """メディアファイル（画像・動画）のダウンロードクラス"""

    def __init__(self):
        self.logger = setup_logger("media_downloader")
        self.session = requests.Session()
        self.media_dir = Path(settings.data_dir) / "media"
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def download_media(self, url: str) -> Optional[dict]:
        """メディアファイルのダウンロード"""
        try:
            headers = {"User-Agent": anti_detection.get_random_user_agent(use_fake_useragent=True)}

            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Content-Type から拡張子を決定
            content_type = response.headers.get("content-type", "")
            extension = mimetypes.guess_extension(content_type) or ".bin"

            # ファイル名生成
            parsed_url = urlparse(url)
            filename_base = Path(parsed_url.path).stem or "media"
            timestamp = int(datetime.now().timestamp())
            filename = f"{filename_base}_{timestamp}{extension}"

            filepath = self.media_dir / filename

            # ファイル保存
            with open(filepath, "wb") as f:
                f.write(response.content)

            media_info = {
                "url": url,
                "filepath": str(filepath),
                "filename": filename,
                "content_type": content_type,
                "file_size": len(response.content),
                "downloaded_at": datetime.utcnow().isoformat(),
            }

            self.logger.info(f"メディアダウンロード完了: {filename}")
            return media_info

        except Exception as e:
            self.logger.error(f"メディアダウンロードエラー ({url}): {e}")
            return None


class ContentProcessor:
    """ツイートから抽出したリンクコンテンツの統合処理クラス"""

    def __init__(self):
        self.article_extractor = ArticleExtractor()
        self.media_downloader = MediaDownloader()
        self.logger = setup_logger("content_processor")

    async def process_tweet_links(self, tweet_data: dict) -> dict[str, list[dict]]:
        """ツイート内のリンクからコンテンツを抽出・処理"""
        results = {"articles": [], "media": []}

        # リンク抽出
        links = self.article_extractor.extract_links_from_tweet(tweet_data)

        if not links:
            return results

        self.logger.info(f"リンク処理開始: {len(links)}件")

        for url in links:
            try:
                # リンクタイプの判定
                if self._is_media_link(url):
                    # メディアダウンロード
                    media_info = self.media_downloader.download_media(url)
                    if media_info:
                        results["media"].append(media_info)
                else:
                    # 記事コンテンツ抽出
                    article = await self.article_extractor.extract_article_content(url)
                    if article:
                        results["articles"].append(article)

                # レート制限対策
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"リンク処理エラー ({url}): {e}")

        self.logger.info(f"リンク処理完了: 記事{len(results['articles'])}件, メディア{len(results['media'])}件")

        return results

    def _is_media_link(self, url: str) -> bool:
        """メディアリンクかどうかを判定"""
        media_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".mp4",
            ".mov",
            ".avi",
            ".pdf",
        }
        parsed = urlparse(url)
        extension = Path(parsed.path).suffix.lower()

        return extension in media_extensions


# グローバルインスタンス
article_extractor = ArticleExtractor()
content_processor = ContentProcessor()
