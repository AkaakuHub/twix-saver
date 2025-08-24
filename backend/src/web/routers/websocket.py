"""
WebSocket リアルタイム通信API
スクレイピング状況とログのリアルタイム配信
"""

import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from src.web.models import WebSocketMessage, LogMessage
from src.services.job_service import job_service
from src.services.user_service import user_service
from src.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("api.websocket")


class ConnectionManager:
    """WebSocket接続管理クラス"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """新しい接続を受け入れ"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = client_info or {}
        
        logger.info(f"WebSocket接続を開始: {len(self.active_connections)}件の接続")
        
        # 接続通知を他のクライアントに送信
        await self.broadcast({
            "type": "connection_update",
            "data": {
                "active_connections": len(self.active_connections),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    def disconnect(self, websocket: WebSocket):
        """接続を切断"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_info.pop(websocket, None)
            
            logger.info(f"WebSocket接続を終了: {len(self.active_connections)}件の接続")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """特定のクライアントにメッセージ送信"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"個別メッセージ送信エラー: {e}")
                self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """全クライアントにメッセージをブロードキャスト"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message, default=str)
        disconnected_clients = []
        
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message_str)
                else:
                    disconnected_clients.append(connection)
            except Exception as e:
                logger.warning(f"ブロードキャスト送信エラー: {e}")
                disconnected_clients.append(connection)
        
        # 切断されたクライアントをクリーンアップ
        for client in disconnected_clients:
            self.disconnect(client)
    
    async def broadcast_log(self, level: str, message: str, source: str = "system"):
        """ログメッセージをブロードキャスト"""
        log_message = {
            "type": "log",
            "data": {
                "level": level,
                "message": message,
                "source": source,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await self.broadcast(log_message)
    
    async def broadcast_job_update(self, job_id: str, status: str, stats: Dict[str, Any] = None):
        """ジョブ更新をブロードキャスト"""
        job_update = {
            "type": "job_update",
            "data": {
                "job_id": job_id,
                "status": status,
                "stats": stats or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await self.broadcast(job_update)
    
    async def broadcast_system_stats(self):
        """システム統計をブロードキャスト"""
        try:
            # 基本統計を取得
            user_stats = user_service.get_user_stats()
            job_stats = job_service.get_job_statistics(days=1)
            running_jobs = job_service.get_running_jobs()
            
            stats_message = {
                "type": "system_stats",
                "data": {
                    "users": {
                        "total": user_stats.get("total_users", 0),
                        "active": user_stats.get("active_users", 0)
                    },
                    "tweets": {
                        "total": user_stats.get("total_tweets", 0)
                    },
                    "jobs": {
                        "running": len(running_jobs),
                        "completed_today": job_stats.get("completed_jobs", 0),
                        "failed_today": job_stats.get("failed_jobs", 0)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            await self.broadcast(stats_message)
            
        except Exception as e:
            logger.error(f"システム統計ブロードキャストエラー: {e}")


# グローバル接続マネージャー
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続エンドポイント"""
    client_host = websocket.client.host if websocket.client else "unknown"
    
    try:
        await manager.connect(websocket, {"host": client_host})
        
        # 接続直後に現在の状況を送信
        await send_initial_data(websocket)
        
        # メッセージ受信ループ
        while True:
            try:
                # クライアントからのメッセージを受信
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # メッセージタイプに応じて処理
                await handle_client_message(websocket, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "無効なJSONフォーマットです"}
                }, websocket)
            except Exception as e:
                logger.error(f"WebSocketメッセージ処理エラー: {e}")
                await manager.send_personal_message({
                    "type": "error", 
                    "data": {"message": f"サーバーエラー: {str(e)}"}
                }, websocket)
                
    except Exception as e:
        logger.error(f"WebSocket接続エラー: {e}")
    finally:
        manager.disconnect(websocket)


async def send_initial_data(websocket: WebSocket):
    """接続時に初期データを送信"""
    try:
        # 実行中のジョブを送信
        running_jobs = job_service.get_running_jobs()
        for job in running_jobs:
            await manager.send_personal_message({
                "type": "job_status",
                "data": {
                    "job_id": job.job_id,
                    "status": job.status,
                    "target_users": job.target_usernames,
                    "stats": vars(job.stats) if job.stats else {}
                }
            }, websocket)
        
        # システム統計を送信
        await manager.broadcast_system_stats()
        
        # ウェルカムメッセージ
        await manager.send_personal_message({
            "type": "welcome",
            "data": {
                "message": "WebSocket接続が確立されました",
                "running_jobs": len(running_jobs),
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)
        
    except Exception as e:
        logger.error(f"初期データ送信エラー: {e}")


async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """クライアントからのメッセージを処理"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    try:
        if message_type == "ping":
            # Ping/Pong for connection health
            await manager.send_personal_message({
                "type": "pong",
                "data": {"timestamp": datetime.utcnow().isoformat()}
            }, websocket)
        
        elif message_type == "subscribe_logs":
            # ログ購読の開始
            manager.connection_info[websocket]["subscribe_logs"] = True
            await manager.send_personal_message({
                "type": "log_subscription",
                "data": {"subscribed": True}
            }, websocket)
        
        elif message_type == "unsubscribe_logs":
            # ログ購読の停止
            manager.connection_info[websocket]["subscribe_logs"] = False
            await manager.send_personal_message({
                "type": "log_subscription", 
                "data": {"subscribed": False}
            }, websocket)
        
        elif message_type == "request_stats":
            # 統計情報のリクエスト
            await manager.broadcast_system_stats()
        
        elif message_type == "request_job_status":
            # ジョブ状況のリクエスト
            job_id = data.get("job_id")
            if job_id:
                job = job_service.get_job(job_id)
                if job:
                    await manager.send_personal_message({
                        "type": "job_status",
                        "data": {
                            "job_id": job.job_id,
                            "status": job.status,
                            "stats": vars(job.stats) if job.stats else {},
                            "logs": job.logs[-10:] if job.logs else []  # 最新10件
                        }
                    }, websocket)
        
        else:
            # 未知のメッセージタイプ
            await manager.send_personal_message({
                "type": "error",
                "data": {"message": f"未知のメッセージタイプ: {message_type}"}
            }, websocket)
            
    except Exception as e:
        logger.error(f"クライアントメッセージ処理エラー: {e}")
        await manager.send_personal_message({
            "type": "error",
            "data": {"message": f"メッセージ処理エラー: {str(e)}"}
        }, websocket)


# バックグラウンドタスク: 定期的な統計更新
async def periodic_stats_broadcast():
    """定期的にシステム統計をブロードキャスト"""
    while True:
        try:
            if manager.active_connections:
                await manager.broadcast_system_stats()
            await asyncio.sleep(30)  # 30秒間隔
        except Exception as e:
            logger.error(f"定期統計ブロードキャストエラー: {e}")
            await asyncio.sleep(60)  # エラー時は1分待機


# 外部から呼び出し可能な関数
async def broadcast_log_message(level: str, message: str, source: str = "system"):
    """外部からログメッセージをブロードキャスト"""
    await manager.broadcast_log(level, message, source)


async def broadcast_job_update(job_id: str, status: str, stats: Dict[str, Any] = None):
    """外部からジョブ更新をブロードキャスト"""
    await manager.broadcast_job_update(job_id, status, stats)


async def broadcast_system_notification(message: str, notification_type: str = "info"):
    """外部からシステム通知をブロードキャスト"""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    })


# アプリケーション起動時にバックグラウンドタスクを開始
def start_background_tasks():
    """バックグラウンドタスクを開始"""
    asyncio.create_task(periodic_stats_broadcast())