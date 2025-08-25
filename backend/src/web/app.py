"""
Twix Saver WebUI - FastAPI メインアプリケーション
TypeScript React フロントエンド用のバックエンドAPI
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config.ports import CORS_ORIGINS
from src.config.settings import initialize_settings
from src.services.job_service import job_service
from src.services.user_service import user_service
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger
from src.web.models import DashboardStats
from src.web.routers import accounts, jobs, media, settings, tweets, users

# Load root .env file for port configuration
root_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(root_env_path)


# ライフサイクル管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    logger = setup_logger("web_app")

    # 起動時の処理
    logger.info("Twix Saver WebUI を起動中...")

    # MongoDB接続チェック
    if not mongodb_manager.is_connected:
        logger.error("MongoDB に接続できません")
        raise RuntimeError("データベース接続エラー")

    # 設定システム初期化
    initialize_settings()
    logger.info("DB連携設定システムを初期化しました")

    # WebSocket機能は削除済み

    logger.info("WebUI サーバーが正常に起動しました")

    yield

    # 終了時の処理
    logger.info("WebUI サーバーを終了中...")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Twix Saver WebUI API",
    description="X.com スクレイピングボットの Web管理インターフェース",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS設定（ポート設定から動的に生成）

cors_origins = CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(tweets.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(media.router, prefix="/api")
# WebSocketルーターを削除しました

# ロガー設定
logger = setup_logger("web_app")


# ===== メインエンドポイント =====


@app.get("/", response_class=FileResponse)
async def read_root():
    """ルートエンドポイント（React アプリを返す）"""
    # 本番環境では React ビルドファイルを返す
    static_dir = os.path.join(os.path.dirname(__file__), "../../web-ui/dist")
    index_file = os.path.join(static_dir, "index.html")

    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        # 開発環境用のプレースホルダー
        return JSONResponse(
            {
                "message": "Twix Saver WebUI API",
                "status": "running",
                "docs_url": "/api/docs",
                "frontend_note": "React アプリは http://localhost:5173 で実行してください",
            }
        )


@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # MongoDB接続チェック
        db_status = "connected" if mongodb_manager.is_connected else "disconnected"

        # 簡単な統計取得テスト
        user_count = len(user_service.get_all_users())

        return {
            "status": "healthy",
            "database": db_status,
            "user_count": user_count,
            "timestamp": "2025-08-24T12:00:00Z",
        }

    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        raise HTTPException(status_code=500, detail=f"システムエラー: {str(e)}") from None


@app.get("/api/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """ダッシュボード統計情報"""
    try:
        # ユーザー統計
        user_stats = user_service.get_user_stats()

        # ジョブ統計
        job_stats = job_service.get_job_statistics(days=1)
        running_jobs = job_service.get_running_jobs()

        # MongoDB統計
        mongo_stats = mongodb_manager.get_tweet_stats()

        # システム状態の判定
        system_status = "idle"
        if running_jobs:
            system_status = "running"
        elif job_stats.get("failed_jobs", 0) > 0:
            system_status = "error"

        dashboard_data = DashboardStats(
            # ユーザー統計
            total_users=user_stats.get("total_users", 0),
            active_users=user_stats.get("active_users", 0),
            # ツイート統計
            total_tweets=mongo_stats.get("total_tweets", 0),
            tweets_today=job_stats.get("total_tweets", 0),
            tweets_this_week=mongo_stats.get("total_tweets", 0),  # 暫定
            # 記事統計
            total_articles=user_stats.get("total_articles", 0),
            articles_today=job_stats.get("total_articles", 0),
            # ジョブ統計
            total_jobs=job_stats.get("total_jobs", 0),
            running_jobs=len(running_jobs),
            completed_jobs_today=job_stats.get("completed_jobs", 0),
            failed_jobs_today=job_stats.get("failed_jobs", 0),
            # システム情報
            last_scraping_at=mongo_stats.get("latest_scraped"),
            system_status=system_status,
            uptime_seconds=0.0,  # TODO: 実際の稼働時間を計算
        )

        logger.info("ダッシュボード統計を取得しました")
        return dashboard_data

    except Exception as e:
        logger.error(f"ダッシュボード統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ダッシュボード統計取得に失敗しました: {str(e)}") from None


@app.get("/api/status")
async def get_system_status():
    """システム状態の詳細情報"""
    try:
        # 各サービスの状態チェック
        services_status = {
            "database": {
                "status": "connected" if mongodb_manager.is_connected else "disconnected",
                "collections": {
                    "tweets": mongodb_manager.tweets_collection.count_documents({}),
                    "target_users": len(user_service.get_all_users()),
                    "scraping_jobs": len(job_service.get_jobs(limit=1000)),
                },
            },
            "scraping": {
                "running_jobs": len(job_service.get_running_jobs()),
                "active_users": len(user_service.get_active_users()),
            },
        }

        # 全体的な健全性スコア
        health_score = 100
        if not mongodb_manager.is_connected:
            health_score -= 50
        if len(user_service.get_active_users()) == 0:
            health_score -= 25

        return {
            "overall_status": "healthy" if health_score > 75 else "warning" if health_score > 25 else "critical",
            "health_score": health_score,
            "services": services_status,
            "timestamp": "2025-08-24T12:00:00Z",
        }

    except Exception as e:
        logger.error(f"システム状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"システム状態取得に失敗しました: {str(e)}") from None


@app.get("/api/activities")
async def get_activities(limit: int = 50):
    """アクティビティフィードを取得"""
    try:
        activities = []

        # 最近のジョブ（過去24時間）
        recent_jobs = job_service.get_recent_jobs(hours=24)
        for job in recent_jobs:
            activities.append(
                {
                    "id": str(job.id),
                    "type": "job",
                    "action": f"ジョブ{job.status}",
                    "message": f"スクレイピングジョブ '{job.id}' が{job.status}になりました",
                    "timestamp": job.created_at or job.updated_at,
                    "data": {
                        "job_id": job.id,
                        "status": job.status,
                        "target_users": len(job.target_usernames) if job.target_usernames else 0,
                    },
                }
            )

        # 最近のツイート（過去1時間）
        from datetime import datetime, timedelta

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        recent_tweets = list(
            mongodb_manager.tweets_collection.find({"scraped_at": {"$gte": one_hour_ago}})
            .sort("scraped_at", -1)
            .limit(20)
        )

        for tweet in recent_tweets:
            username = ""
            if "legacy" in tweet and "user" in tweet["legacy"]:
                username = tweet["legacy"]["user"].get("screen_name", "")
            elif "core" in tweet and "user_results" in tweet["core"]:
                user_result = tweet["core"]["user_results"].get("result", {})
                if "legacy" in user_result:
                    username = user_result["legacy"].get("screen_name", "")

            activities.append(
                {
                    "id": tweet.get("id_str", str(tweet.get("_id", ""))),
                    "type": "tweet",
                    "action": "ツイート収集",
                    "message": f"@{username} のツイートを収集しました",
                    "timestamp": tweet.get("scraped_at"),
                    "data": {
                        "tweet_id": tweet.get("id_str"),
                        "username": username,
                        "has_articles": bool(tweet.get("extracted_articles")),
                        "has_media": bool(tweet.get("downloaded_media")),
                    },
                }
            )

        # アクティビティを時系列でソート
        activities.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)

        # 制限数まで取得
        activities = activities[:limit]

        logger.info(f"アクティビティフィードを取得: {len(activities)}件")
        return activities

    except Exception as e:
        logger.error(f"アクティビティフィード取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"アクティビティフィード取得に失敗しました: {str(e)}",
        ) from None


# ===== エラーハンドラー =====


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404エラーハンドラー"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "リソースが見つかりません",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """500エラーハンドラー"""
    logger.error(f"内部サーバーエラー: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "内部サーバーエラーが発生しました",
            "error_type": type(exc).__name__,
        },
    )


# ===== 静的ファイル配信 (本番用) =====

# React ビルドファイルの配信（本番環境用）
static_dir = os.path.join(os.path.dirname(__file__), "../../web-ui/dist")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    # 開発用サーバー起動
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",  # noqa: S104
        port=int(os.getenv("VITE_BACKEND_PORT", 8000)),
        reload=True,
        log_level="info",
    )
