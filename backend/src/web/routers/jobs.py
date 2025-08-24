"""
スクレイピングジョブ管理API
ジョブの作成、監視、統計情報を提供
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import datetime

from src.web.models import (
    ScrapingJobCreate, ScrapingJobResponse, JobStatistics,
    SuccessResponse, PaginatedResponse
)
from src.services.job_service import job_service
from src.services.user_service import user_service
from src.utils.logger import setup_logger

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = setup_logger("api.jobs")


@router.get("/", response_model=List[ScrapingJobResponse])
async def get_jobs(
    status: Optional[str] = Query(None, description="ジョブステータスでフィルタ"),
    limit: int = Query(50, ge=1, le=100, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット")
):
    """ジョブ一覧を取得"""
    try:
        jobs = job_service.get_jobs(status=status, limit=limit, offset=offset)
        
        response_jobs = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # stats が ScrapingJobStats オブジェクトの場合は dict に変換
            if hasattr(job_dict.get('stats'), '__dict__'):
                job_dict['stats'] = vars(job_dict['stats'])
            elif job_dict.get('stats') is None:
                job_dict['stats'] = {
                    'tweets_collected': 0,
                    'articles_extracted': 0,
                    'media_downloaded': 0,
                    'errors_count': 0,
                    'processing_time_seconds': 0.0,
                    'pages_scrolled': 0,
                    'api_requests_made': 0
                }
            
            response_jobs.append(ScrapingJobResponse(**job_dict))
        
        logger.info(f"ジョブ一覧を取得: {len(response_jobs)}件")
        return response_jobs
        
    except Exception as e:
        logger.error(f"ジョブ一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ一覧取得に失敗しました: {str(e)}")


@router.get("/recent", response_model=List[ScrapingJobResponse])
async def get_recent_jobs(hours: int = Query(24, ge=1, le=168)):
    """最近のジョブを取得"""
    try:
        jobs = job_service.get_recent_jobs(hours=hours)
        
        response_jobs = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # stats の型変換
            if hasattr(job_dict.get('stats'), '__dict__'):
                job_dict['stats'] = vars(job_dict['stats'])
            elif job_dict.get('stats') is None:
                job_dict['stats'] = {
                    'tweets_collected': 0,
                    'articles_extracted': 0,
                    'media_downloaded': 0,
                    'errors_count': 0,
                    'processing_time_seconds': 0.0,
                    'pages_scrolled': 0,
                    'api_requests_made': 0
                }
            
            response_jobs.append(ScrapingJobResponse(**job_dict))
        
        logger.info(f"最近{hours}時間のジョブを取得: {len(response_jobs)}件")
        return response_jobs
        
    except Exception as e:
        logger.error(f"最近ジョブ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"最近ジョブ取得に失敗しました: {str(e)}")


@router.get("/running", response_model=List[ScrapingJobResponse])
async def get_running_jobs():
    """実行中のジョブを取得"""
    try:
        jobs = job_service.get_running_jobs()
        
        response_jobs = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # stats の型変換
            if hasattr(job_dict.get('stats'), '__dict__'):
                job_dict['stats'] = vars(job_dict['stats'])
            elif job_dict.get('stats') is None:
                job_dict['stats'] = {
                    'tweets_collected': 0,
                    'articles_extracted': 0,
                    'media_downloaded': 0,
                    'errors_count': 0,
                    'processing_time_seconds': 0.0,
                    'pages_scrolled': 0,
                    'api_requests_made': 0
                }
            
            response_jobs.append(ScrapingJobResponse(**job_dict))
        
        logger.info(f"実行中のジョブを取得: {len(response_jobs)}件")
        return response_jobs
        
    except Exception as e:
        logger.error(f"実行中ジョブ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"実行中ジョブ取得に失敗しました: {str(e)}")


@router.get("/active", response_model=List[ScrapingJobResponse])
async def get_active_jobs():
    """アクティブジョブを取得"""
    try:
        jobs = job_service.get_running_jobs()
        
        response_jobs = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # stats の型変換
            if hasattr(job_dict.get('stats'), '__dict__'):
                job_dict['stats'] = vars(job_dict['stats'])
            elif job_dict.get('stats') is None:
                job_dict['stats'] = {
                    'tweets_collected': 0,
                    'articles_extracted': 0,
                    'media_downloaded': 0,
                    'errors_count': 0,
                    'processing_time_seconds': 0.0,
                    'pages_scrolled': 0,
                    'api_requests_made': 0
                }
            
            response_jobs.append(ScrapingJobResponse(**job_dict))
        
        logger.info(f"アクティブジョブを取得: {len(response_jobs)}件")
        return response_jobs
        
    except Exception as e:
        logger.error(f"アクティブジョブ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アクティブジョブ取得に失敗しました: {str(e)}")


@router.get("/stats", response_model=JobStatistics)
async def get_job_stats(days: int = Query(7, ge=1, le=365)):
    """ジョブ統計を取得"""
    try:
        stats = job_service.get_job_statistics(days=days)
        
        return JobStatistics(
            total_jobs=stats.get("total_jobs", 0),
            completed_jobs=stats.get("completed_jobs", 0),
            failed_jobs=stats.get("failed_jobs", 0),
            total_tweets=stats.get("total_tweets", 0),
            total_articles=stats.get("total_articles", 0),
            success_rate=round(stats.get("success_rate", 0), 2),
            avg_processing_time=round(stats.get("avg_processing_time", 0), 2),
            daily_stats=stats.get("daily_stats", {})
        )
        
    except Exception as e:
        logger.error(f"ジョブ統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ統計取得に失敗しました: {str(e)}")


@router.get("/success-rate")
async def get_job_success_rate(days: int = Query(7, ge=1, le=365)):
    """ジョブ成功率を取得"""
    try:
        stats = job_service.get_job_statistics(days=days)
        success_rate = stats.get("success_rate", 0)
        
        return {
            "success_rate": round(success_rate, 2),
            "total_jobs": stats.get("total_jobs", 0),
            "completed_jobs": stats.get("completed_jobs", 0),
            "failed_jobs": stats.get("failed_jobs", 0),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"ジョブ成功率取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ成功率取得に失敗しました: {str(e)}")


@router.get("/{job_id}", response_model=ScrapingJobResponse)
async def get_job(job_id: str):
    """指定ジョブの詳細を取得"""
    try:
        job = job_service.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"ジョブが見つかりません: {job_id}")
        
        job_dict = job.to_dict()
        
        # stats の型変換
        if hasattr(job_dict.get('stats'), '__dict__'):
            job_dict['stats'] = vars(job_dict['stats'])
        elif job_dict.get('stats') is None:
            job_dict['stats'] = {
                'tweets_collected': 0,
                'articles_extracted': 0,
                'media_downloaded': 0,
                'errors_count': 0,
                'processing_time_seconds': 0.0,
                'pages_scrolled': 0,
                'api_requests_made': 0
            }
        
        return ScrapingJobResponse(**job_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ取得エラー ({job_id}): {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ取得に失敗しました: {str(e)}")


@router.post("/", response_model=SuccessResponse)
async def create_job(job_data: ScrapingJobCreate, background_tasks: BackgroundTasks):
    """新しいスクレイピングジョブを作成"""
    try:
        # ターゲットユーザー名の正規化（@マーク除去、空文字チェック）
        valid_users = []
        for username in job_data.target_usernames:
            normalized_username = username.lstrip('@').strip().lower()
            if normalized_username and len(normalized_username) > 0:
                valid_users.append(normalized_username)
            else:
                logger.warning(f"無効なユーザー名をスキップ: '{username}'")
        
        if not valid_users:
            raise HTTPException(
                status_code=400, 
                detail="有効なユーザー名が指定されていません"
            )
        
        # ジョブ作成
        job_id = job_service.create_job(
            target_usernames=valid_users,
            scraper_account=job_data.scraper_account,
            process_articles=job_data.process_articles,
            max_tweets=job_data.max_tweets
        )
        
        if not job_id:
            raise HTTPException(status_code=500, detail="ジョブの作成に失敗しました")
        
        logger.info(f"新しいスクレイピングジョブを作成: {job_id} "
                   f"(ターゲット: {', '.join(valid_users)})")
        
        # バックグラウンドでジョブを実行（実際の実装では非同期タスクキューを使用）
        # background_tasks.add_task(execute_scraping_job, job_id)
        
        return SuccessResponse(
            message=f"スクレイピングジョブを作成しました",
            data={
                "job_id": job_id,
                "target_users": valid_users,
                "process_articles": job_data.process_articles,
                "max_tweets": job_data.max_tweets
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ作成に失敗しました: {str(e)}")


@router.post("/create-from-active-users", response_model=SuccessResponse)
async def create_job_from_active_users(
    process_articles: bool = Query(True, description="記事抽出を実行するか"),
    max_tweets: Optional[int] = Query(None, description="最大ツイート数"),
    min_priority: int = Query(2, ge=1, le=4, description="最小優先度")
):
    """アクティブユーザーから自動的にジョブを作成"""
    try:
        # 指定優先度以上のアクティブユーザーを取得
        users = user_service.get_users_by_priority(min_priority)
        
        if not users:
            raise HTTPException(
                status_code=400,
                detail=f"優先度{min_priority}以上のアクティブユーザーが見つかりません"
            )
        
        usernames = [user.username for user in users]
        
        # ジョブ作成
        job_id = job_service.create_job(
            target_usernames=usernames,
            process_articles=process_articles,
            max_tweets=max_tweets
        )
        
        if not job_id:
            raise HTTPException(status_code=500, detail="ジョブの作成に失敗しました")
        
        logger.info(f"アクティブユーザーからジョブを作成: {job_id} "
                   f"({len(usernames)}ユーザー, 優先度{min_priority}以上)")
        
        return SuccessResponse(
            message=f"アクティブユーザーから自動ジョブを作成しました",
            data={
                "job_id": job_id,
                "target_users": usernames,
                "user_count": len(usernames),
                "min_priority": min_priority
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自動ジョブ作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"自動ジョブ作成に失敗しました: {str(e)}")


@router.post("/{job_id}/run", response_model=SuccessResponse)
async def run_job_immediately(job_id: str, background_tasks: BackgroundTasks):
    """指定されたジョブを即座に実行"""
    try:
        import subprocess
        from pathlib import Path
        
        # ジョブの存在確認
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        # ジョブが実行可能な状態か確認
        if job.status not in ["pending", "stopped", "failed", "cancelled", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"ジョブは実行できません。現在のステータス: {job.status}"
            )
        
        # 現在のプロジェクトディレクトリを取得
        project_root = Path(__file__).parent.parent.parent.parent
        backend_path = project_root / "backend"
        venv_python = backend_path / "venv" / "bin" / "python"
        main_script = backend_path / "main.py"
        
        # バックグラウンドで特定のjobを実行
        def run_single_job():
            try:
                subprocess.run(
                    [str(venv_python), str(main_script), "--run-single-job", job_id],
                    cwd=str(backend_path),
                    check=True
                )
                logger.info(f"ジョブ {job_id} の実行が完了しました")
            except subprocess.CalledProcessError as e:
                logger.error(f"ジョブ実行プロセスエラー: {e}")
            except Exception as e:
                logger.error(f"バックグラウンドジョブ実行エラー: {e}")
        
        background_tasks.add_task(run_single_job)
        
        logger.info(f"ジョブ {job_id} の即座実行を開始")
        return SuccessResponse(
            message=f"ジョブの実行を開始しました",
            data={
                "job_id": job_id,
                "status": "started"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ実行エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ実行開始に失敗しました: {str(e)}")


@router.post("/run-pending", response_model=SuccessResponse)
async def run_pending_jobs_now(background_tasks: BackgroundTasks):
    """待機中のジョブを即座に実行"""
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # 現在のプロジェクトディレクトリを取得
        project_root = Path(__file__).parent.parent.parent.parent
        backend_path = project_root / "backend"
        venv_python = backend_path / "venv" / "bin" / "python"
        main_script = backend_path / "main.py"
        
        # 待機中ジョブをカウント
        pending_jobs = job_service.get_jobs(status="pending", limit=100)
        job_count = len(pending_jobs)
        
        if job_count == 0:
            return SuccessResponse(
                message="実行待ちのジョブはありません",
                data={"pending_jobs": 0}
            )
        
        # バックグラウンドでjobを実行
        def run_jobs():
            try:
                subprocess.run(
                    [str(venv_python), str(main_script), "--run-jobs"],
                    cwd=str(backend_path),
                    check=True
                )
                logger.info(f"待機中ジョブの実行が完了しました")
            except subprocess.CalledProcessError as e:
                logger.error(f"ジョブ実行プロセスエラー: {e}")
            except Exception as e:
                logger.error(f"バックグラウンドジョブ実行エラー: {e}")
        
        background_tasks.add_task(run_jobs)
        
        logger.info(f"待機中ジョブの即座実行を開始: {job_count}件")
        return SuccessResponse(
            message=f"待機中のジョブ{job_count}件の実行を開始しました",
            data={
                "pending_jobs": job_count,
                "status": "started"
            }
        )
        
    except Exception as e:
        logger.error(f"待機中ジョブ実行エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ実行開始に失敗しました: {str(e)}")


@router.put("/{job_id}/start", response_model=SuccessResponse)
async def start_job(job_id: str):
    """ジョブを開始"""
    try:
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"ジョブが見つかりません: {job_id}")
        
        if job.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"ジョブは開始できません。現在のステータス: {job.status}"
            )
        
        success = job_service.start_job(job_id)
        
        if success:
            logger.info(f"ジョブを開始: {job_id}")
            return SuccessResponse(
                message=f"ジョブを開始しました",
                data={"job_id": job_id, "status": "running"}
            )
        else:
            raise HTTPException(status_code=400, detail="ジョブの開始に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ開始エラー ({job_id}): {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ開始に失敗しました: {str(e)}")


@router.put("/{job_id}/stop", response_model=SuccessResponse)
async def stop_job(job_id: str):
    """ジョブを停止"""
    try:
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"ジョブが見つかりません: {job_id}")
        
        if job.status not in ["running", "pending"]:
            raise HTTPException(
                status_code=400,
                detail=f"ジョブは停止できません。現在のステータス: {job.status}"
            )
        
        success = job_service.cancel_job(job_id)
        
        if success:
            logger.info(f"ジョブを停止: {job_id}")
            return SuccessResponse(
                message=f"ジョブを停止しました",
                data={"job_id": job_id, "status": "cancelled"}
            )
        else:
            raise HTTPException(status_code=400, detail="ジョブの停止に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ停止エラー ({job_id}): {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ停止に失敗しました: {str(e)}")


@router.put("/{job_id}/fail", response_model=SuccessResponse)
async def fail_job(job_id: str, error_message: str = Query(..., description="エラーメッセージ")):
    """ジョブを失敗状態にする"""
    try:
        job = job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"ジョブが見つかりません: {job_id}")
        
        success = job_service.fail_job(job_id, error_message)
        
        if success:
            logger.info(f"ジョブを失敗状態に更新: {job_id}")
            return SuccessResponse(
                message=f"ジョブを失敗状態にしました",
                data={"job_id": job_id, "status": "failed", "error": error_message}
            )
        else:
            raise HTTPException(status_code=400, detail="ジョブの失敗更新に失敗しました")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブ失敗更新エラー ({job_id}): {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ失敗更新に失敗しました: {str(e)}")


@router.get("/stats/summary", response_model=JobStatistics)
async def get_job_statistics(days: int = Query(30, ge=1, le=365)):
    """ジョブ統計情報を取得"""
    try:
        stats = job_service.get_job_statistics(days=days)
        
        return JobStatistics(
            total_jobs=stats.get("total_jobs", 0),
            completed_jobs=stats.get("completed_jobs", 0),
            failed_jobs=stats.get("failed_jobs", 0),
            total_tweets=stats.get("total_tweets", 0),
            total_articles=stats.get("total_articles", 0),
            success_rate=round(stats.get("success_rate", 0), 2),
            avg_processing_time=round(stats.get("avg_processing_time", 0), 2),
            daily_stats=stats.get("daily_stats", {})
        )
        
    except Exception as e:
        logger.error(f"ジョブ統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブ統計取得に失敗しました: {str(e)}")


@router.delete("/cleanup", response_model=SuccessResponse)
async def cleanup_old_jobs(days: int = Query(30, ge=1, le=365)):
    """古いジョブをクリーンアップ"""
    try:
        deleted_count = job_service.cleanup_old_jobs(days=days)
        
        logger.info(f"古いジョブをクリーンアップ: {deleted_count}件削除")
        return SuccessResponse(
            message=f"{days}日以前の完了・失敗ジョブを削除しました",
            data={"deleted_count": deleted_count, "days": days}
        )
        
    except Exception as e:
        logger.error(f"ジョブクリーンアップエラー: {e}")
        raise HTTPException(status_code=500, detail=f"ジョブクリーンアップに失敗しました: {str(e)}")


# 将来の実装: ジョブ実行のためのバックグラウンドタスク
async def execute_scraping_job(job_id: str):
    """スクレイピングジョブを実際に実行（プレースホルダー実装）"""
    # ここで実際のスクレイピング処理を呼び出し
    # main.py の機能を非同期で実行
    pass