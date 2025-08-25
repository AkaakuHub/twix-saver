#!/usr/bin/env python3
"""
Pydanticモデルファイル変更監視スクリプト
src/web/models.py の変更を監視し、変更時に自動的に型定義を再生成
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("watchdog ライブラリが見つかりません。インストール中...")
    subprocess.run([sys.executable, "-m", "pip", "install", "watchdog"], check=True)  # noqa: S603
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_FILE = PROJECT_ROOT / "src" / "web" / "models.py"
GENERATE_SCRIPT = PROJECT_ROOT / "scripts" / "generate-types.py"


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class ModelsChangeHandler(FileSystemEventHandler):
    """Pydanticモデルファイル変更ハンドラー"""

    def __init__(self):
        self.last_modified = 0
        self.debounce_seconds = 2  # 2秒以内の連続変更は無視

    def on_modified(self, event):
        """ファイル変更時の処理"""
        if event.is_directory:
            return

        # models.py の変更のみを監視
        if not event.src_path.endswith("models.py"):
            return

        # デバウンス処理（短時間での連続変更を無視）
        current_time = time.time()
        if current_time - self.last_modified < self.debounce_seconds:
            return

        self.last_modified = current_time

        log(f"Pydanticモデルファイルの変更を検知: {event.src_path}")
        self.regenerate_types()

    def regenerate_types(self):
        """型定義を再生成"""
        log("TypeScript型定義を自動再生成中...")

        try:
            # 型定義生成スクリプトを実行
            result = subprocess.run(  # noqa: S603
                [sys.executable, str(GENERATE_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                log("✅ 型定義の自動再生成が完了しました")
                if result.stdout:
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            log(f"  {line}")
            else:
                log("❌ 型定義の自動再生成に失敗しました")
                if result.stderr:
                    for line in result.stderr.split("\n"):
                        if line.strip():
                            log(f"ERROR: {line}")

        except Exception as e:
            log(f"❌ 型定義再生成でエラーが発生: {e}")


def main():
    """メイン処理"""
    log("=== Pydanticモデルファイル変更監視 開始 ===")

    if not MODELS_FILE.exists():
        log(f"❌ 監視対象ファイルが存在しません: {MODELS_FILE}")
        sys.exit(1)

    if not GENERATE_SCRIPT.exists():
        log(f"❌ 型生成スクリプトが存在しません: {GENERATE_SCRIPT}")
        sys.exit(1)

    log(f"監視対象: {MODELS_FILE}")
    log(f"生成スクリプト: {GENERATE_SCRIPT}")

    # ファイルシステム監視の設定
    event_handler = ModelsChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(MODELS_FILE.parent), recursive=False)

    try:
        observer.start()
        log("ファイル監視を開始しました (Ctrl+C で停止)")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        log("ファイル監視を停止中...")
        observer.stop()

    observer.join()
    log("=== Pydanticモデルファイル変更監視 終了 ===")


if __name__ == "__main__":
    main()
