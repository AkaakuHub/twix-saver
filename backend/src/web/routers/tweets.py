"""
ツイートデータ表示・検索API
MongoDB からのツイートデータ取得と検索機能を提供
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from pymongo.errors import PyMongoError

from src.web.models import TweetSearchFilter, TweetResponse, PaginatedResponse
from src.utils.data_manager import mongodb_manager
from src.utils.logger import setup_logger

router = APIRouter(prefix="/tweets", tags=["tweets"])
logger = setup_logger("api.tweets")  # reload trigger


@router.get("/", response_model=List[TweetResponse])
async def get_tweets(
    username: Optional[str] = Query(None, description="特定ユーザーのツイートのみ"),
    keyword: Optional[str] = Query(None, description="検索キーワード"),
    start_date: Optional[datetime] = Query(None, description="開始日時"),
    end_date: Optional[datetime] = Query(None, description="終了日時"),
    has_articles: Optional[bool] = Query(None, description="記事リンクありのみ"),
    has_media: Optional[bool] = Query(None, description="メディアありのみ"),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット")
):
    """ツイート一覧を取得（検索・フィルタ機能付き）"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # クエリ構築
        query = {}
        
        # ユーザー名フィルタ
        if username:
            query["$or"] = [
                {"legacy.user.screen_name": {"$regex": username, "$options": "i"}},
                {"core.user_results.result.legacy.screen_name": {"$regex": username, "$options": "i"}}
            ]
        
        # キーワード検索
        if keyword:
            query["$or"] = query.get("$or", [])
            if not query["$or"]:
                query["$or"] = []
            query["$or"].extend([
                {"legacy.full_text": {"$regex": keyword, "$options": "i"}},
                {"note_tweet.note_tweet_results.result.text": {"$regex": keyword, "$options": "i"}}
            ])
        
        # 日時範囲フィルタ
        if start_date or end_date:
            scraped_filter = {}
            if start_date:
                scraped_filter["$gte"] = start_date
            if end_date:
                scraped_filter["$lte"] = end_date
            query["scraped_at"] = scraped_filter
        
        # 記事リンクフィルタ
        if has_articles is not None:
            if has_articles:
                query["extracted_articles"] = {"$exists": True, "$ne": []}
            else:
                query["$or"] = [
                    {"extracted_articles": {"$exists": False}},
                    {"extracted_articles": []}
                ]
        
        # メディアフィルタ
        if has_media is not None:
            if has_media:
                query["$or"] = query.get("$or", [])
                if not query["$or"]:
                    query["$or"] = []
                query["$or"].extend([
                    {"legacy.entities.media": {"$exists": True, "$ne": []}},
                    {"downloaded_media": {"$exists": True, "$ne": []}}
                ])
            else:
                query["$and"] = query.get("$and", [])
                query["$and"].extend([
                    {"$or": [
                        {"legacy.entities.media": {"$exists": False}},
                        {"legacy.entities.media": []}
                    ]},
                    {"$or": [
                        {"downloaded_media": {"$exists": False}},
                        {"downloaded_media": []}
                    ]}
                ])
        
        # データ取得
        cursor = (mongodb_manager.tweets_collection
                 .find(query)
                 .sort("scraped_at", -1)
                 .skip(offset)
                 .limit(limit))
        
        tweets = []
        for doc in cursor:
            try:
                tweet = _convert_tweet_document(doc)
                tweets.append(TweetResponse(**tweet))
            except Exception as e:
                logger.warning(f"ツイート変換エラー: {e}")
                continue
        
        logger.info(f"ツイートを取得: {len(tweets)}件 "
                   f"(ユーザー: {username}, キーワード: {keyword})")
        
        return tweets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ツイート取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ツイート取得に失敗しました: {str(e)}")


