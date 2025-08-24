"""
設定管理ルーター - DB連携のアプリケーション設定API
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.services.config_service import config_service
from src.services.account_service import twitter_account_service
from src.utils.logger import setup_logger

logger = setup_logger("settings_router")
router = APIRouter()

# Pydanticモデル定義
class ProxyConfig(BaseModel):
    enabled: bool = False
    server: str = ""
    username: str = ""
    password: str = ""

class ScrapingConfig(BaseModel):
    intervalMinutes: int = 15
    randomDelayMaxSeconds: int = 120
    maxTweetsPerSession: int = 100
    headless: bool = True

class GeneralConfig(BaseModel):
    logLevel: str = "INFO"
    corsOrigins: str = "http://localhost:3000,http://localhost:5173"

class SystemConfigItem(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    category: str = "general"
    updated_at: Optional[str] = None

class SettingsRequest(BaseModel):
    proxy: ProxyConfig
    scraping: ScrapingConfig
    general: GeneralConfig

class SettingsResponse(BaseModel):
    proxy: ProxyConfig
    scraping: ScrapingConfig
    general: GeneralConfig
    twitter_accounts_available: int


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """現在の設定を取得（DB連携版）"""
    try:
        # プロキシ設定
        proxy_config = ProxyConfig(
            enabled=config_service.get_config("proxy_enabled", False),
            server=config_service.get_config("proxy_server", ""),
            username=config_service.get_config("proxy_username", ""),
            password=""  # セキュリティのためパスワードは空で返す
        )
        
        # スクレイピング設定
        scraping_config = ScrapingConfig(
            intervalMinutes=config_service.get_config("scraping_interval_minutes", 15),
            randomDelayMaxSeconds=config_service.get_config("random_delay_max_seconds", 120),
            maxTweetsPerSession=config_service.get_config("max_tweets_per_session", 100),
            headless=config_service.get_config("headless_mode", True)
        )
        
        # 一般設定
        general_config = GeneralConfig(
            logLevel=config_service.get_config("log_level", "INFO"),
            corsOrigins=config_service.get_config("cors_origins", "http://localhost:3000,http://localhost:5173")
        )
        
        # 使用可能なTwitterアカウント数
        available_accounts = len(twitter_account_service.get_available_accounts())
        
        response = SettingsResponse(
            proxy=proxy_config,
            scraping=scraping_config,
            general=general_config,
            twitter_accounts_available=available_accounts
        )
        
        logger.info(f"設定を取得しました: {response}")
        logger.debug(f"プロキシ設定: {proxy_config}")
        logger.debug(f"スクレイピング設定: {scraping_config}")
        logger.debug(f"一般設定: {general_config}")
        return response
        
    except Exception as e:
        logger.error(f"設定取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定取得に失敗しました: {str(e)}")


@router.put("/settings")
async def update_settings(settings_request: SettingsRequest):
    """設定を更新（DB連携版）"""
    try:
        # 設定更新用の辞書を作成
        config_updates = {}
        
        # プロキシ設定
        config_updates["proxy_enabled"] = settings_request.proxy.enabled
        config_updates["proxy_server"] = settings_request.proxy.server
        config_updates["proxy_username"] = settings_request.proxy.username
        if settings_request.proxy.password:  # パスワードが空でない場合のみ更新
            config_updates["proxy_password"] = settings_request.proxy.password
        
        # スクレイピング設定
        config_updates["scraping_interval_minutes"] = settings_request.scraping.intervalMinutes
        config_updates["random_delay_max_seconds"] = settings_request.scraping.randomDelayMaxSeconds
        config_updates["max_tweets_per_session"] = settings_request.scraping.maxTweetsPerSession
        config_updates["headless_mode"] = settings_request.scraping.headless
        
        # 一般設定
        config_updates["log_level"] = settings_request.general.logLevel
        config_updates["cors_origins"] = settings_request.general.corsOrigins
        
        # データベースに一括更新
        success = config_service.update_configs(config_updates)
        if not success:
            raise HTTPException(status_code=500, detail="設定の一部更新に失敗しました")
        
        logger.info("設定を更新しました（DB連携）")
        return {"success": True, "message": "設定を保存しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設定更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定更新に失敗しました: {str(e)}")


@router.get("/configs", response_model=List[SystemConfigItem])
async def get_all_configs():
    """全システム設定を取得"""
    try:
        configs = config_service.get_all_config_objects()
        config_items = []
        
        for config in configs:
            config_dict = config.to_dict()
            config_items.append(SystemConfigItem(**config_dict))
        
        return config_items
        
    except Exception as e:
        logger.error(f"設定一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定一覧取得に失敗しました: {str(e)}")


@router.get("/configs/{category}")
async def get_configs_by_category(category: str):
    """カテゴリ別設定を取得"""
    try:
        configs = config_service.get_configs_by_category(category)
        return configs
        
    except Exception as e:
        logger.error(f"カテゴリ別設定取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"カテゴリ別設定取得に失敗しました: {str(e)}")


@router.put("/configs/{key}")
async def update_config(key: str, config_data: dict):
    """個別設定を更新"""
    try:
        if "value" not in config_data:
            raise HTTPException(status_code=400, detail="value は必須です")
        
        success = config_service.set_config(
            key=key,
            value=config_data["value"],
            description=config_data.get("description"),
            category=config_data.get("category", "general")
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="設定更新に失敗しました")
        
        return {"success": True, "message": f"設定 {key} を更新しました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設定更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定更新に失敗しました: {str(e)}")


@router.post("/settings/migrate-from-env")
async def migrate_from_env():
    """環境変数からDB設定に移行"""
    try:
        # 環境変数から設定を読み取りDBに移行
        env_mapping = {
            "SCRAPING_INTERVAL_MINUTES": ("scraping_interval_minutes", int),
            "RANDOM_DELAY_MAX_SECONDS": ("random_delay_max_seconds", int),
            "MAX_TWEETS_PER_SESSION": ("max_tweets_per_session", int),
            "HEADLESS": ("headless_mode", lambda x: x.lower() == "true"),
            "LOG_LEVEL": ("log_level", str),
            "CORS_ORIGINS": ("cors_origins", str),
            "PROXY_SERVER": ("proxy_server", str),
            "PROXY_USERNAME": ("proxy_username", str),
            "PROXY_PASSWORD": ("proxy_password", str),
        }
        
        migrated_count = 0
        for env_key, (config_key, converter) in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value:
                try:
                    converted_value = converter(env_value)
                    config_service.set_config(config_key, converted_value)
                    migrated_count += 1
                except Exception as e:
                    logger.warning(f"環境変数 {env_key} の変換に失敗: {e}")
        
        # プロキシが設定されている場合は有効化
        if os.getenv("PROXY_SERVER"):
            config_service.set_config("proxy_enabled", True)
            migrated_count += 1
        
        logger.info(f"環境変数から {migrated_count} 件の設定を移行しました")
        return {"success": True, "message": f"{migrated_count} 件の設定をDBに移行しました"}
        
    except Exception as e:
        logger.error(f"設定移行エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定移行に失敗しました: {str(e)}")


@router.get("/settings/validate")
async def validate_settings():
    """設定の妥当性をチェック"""
    try:
        # Twitterアカウントチェック
        available_accounts = twitter_account_service.get_available_accounts()
        twitter_valid = len(available_accounts) > 0
        
        # プロキシ設定チェック
        proxy_enabled = config_service.get_config("proxy_enabled", False)
        proxy_server = config_service.get_config("proxy_server", "")
        proxy_valid = not proxy_enabled or bool(proxy_server)
        
        # スクレイピング設定チェック
        interval = config_service.get_config("scraping_interval_minutes", 15)
        max_tweets = config_service.get_config("max_tweets_per_session", 100)
        scraping_valid = interval > 0 and max_tweets > 0
        
        validation_results = {
            "twitter_accounts": {
                "valid": twitter_valid,
                "message": f"{len(available_accounts)}個のTwitterアカウントが利用可能です" if twitter_valid else "利用可能なTwitterアカウントがありません"
            },
            "proxy": {
                "valid": proxy_valid,
                "message": "プロキシ設定は有効です" if proxy_valid else "プロキシが有効ですがサーバーが設定されていません"
            },
            "scraping": {
                "valid": scraping_valid,
                "message": "スクレイピング設定が有効です" if scraping_valid else "スクレイピング設定に問題があります"
            }
        }
        
        overall_valid = all(result["valid"] for result in validation_results.values())
        
        return {
            "valid": overall_valid,
            "results": validation_results,
            "message": "設定は有効です" if overall_valid else "一部の設定に問題があります"
        }
        
    except Exception as e:
        logger.error(f"設定検証エラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定検証に失敗しました: {str(e)}")


@router.post("/settings/reset")
async def reset_settings():
    """設定をデフォルトにリセット"""
    try:
        success = config_service.reset_to_defaults()
        if not success:
            raise HTTPException(status_code=500, detail="設定リセットに失敗しました")
        
        return {"success": True, "message": "設定をデフォルトにリセットしました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設定リセットエラー: {e}")
        raise HTTPException(status_code=500, detail=f"設定リセットに失敗しました: {str(e)}")