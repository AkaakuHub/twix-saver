#!/usr/bin/env python3
"""
X.com スクレイピングボット - メイン実行スクリプト

データベース駆動でジョブを実行し、WebSocket経由でリアルタイム更新を送信
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.scrapers.twitter_scraper import ScrapingSession
from src.utils.data_manager import data_ingest_service
from src.utils.article_extractor import content_processor
from src.utils.logger import setup_logger, log_scraping_stats
from src.services.job_service import job_service
from src.models.database import ScrapingJob, ScrapingJobStatus, ScrapingJobStats
# WebSocket廃止済み


async def execute_job(job: ScrapingJob) -> bool:
    """データベースジョブを実行"""
    logger = setup_logger("job_executor")
    job_id = job.job_id
    
    try:
        # ジョブ開始
        if not job_service.start_job(job_id):
            logger.error(f"ジョブの開始に失敗: {job_id}")
            return False
        
        # WebSocket廃止済み
        
        logger.info(f"ジョブを実行開始: {job_id} (ターゲット: {', '.join(job.target_usernames)})")
        
        # Twitterアカウント設定チェック（DB連携）
        from src.services.account_service import twitter_account_service
        available_accounts = twitter_account_service.get_available_accounts()
        if not available_accounts:
            error_msg = "利用可能なTwitterアカウントがありません。設定画面でTwitterアカウントを追加してください。"
            job_service.fail_job(job_id, error_msg)
            # WebSocket廃止済み
            return False
        
        start_time = time.time()
        stats = ScrapingJobStats()
        
        # スクレイピングセッション実行
        logger.info(f"ジョブ {job_id}: スクレイピングセッションを開始 (対象: {', '.join(job.target_usernames)})")
        job_service.add_job_log(job_id, f"スクレイピングセッションを開始: {', '.join(job.target_usernames)}")
        
        try:
            session = ScrapingSession()
            results = await session.run_session(job.target_usernames)
            logger.info(f"ジョブ {job_id}: スクレイピングセッション完了 - 結果: {list(results.keys())}")
        except Exception as e:
            logger.error(f"ジョブ {job_id}: スクレイピングセッションエラー: {e}")
            job_service.add_job_log(job_id, f"スクレイピングエラー: {str(e)}")
            raise
        
        total_tweets = sum(len(tweets) for tweets in results.values())
        stats.tweets_collected = total_tweets
        
        # 進捗ログ
        job_service.add_job_log(job_id, f"スクレイピング完了: {total_tweets}件のツイートを取得")
        # WebSocket廃止済み
        
        if total_tweets == 0:
            logger.warning(f"ジョブ {job_id}: 取得できたツイートがありません")
            job_service.add_job_log(job_id, "取得できたツイートがありませんでした")
        
        # 記事コンテンツの処理
        if job.process_articles and total_tweets > 0:
            job_service.add_job_log(job_id, "リンク先記事の処理を開始")
            # WebSocket廃止済み
            
            articles_count = 0
            for username, tweets in results.items():
                logger.info(f"@{username} のリンクを処理中...")
                job_service.add_job_log(job_id, f"@{username} のリンクを処理中")
                
                for tweet in tweets:
                    try:
                        # リンクからコンテンツを抽出
                        content_results = await content_processor.process_tweet_links(tweet)
                        
                        # ツイートデータに記事情報を追加
                        if content_results['articles']:
                            tweet['extracted_articles'] = content_results['articles']
                            articles_count += len(content_results['articles'])
                        
                        if content_results['media']:
                            tweet['downloaded_media'] = content_results['media']
                            stats.media_downloaded += len(content_results['media'])
                        
                    except Exception as e:
                        logger.error(f"記事処理エラー: {e}")
                        job_service.add_job_log(job_id, f"記事処理エラー: {e}")
            
            stats.articles_extracted = articles_count
            job_service.add_job_log(job_id, f"記事処理完了: {articles_count}件")
        
        # 進捗更新
        # WebSocket廃止済み
        
        # データインジェスト実行
        logger.info(f"ジョブ {job_id}: データインジェストを実行")
        job_service.add_job_log(job_id, "データインジェストを実行中")
        ingest_results = data_ingest_service.process_jsonl_files()
        
        job_service.add_job_log(job_id, 
            f"インジェスト完了: ファイル{ingest_results['processed_files']}件, "
            f"ツイート{ingest_results['processed_tweets']}件, "
            f"記事{ingest_results['processed_articles']}件")
        
        # 統計情報を更新
        session_duration = time.time() - start_time
        stats.processing_time_seconds = session_duration
        
        # ジョブ完了
        job_service.complete_job(job_id, stats)
        
        # WebSocket廃止済み
        
        logger.info(f"ジョブが正常に完了: {job_id}")
        log_scraping_stats(total_tweets, 0, session_duration)
        
        return True
        
    except Exception as e:
        logger.error(f"ジョブ実行エラー ({job_id}): {e}")
        job_service.fail_job(job_id, str(e))
        
        # WebSocket廃止済み
        
        return False


async def main_scraping_task(target_users: List[str], process_articles: bool = True) -> bool:
    """従来のコマンドライン用スクレイピングタスク（後方互換性）"""
    logger = setup_logger("main")
    
    # ジョブを作成して実行
    job_id = job_service.create_job(
        target_usernames=target_users,
        process_articles=process_articles
    )
    
    if not job_id:
        logger.error("ジョブの作成に失敗しました")
        return False
    
    # ジョブを取得して実行
    job = job_service.get_job(job_id)
    if not job:
        logger.error(f"作成したジョブが見つかりません: {job_id}")
        return False
    
    return await execute_job(job)


def data_ingest_only():
    """データインジェストのみを実行"""
    logger = setup_logger("ingest_only")
    
    logger.info("データインジェストを開始...")
    
    try:
        results = data_ingest_service.process_jsonl_files()
        
        logger.info(f"インジェスト完了: ファイル{results['processed_files']}件, "
                   f"ツイート{results['processed_tweets']}件, "
                   f"記事{results['processed_articles']}件")
        
        return True
        
    except Exception as e:
        logger.error(f"データインジェストでエラーが発生: {e}")
        return False


def show_stats():
    """統計情報の表示"""
    logger = setup_logger("stats")
    
    from src.utils.data_manager import mongodb_manager
    
    if not mongodb_manager.is_connected:
        logger.error("MongoDBに接続できません")
        return False
    
    try:
        stats = mongodb_manager.get_tweet_stats()
        
        print("\n=== Twitter スクレイパー統計 ===")
        print(f"総ツイート数: {stats.get('total_tweets', 0):,}")
        print(f"最新取得日時: {stats.get('latest_scraped', 'なし')}")
        
        print("\n=== スクレイパー別統計 ===")
        for scraper_stat in stats.get('scraper_stats', []):
            account = scraper_stat['_id'] or '不明'
            count = scraper_stat['count']
            print(f"  {account}: {count:,}件")
        
        print()
        return True
        
    except Exception as e:
        logger.error(f"統計取得エラー: {e}")
        return False


async def run_pending_jobs():
    """待機中のジョブを実行"""
    logger = setup_logger("job_runner")
    
    logger.info("待機中のジョブを検索しています...")
    pending_jobs = job_service.get_jobs(status=ScrapingJobStatus.PENDING.value, limit=10)
    
    if not pending_jobs:
        logger.info("実行可能なジョブがありません")
        return True
    
    logger.info(f"{len(pending_jobs)}件の待機中ジョブを発見")
    
    success_count = 0
    for job in pending_jobs:
        logger.info(f"ジョブを実行中: {job.job_id}")
        
        try:
            success = await execute_job(job)
            if success:
                success_count += 1
            
            # ジョブ間の休憩（レート制限対応）
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"ジョブ実行中にエラー ({job.job_id}): {e}")
    
    logger.info(f"ジョブ実行完了: {success_count}/{len(pending_jobs)}件が成功")
    return success_count == len(pending_jobs)


async def run_single_job(job_id: str):
    """指定されたジョブを実行"""
    logger = setup_logger("single_job_runner")
    
    logger.info(f"ジョブ {job_id} を検索しています...")
    job = job_service.get_job(job_id)
    
    if not job:
        logger.error(f"ジョブが見つかりません: {job_id}")
        return False
    
    if job.status not in [ScrapingJobStatus.PENDING.value, ScrapingJobStatus.FAILED.value, ScrapingJobStatus.CANCELLED.value, ScrapingJobStatus.RUNNING.value]:
        logger.error(f"ジョブは実行できません。現在のステータス: {job.status}")
        return False
    
    logger.info(f"ジョブを実行中: {job.job_id}")
    
    # ジョブが完了またはキャンセル状態の場合は、状態をリセット
    if job.status in [ScrapingJobStatus.COMPLETED.value, ScrapingJobStatus.CANCELLED.value, ScrapingJobStatus.FAILED.value]:
        logger.info(f"ジョブ状態をリセット: {job.job_id} ({job.status} -> pending)")
        job_service.collection.update_one(
            {"job_id": job.job_id},
            {
                "$set": {
                    "status": ScrapingJobStatus.PENDING.value,
                    "completed_at": None,
                    "started_at": None
                },
                "$unset": {
                    "errors": "",
                }
            }
        )
        # ジョブオブジェクトを再取得
        job = job_service.get_job(job.job_id)
    
    try:
        success = await execute_job(job)
        if success:
            logger.info(f"ジョブ実行完了: {job.job_id}")
        else:
            logger.error(f"ジョブ実行失敗: {job.job_id}")
        return success
    except Exception as e:
        logger.error(f"ジョブ実行中にエラー ({job.job_id}): {e}")
        return False


def main():
    """コマンドライン実行のメイン関数"""
    parser = argparse.ArgumentParser(
        description="X.com レジリエントスクレイピングボット",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --users elonmusk jack dorsey    # 指定ユーザーをスクレイピング
  %(prog)s --run-jobs                      # データベースの待機中ジョブを実行
  %(prog)s --ingest-only                   # データインジェストのみ実行
  %(prog)s --stats                         # 統計情報を表示
  %(prog)s --users elonmusk --no-articles  # 記事処理なしでスクレイピング
        """
    )
    
    parser.add_argument(
        '--users', '-u',
        nargs='+',
        help='スクレイピング対象のユーザー名（@なし）'
    )
    
    parser.add_argument(
        '--run-jobs',
        action='store_true',
        help='データベースの待機中ジョブを実行'
    )
    
    parser.add_argument(
        '--run-single-job',
        type=str,
        help='指定されたジョブIDの単一ジョブを実行'
    )
    
    parser.add_argument(
        '--ingest-only',
        action='store_true',
        help='データインジェストのみを実行（スクレイピングは行わない）'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='統計情報を表示'
    )
    
    parser.add_argument(
        '--no-articles',
        action='store_true',
        help='記事コンテンツの処理をスキップ'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=None,
        help='ログレベルを指定'
    )
    
    args = parser.parse_args()
    
    # ログレベル設定
    if args.log_level:
        settings.log_level = args.log_level
    
    # 統計表示
    if args.stats:
        success = show_stats()
        sys.exit(0 if success else 1)
    
    # データインジェストのみ
    if args.ingest_only:
        success = data_ingest_only()
        sys.exit(0 if success else 1)
    
    # データベースジョブを実行
    if args.run_jobs:
        success = asyncio.run(run_pending_jobs())
        sys.exit(0 if success else 1)
    
    # 単一ジョブを実行
    if args.run_single_job:
        success = asyncio.run(run_single_job(args.run_single_job))
        sys.exit(0 if success else 1)
    
    # スクレイピング実行（従来方式）
    if not args.users:
        parser.error("--users, --run-jobs, または --run-single-job オプションを指定してください")
    
    # 非同期実行
    success = asyncio.run(
        main_scraping_task(
            args.users,
            process_articles=not args.no_articles
        )
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()