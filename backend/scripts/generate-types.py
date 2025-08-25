#!/usr/bin/env python3
"""
Pydantic→TypeScript型定義自動生成スクリプト
src/web/models.py のPydanticモデルからTypeScript型定義を生成
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_MODULE = "src.web.models"
OUTPUT_FILE = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "api.generated.ts"
BACKUP_DIR = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "backups"


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def ensure_directories():
    """必要なディレクトリを作成"""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_existing_types():
    """既存の型定義をバックアップ"""
    if OUTPUT_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"api.generated.{timestamp}.ts.backup"
        OUTPUT_FILE.rename(backup_file)
        log(f"既存のファイルをバックアップ: {backup_file}")


def install_dependencies():
    """必要な依存関係をインストール"""
    log("pydantic-to-typescript の依存関係を確認中...")

    try:
        import pydantic_to_typescript  # noqa: F401

        log("pydantic-to-typescript は既にインストール済み")
    except ImportError:
        log("pydantic-to-typescript をインストール中...")
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pip", "install", "pydantic-to-typescript>=2.0.0"],
            check=True,
        )
        log("pydantic-to-typescript のインストール完了")


def generate_typescript_types():
    """TypeScript型定義を生成"""
    log("Pydanticモデルから TypeScript 型定義を生成中...")
    log(f"入力モジュール: {MODELS_MODULE}")
    log(f"出力ファイル: {OUTPUT_FILE}")

    # sys.pathにプロジェクトルートを追加
    sys.path.insert(0, str(PROJECT_ROOT))

    try:
        # pydantic-to-typescript を使用して型定義生成
        # src.web.models をインポート
        import importlib.util

        from pydantic_to_typescript import generate_typescript_defs

        models_path = PROJECT_ROOT / "src" / "web" / "models.py"
        spec = importlib.util.spec_from_file_location("models", models_path)
        models_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(models_module)

        # 全てのPydanticモデルを取得
        from pydantic import BaseModel

        pydantic_models = []

        for name in dir(models_module):
            obj = getattr(models_module, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel:
                pydantic_models.append(obj)

        log(f"発見されたPydanticモデル: {[model.__name__ for model in pydantic_models]}")

        # TypeScript型定義を生成
        generate_typescript_defs(models=pydantic_models, output=str(OUTPUT_FILE))

        log(f"TypeScript型定義を生成完了: {OUTPUT_FILE}")
        return True

    except Exception as e:
        log(f"型定義生成でエラーが発生: {e}")
        return False


def add_custom_types():
    """カスタム型定義と拡張を追加"""
    if not OUTPUT_FILE.exists():
        log("出力ファイルが存在しないため、カスタム型を追加できません")
        return

    # 既存の生成された内容を読み取り
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        generated_content = f.read()

    # カスタム型定義とユーティリティを追加
    custom_additions = """
// ===== カスタム型定義と拡張 =====

export type ApiResponse<T = any> = SuccessResponse<T> | ErrorResponse;

// 優先度表示用ラベルとカラー
export const UserPriorityLabels = {
  1: '低',
  2: '標準',
  3: '高',
  4: '緊急',
} as const;

export const UserPriorityColors = {
  1: 'text-gray-500',
  2: 'text-blue-500',
  3: 'text-yellow-500',
  4: 'text-red-500',
} as const;

// ジョブステータス表示用ラベルとカラー
export const JobStatusLabels = {
  'pending': '待機中',
  'running': '実行中',
  'completed': '完了',
  'failed': '失敗',
  'cancelled': 'キャンセル',
} as const;

export const JobStatusColors = {
  'pending': 'text-yellow-500 bg-yellow-50',
  'running': 'text-blue-500 bg-blue-50',
  'completed': 'text-green-500 bg-green-50',
  'failed': 'text-red-500 bg-red-50',
  'cancelled': 'text-gray-500 bg-gray-50',
} as const;

// ===== APIエラークラス =====

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ===== ユーティリティ型 =====

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

"""

    # ファイルヘッダーを追加
    header = f"""/**
 * 自動生成されたAPI型定義
 *
 * このファイルは scripts/generate-types.py によって自動生成されます。
 * 手動で編集しないでください。変更は src/web/models.py で行ってください。
 *
 * 生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
 */

"""

    # 最終的なコンテンツを構築
    final_content = header + generated_content + custom_additions

    # ファイルに書き込み
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_content)

    log("カスタム型定義と拡張を追加完了")


def validate_generated_types():
    """生成された型定義をバリデーション"""
    if not OUTPUT_FILE.exists():
        log("❌ 型定義ファイルが生成されていません")
        return False

    # ファイルサイズチェック
    file_size = OUTPUT_FILE.stat().st_size
    if file_size < 1000:  # 1KB未満の場合は問題の可能性
        log(f"⚠️ 生成された型定義ファイルが小さすぎます ({file_size} bytes)")
        return False

    # TypeScriptファイルとして最低限の文法チェック
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        content = f.read()

    # 基本的な文法要素の存在チェック
    if "export" not in content:
        log("❌ export文が見つかりません")
        return False

    if "interface" not in content and "type" not in content:
        log("❌ interface または type定義が見つかりません")
        return False

    log(f"✅ 型定義ファイルの生成が成功しました ({file_size} bytes)")
    return True


def main():
    """メイン処理"""
    log("=== Pydantic→TypeScript 型定義自動生成 開始 ===")

    try:
        # 1. ディレクトリの確保
        ensure_directories()

        # 2. 依存関係のインストール
        install_dependencies()

        # 3. 既存ファイルのバックアップ
        backup_existing_types()

        # 4. TypeScript型定義の生成
        if not generate_typescript_types():
            log("❌ 型定義生成に失敗しました")
            sys.exit(1)

        # 5. カスタム型定義の追加
        add_custom_types()

        # 6. 生成結果のバリデーション
        if not validate_generated_types():
            log("❌ 生成された型定義の検証に失敗しました")
            sys.exit(1)

        log("✅ 型定義生成が完了しました")
        log(f"生成先: {OUTPUT_FILE}")

    except Exception as e:
        log(f"❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    log("=== Pydantic→TypeScript 型定義自動生成 完了 ===")


if __name__ == "__main__":
    main()
