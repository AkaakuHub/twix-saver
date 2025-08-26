"""
バッチ処理システム
ツイートの画像処理をバッチ単位で効率的に実行
"""

import asyncio
from typing import Any

from src.models.image_processing import ImageProcessingState, ImageProcessingStatus
from src.utils.logger import setup_logger
from src.utils.media_processor import media_processor


class BatchProcessor:
    """バッチ処理管理クラス"""

    def __init__(self, batch_size: int = 10, max_retries: int = 3):
        self.logger = setup_logger("batch_processor")
        self.batch_size = batch_size
        self.max_retries = max_retries

    def create_batches(self, items: list[Any], size: int = None) -> list[list[Any]]:
        """リストをバッチに分割"""
        batch_size = size or self.batch_size
        return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    async def process_tweets_with_images_batch(
        self, tweets: list[dict[str, Any]], db_manager, batch_size: int = None
    ) -> tuple[int, int, int]:
        """
        ツイートをバッチ単位で画像処理

        Returns:
            Tuple[processed_count, success_count, failed_count]
        """
        if not tweets:
            return 0, 0, 0

        batch_size = batch_size or self.batch_size
        batches = self.create_batches(tweets, batch_size)

        total_processed = 0
        total_success = 0
        total_failed = 0

        self.logger.info(f"開始: {len(tweets)}件のツイートを{len(batches)}バッチで処理")

        async with media_processor:
            for batch_idx, batch in enumerate(batches, 1):
                self.logger.info(f"バッチ {batch_idx}/{len(batches)} 処理開始 ({len(batch)}件)")

                # バッチ内のツイートを並行処理
                processed_tweets = await self._process_batch_parallel(batch, db_manager)

                # DB挿入（バッチ単位）
                if processed_tweets:
                    inserted_count = db_manager.insert_tweets(processed_tweets)

                    # 統計更新（実際に画像処理が実行されたもののみカウント）
                    success_count = sum(
                        1
                        for t in processed_tweets
                        if (
                            t.get("image_processing_status") == ImageProcessingStatus.COMPLETED.value
                            and t.get("_image_processing_executed", False)
                        )
                    )
                    failed_count = sum(
                        1
                        for t in processed_tweets
                        if t.get("image_processing_status") == ImageProcessingStatus.FAILED.value
                    )
                    skipped_count = sum(
                        1
                        for t in processed_tweets
                        if (
                            t.get("image_processing_status") == ImageProcessingStatus.COMPLETED.value
                            and not t.get("_image_processing_executed", False)
                        )
                    )

                    total_processed += len(processed_tweets)
                    total_success += success_count
                    total_failed += failed_count

                    self.logger.info(
                        f"バッチ {batch_idx} 完了: {inserted_count}件DB挿入, "
                        f"画像処理成功: {success_count}件, 失敗: {failed_count}件, スキップ: {skipped_count}件"
                    )

                # バッチ間の小休止（負荷軽減）
                if batch_idx < len(batches):
                    await asyncio.sleep(0.5)

        self.logger.info(
            f"全バッチ処理完了: 処理済み {total_processed}件, 成功 {total_success}件, 失敗 {total_failed}件"
        )

        return total_processed, total_success, total_failed

    async def _process_batch_parallel(self, batch: list[dict[str, Any]], db_manager) -> list[dict[str, Any]]:
        """バッチ内のツイートを並行処理"""
        processed_tweets = []

        # 各ツイートの処理をタスクとして作成
        tasks = []
        for tweet in batch:
            task = self._process_single_tweet_with_state(tweet, db_manager)
            tasks.append(task)

        # 並行実行（最大5件同時）
        semaphore = asyncio.Semaphore(5)

        async def process_with_semaphore(task):
            async with semaphore:
                return await task

        # 全タスクを並行実行
        results = await asyncio.gather(*[process_with_semaphore(task) for task in tasks], return_exceptions=True)

        # 結果をまとめる
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"ツイート処理でエラー: {result}")
            else:
                processed_tweets.append(result)

        return processed_tweets

    async def _process_single_tweet_with_state(self, tweet: dict[str, Any], db_manager) -> dict[str, Any]:
        """単一ツイートの画像処理（状態管理付き）"""
        try:
            # 画像処理状態の初期化
            if "image_processing_status" not in tweet:
                tweet.update(ImageProcessingState.create_initial_state())

            # 既に処理済みかチェック
            status = tweet.get("image_processing_status", "なし")
            tweet_id = tweet.get("id_str") or tweet.get("rest_id") or tweet.get("id") or "unknown"
            if not ImageProcessingState.is_processing_needed(tweet):
                # 処理不要の場合はそのまま返す（実行フラグはFalse）
                self.logger.info(f"ツイート {tweet_id} は処理済みのためスキップ (状態: {status})")
                tweet["_image_processing_executed"] = False
                return tweet

            # 処理中状態に更新
            tweet = ImageProcessingState.mark_as_processing(tweet)

            # 画像処理の実行
            original_media_count = len(tweet.get("downloaded_media", []))
            processed_tweet = await media_processor.process_tweet_media(tweet, db_manager)

            # 処理結果の確認
            new_media_count = len(processed_tweet.get("downloaded_media", []))

            if original_media_count == 0 and new_media_count == 0:
                # 画像がない場合はスキップ
                processed_tweet = ImageProcessingState.mark_as_skipped(processed_tweet)
            else:
                # 成功として処理（部分的成功も含む）
                processed_tweet = ImageProcessingState.mark_as_completed(
                    processed_tweet, new_media_count, new_media_count
                )

            # 実行フラグを設定
            processed_tweet["_image_processing_executed"] = True
            return processed_tweet

        except Exception as e:
            error_msg = f"画像処理エラー: {str(e)}"
            tweet_id = tweet.get("id_str") or tweet.get("rest_id") or tweet.get("id") or "unknown"
            self.logger.warning(f"ツイート {tweet_id} の{error_msg}")

            # 失敗状態に更新
            tweet = ImageProcessingState.mark_as_failed(tweet, error_msg)
            tweet["_image_processing_executed"] = True  # 失敗も実行扱い
            return tweet

    async def retry_failed_image_processing(self, db_manager, max_tweets: int = 100) -> tuple[int, int]:
        """
        画像処理が失敗したツイートのリトライ処理

        Returns:
            Tuple[retry_count, success_count]
        """
        if not db_manager.is_connected:
            self.logger.error("MongoDB接続が無効です")
            return 0, 0

        # 失敗したツイートを取得
        failed_filter = ImageProcessingState.get_failed_tweets_filter()
        failed_tweets = list(db_manager.db.tweets.find(failed_filter).limit(max_tweets))

        if not failed_tweets:
            self.logger.info("リトライ対象の失敗ツイートがありません")
            return 0, 0

        # リトライ可能なツイートのみフィルタリング
        retry_tweets = [tweet for tweet in failed_tweets if ImageProcessingState.should_retry(tweet, self.max_retries)]

        if not retry_tweets:
            self.logger.info("リトライ制限に達したため、リトライ対象なし")
            return 0, 0

        self.logger.info(f"画像処理失敗ツイートのリトライ開始: {len(retry_tweets)}件")

        # バッチ処理でリトライ
        processed, success, failed = await self.process_tweets_with_images_batch(retry_tweets, db_manager)

        self.logger.info(f"リトライ完了: {success}件成功, {failed}件失敗")
        return processed, success


# グローバルインスタンス
batch_processor = BatchProcessor()