@router.get("/search", response_model=List[TweetResponse])
async def search_tweets(q: str = Query(..., min_length=1, description="検索クエリ")):
    """ツイート全文検索"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # 全文検索クエリ
        search_query = {
            "$or": [
                {"legacy.full_text": {"$regex": q, "$options": "i"}},
                {"note_tweet.note_tweet_results.result.text": {"$regex": q, "$options": "i"}},
                {"legacy.user.name": {"$regex": q, "$options": "i"}},
                {"legacy.user.screen_name": {"$regex": q, "$options": "i"}}
            ]
        }
        
        cursor = (mongodb_manager.tweets_collection
                 .find(search_query)
                 .sort("scraped_at", -1)
                 .limit(50))
        
        tweets = []
        for doc in cursor:
            try:
                tweet = _convert_tweet_document(doc)
                tweets.append(TweetResponse(**tweet))
            except Exception as e:
                logger.warning(f"ツイート変換エラー: {e}")
                continue
        
        logger.info(f"ツイート検索: '{q}' -> {len(tweets)}件")
        return tweets
        
    except Exception as e:
        logger.error(f"ツイート検索エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ツイート検索に失敗しました: {str(e)}")




@router.get("/user/{username}/latest", response_model=List[TweetResponse])
async def get_user_latest_tweets(
    username: str,
    limit: int = Query(10, ge=1, le=50, description="取得件数")
):
    """特定ユーザーの最新ツイートを取得"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # ユーザー名の正規化
        username = username.lstrip('@').lower()
        
        query = {
            "$or": [
                {"legacy.user.screen_name": {"$regex": f"^{username}$", "$options": "i"}},
                {"core.user_results.result.legacy.screen_name": {"$regex": f"^{username}$", "$options": "i"}}
            ]
        }
        
        cursor = (mongodb_manager.tweets_collection
                 .find(query)
                 .sort("scraped_at", -1)
                 .limit(limit))
        
        tweets = []
        for doc in cursor:
            try:
                tweet = _convert_tweet_document(doc)
                tweets.append(TweetResponse(**tweet))
            except Exception as e:
                logger.warning(f"ツイート変換エラー: {e}")
                continue
        
        logger.info(f"ユーザー最新ツイート: @{username} -> {len(tweets)}件")
        return tweets
        
    except Exception as e:
        logger.error(f"ユーザー最新ツイート取得エラー ({username}): {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー最新ツイート取得に失敗しました: {str(e)}")


@router.get("/stats")
async def get_tweet_stats():
    """ツイート統計を取得"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # 基本統計
        total_tweets = mongodb_manager.tweets_collection.count_documents({})
        
        # 今日のツイート数
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tweets_today = mongodb_manager.tweets_collection.count_documents({
            "scraped_at": {"$gte": today}
        })
        
        # 今週のツイート数
        week_ago = today - timedelta(days=7)
        tweets_this_week = mongodb_manager.tweets_collection.count_documents({
            "scraped_at": {"$gte": week_ago}
        })
        
        # 記事付きツイート数
        tweets_with_articles = mongodb_manager.tweets_collection.count_documents({
            "extracted_articles": {"$exists": True, "$ne": []}
        })
        
        # メディア付きツイート数
        tweets_with_media = mongodb_manager.tweets_collection.count_documents({
            "$or": [
                {"legacy.entities.media": {"$exists": True, "$ne": []}},
                {"downloaded_media": {"$exists": True, "$ne": []}}
            ]
        })
        
        # 最新ツイート
        latest_tweet = mongodb_manager.tweets_collection.find_one(
            {},
            sort=[("scraped_at", -1)]
        )
        
        stats = {
            "total_tweets": total_tweets,
            "tweets_today": tweets_today,
            "tweets_this_week": tweets_this_week,
            "tweets_with_articles": tweets_with_articles,
            "tweets_with_media": tweets_with_media,
            "latest_scraped_at": latest_tweet.get("scraped_at") if latest_tweet else None
        }
        
        logger.info("ツイート統計を取得しました")
        return stats
        
    except Exception as e:
        logger.error(f"ツイート統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ツイート統計取得に失敗しました: {str(e)}")


@router.get("/time-series")
async def get_tweet_time_series(days: int = Query(7, ge=1, le=30)):
    """ツイート時系列データを取得"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # 指定日数前からのデータを集計
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 日別のツイート数を集計
        pipeline = [
            {
                "$match": {
                    "scraped_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$scraped_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        time_series_data = list(mongodb_manager.tweets_collection.aggregate(pipeline))
        
        # 結果を整形
        data = []
        for item in time_series_data:
            data.append({
                "date": item["_id"],
                "count": item["count"]
            })
        
        logger.info(f"ツイート時系列データを取得: {days}日間, {len(data)}日分")
        return {
            "days": days,
            "data": data,
            "total_tweets": sum(item["count"] for item in data)
        }
        
    except Exception as e:
        logger.error(f"ツイート時系列データ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ツイート時系列データ取得に失敗しました: {str(e)}")


@router.get("/stats/summary")
async def get_tweet_statistics():
    """ツイート統計情報を取得（詳細版）"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        # 基本統計
        total_tweets = mongodb_manager.tweets_collection.count_documents({})
        
        # 今日のツイート数
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tweets_today = mongodb_manager.tweets_collection.count_documents({
            "scraped_at": {"$gte": today}
        })
        
        # 今週のツイート数
        week_ago = today - timedelta(days=7)
        tweets_this_week = mongodb_manager.tweets_collection.count_documents({
            "scraped_at": {"$gte": week_ago}
        })
        
        # 記事付きツイート数
        tweets_with_articles = mongodb_manager.tweets_collection.count_documents({
            "extracted_articles": {"$exists": True, "$ne": []}
        })
        
        # メディア付きツイート数
        tweets_with_media = mongodb_manager.tweets_collection.count_documents({
            "$or": [
                {"legacy.entities.media": {"$exists": True, "$ne": []}},
                {"downloaded_media": {"$exists": True, "$ne": []}}
            ]
        })
        
        # 最新ツイート
        latest_tweet = mongodb_manager.tweets_collection.find_one(
            {},
            sort=[("scraped_at", -1)]
        )
        
        # ユーザー別ツイート数（上位10）
        user_stats = list(mongodb_manager.tweets_collection.aggregate([
            {
                "$group": {
                    "_id": {
                        "$ifNull": [
                            "$legacy.user.screen_name",
                            "$core.user_results.result.legacy.screen_name"
                        ]
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        stats = {
            "total_tweets": total_tweets,
            "tweets_today": tweets_today,
            "tweets_this_week": tweets_this_week,
            "tweets_with_articles": tweets_with_articles,
            "tweets_with_media": tweets_with_media,
            "latest_scraped_at": latest_tweet.get("scraped_at") if latest_tweet else None,
            "top_users": [
                {"username": stat["_id"], "tweet_count": stat["count"]}
                for stat in user_stats if stat["_id"]
            ]
        }
        
        logger.info("ツイート統計を取得しました")
        return stats
        
    except Exception as e:
        logger.error(f"ツイート統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ツイート統計取得に失敗しました: {str(e)}")


@router.get("/{tweet_id}", response_model=TweetResponse)
async def get_tweet(tweet_id: str):
    """特定ツイートの詳細を取得"""
    try:
        if not mongodb_manager.is_connected:
            raise HTTPException(status_code=500, detail="データベース接続エラー")
        
        doc = mongodb_manager.tweets_collection.find_one({
            "$or": [
                {"id_str": tweet_id},
                {"rest_id": tweet_id}
            ]
        })
        
        if not doc:
            raise HTTPException(status_code=404, detail=f"ツイートが見つかりません: {tweet_id}")
        
        tweet = _convert_tweet_document(doc)
        return TweetResponse(**tweet)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ツイート詳細取得エラー ({tweet_id}): {e}")
        raise HTTPException(status_code=500, detail=f"ツイート詳細取得に失敗しました: {str(e)}")


def _convert_tweet_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """MongoDBドキュメントをTweetResponseモデルに変換"""
    
    # 基本情報の抽出
    tweet_id = doc.get("id_str") or doc.get("rest_id") or str(doc.get("_id", ""))
    
    # ツイート本文の抽出
    content = ""
    if "legacy" in doc and "full_text" in doc["legacy"]:
        content = doc["legacy"]["full_text"]
    elif "note_tweet" in doc and "note_tweet_results" in doc["note_tweet"]:
        note = doc["note_tweet"]["note_tweet_results"].get("result", {})
        content = note.get("text", "")
    
    # ユーザー情報の抽出
    author_username = ""
    author_display_name = ""
    
    # 新構造のチェックを優先（core.user_resultsが存在する場合）
    if "core" in doc and "user_results" in doc["core"]:
        user_result = doc["core"]["user_results"].get("result", {})
        if "core" in user_result:
            # 新構造のcoreフィールド（最新）- これが最優先
            core_user = user_result["core"]
            author_username = core_user.get("screen_name", "")
            author_display_name = core_user.get("name", "")
        elif "legacy" in user_result:
            # 新構造のlegacyフィールド
            legacy_user = user_result["legacy"]
            author_username = legacy_user.get("screen_name", "")
            author_display_name = legacy_user.get("name", "")
    # 旧構造のチェック（legacy.userが存在する場合）
    elif "legacy" in doc and "user" in doc["legacy"]:
        user = doc["legacy"]["user"]
        author_username = user.get("screen_name", "")
        author_display_name = user.get("name", "")
    
    # デバッグログ
    if not author_username:
        logger.debug(f"ユーザー名取得失敗 - Tweet ID: {tweet_id}, Data keys: {list(doc.keys())}")
    
    # エンゲージメント情報
    engagement = {}
    if "legacy" in doc:
        legacy = doc["legacy"]
        engagement = {
            "retweet_count": legacy.get("retweet_count"),
            "like_count": legacy.get("favorite_count"),
            "reply_count": legacy.get("reply_count")
        }
    
    # 作成日時の抽出・変換
    created_at = None
    if "legacy" in doc and "created_at" in doc["legacy"]:
        # Twitter API の日時形式をパース
        try:
            from datetime import datetime
            created_at_str = doc["legacy"]["created_at"]
            # "Wed Oct 10 20:19:24 +0000 2018" 形式
            created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        except (ValueError, TypeError):
            pass
    
    # スクレイピング日時
    scraped_at = doc.get("scraped_at")
    if isinstance(scraped_at, str):
        try:
            scraped_at = datetime.fromisoformat(scraped_at)
        except ValueError:
            pass
    
    # ハッシュタグとメンションの抽出
    hashtags = []
    mentions = []
    
    if "legacy" in doc and "entities" in doc["legacy"]:
        entities = doc["legacy"]["entities"]
        
        if "hashtags" in entities:
            hashtags = [tag.get("text", "") for tag in entities["hashtags"]]
        
        if "user_mentions" in entities:
            mentions = [mention.get("screen_name", "") for mention in entities["user_mentions"]]
    
    return {
        "id_str": tweet_id,
        "content": content,
        "author_username": author_username,
        "author_display_name": author_display_name,
        "created_at": created_at,
        "scraped_at": scraped_at,
        "scraper_account": doc.get("scraper_account"),
        "retweet_count": engagement.get("retweet_count"),
        "like_count": engagement.get("like_count"),
        "reply_count": engagement.get("reply_count"),
        "extracted_articles": doc.get("extracted_articles"),
        "downloaded_media": doc.get("downloaded_media"),
        "hashtags": hashtags if hashtags else None,
        "mentions": mentions if mentions else None
    }