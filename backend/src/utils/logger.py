"""
ログ設定とユーティリティ
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.settings import settings


class ColoredFormatter(logging.Formatter):
    """カラー出力対応のログフォーマッター"""

    COLORS = {
        "DEBUG": "\033[36m",  # シアン
        "INFO": "\033[32m",  # 緑
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 赤
        "CRITICAL": "\033[35m",  # マゼンタ
        "RESET": "\033[0m",  # リセット
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset_color = self.COLORS["RESET"]

        # レベル名をカラー化
        record.levelname = f"{log_color}{record.levelname}{reset_color}"

        return super().format(record)


def setup_logger(name: str = "twix_scraper", level: Optional[str] = None, log_to_file: bool = True) -> logging.Logger:
    """
    ロガーの設定を行う

    Args:
        name: ロガー名
        level: ログレベル
        log_to_file: ファイル出力を行うかどうか

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)

    # 既に設定済みの場合はそのまま返す
    if logger.handlers:
        return logger

    # ログレベル設定
    if level is None:
        level = settings.log_level

    logger.setLevel(getattr(logging, level.upper()))

    # コンソール出力ハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # カラーフォーマッター（ターミナル検出）
    if sys.stdout.isatty():
        console_formatter = ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # ファイル出力ハンドラー
    if log_to_file:
        # ログディレクトリ作成
        log_dir = Path(settings.logs_dir)
        log_dir.mkdir(exist_ok=True)

        # 日付ベースのログファイル名
        today = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"scraper_{today}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # ファイルは常にDEBUGレベル

        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def log_performance(func):
    """関数の実行時間を測定するデコレータ"""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("twix_scraper.performance")
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} 実行時間: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 実行時間: {execution_time:.2f}秒 (エラー: {e})")
            raise

    return wrapper


def log_scraping_stats(tweets_collected: int, errors: int, session_duration: float):
    """スクレイピング統計をログ出力"""
    logger = logging.getLogger("twix_scraper.stats")

    logger.info(
        f"スクレイピング完了 - 取得ツイート数: {tweets_collected}, "
        f"エラー数: {errors}, 実行時間: {session_duration:.2f}秒"
    )

    if tweets_collected > 0:
        avg_time_per_tweet = session_duration / tweets_collected
        logger.info(f"平均処理時間: {avg_time_per_tweet:.2f}秒/ツイート")


# デフォルトロガーの初期化
default_logger = setup_logger()
