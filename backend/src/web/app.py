"""
Twix Saver WebUI - FastAPI メインアプリケーション
TypeScript React フロントエンド用のバックエンドAPI
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from src.web.routers import users, jobs, tweets, websocket
from src.web.models import DashboardStats, SuccessResponse
from src.services.user_service import user_service
from src.services.job_service import job_service
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger


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
    
    # WebSocketバックグラウンドタスク開始
    websocket.start_background_tasks()
    
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
    lifespan=lifespan
)

# CORS設定（React開発サーバー用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(tweets.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")

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
        return JSONResponse({
            "message": "Twix Saver WebUI API",
            "status": "running",
            "docs_url": "/api/docs",
            "frontend_note": "React アプリは http://localhost:5173 で実行してください"
        })


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
            "timestamp": "2025-08-24T12:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        raise HTTPException(status_code=500, detail=f"システムエラー: {str(e)}")


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
            uptime_seconds=0.0  # TODO: 実際の稼働時間を計算
        )
        
        logger.info("ダッシュボード統計を取得しました")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"ダッシュボード統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ダッシュボード統計取得に失敗しました: {str(e)}")


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
                    "scraping_jobs": len(job_service.get_jobs(limit=1000))
                }
            },
            "scraping": {
                "running_jobs": len(job_service.get_running_jobs()),
                "active_users": len(user_service.get_active_users())
            },
            "websocket": {
                "active_connections": len(websocket.manager.active_connections)
            }
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
            "timestamp": "2025-08-24T12:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"システム状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"システム状態取得に失敗しました: {str(e)}")


# ===== エラーハンドラー =====

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404エラーハンドラー"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "リソースが見つかりません",
            "path": str(request.url.path)
        }
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
            "error_type": type(exc).__name__
        }
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
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )