#!/usr/bin/env python3
"""
Pydantic↔TypeScript型同期チェックスクリプト
手動で作成された型定義と自動生成された型定義の差分をチェック
CI/CDパイプラインで使用
"""

import difflib
import hashlib
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MANUAL_TYPES_FILE = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "api.ts"
GENERATED_TYPES_FILE = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "api.generated.ts"


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_file_hash(filepath: Path) -> str:
    """ファイルのハッシュ値を取得"""
    if not filepath.exists():
        return ""

    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()  # noqa: S324


def extract_type_definitions(content: str) -> list:
    """型定義部分を抽出（コメントや装飾を除く）"""
    lines = content.split("\n")
    type_lines = []

    for line in lines:
        stripped = line.strip()
        # 型定義に関連する行のみを抽出
        if any(
            keyword in stripped
            for keyword in [
                "export interface",
                "export type",
                "export enum",
                "export const",
                "export class",
            ]
        ):
            type_lines.append(stripped)

    return type_lines


def compare_types():
    """型定義を比較"""
    if not MANUAL_TYPES_FILE.exists():
        log(f"❌ 手動型定義ファイルが存在しません: {MANUAL_TYPES_FILE}")
        return False

    if not GENERATED_TYPES_FILE.exists():
        log(f"❌ 生成型定義ファイルが存在しません: {GENERATED_TYPES_FILE}")
        log("まず scripts/generate-types.py を実行してください")
        return False

    # ファイル内容を読み込み
    with open(MANUAL_TYPES_FILE, encoding="utf-8") as f:
        manual_content = f.read()

    with open(GENERATED_TYPES_FILE, encoding="utf-8") as f:
        generated_content = f.read()

    # 型定義部分のみを抽出して比較
    manual_types = extract_type_definitions(manual_content)
    generated_types = extract_type_definitions(generated_content)

    log(f"手動型定義: {len(manual_types)} 個の定義")
    log(f"生成型定義: {len(generated_types)} 個の定義")

    # 差分をチェック
    if manual_types == generated_types:
        log("✅ 型定義は同期されています")
        return True

    log("⚠️ 型定義に差分が検出されました:")

    # 詳細な差分を表示
    diff = list(
        difflib.unified_diff(
            manual_types,
            generated_types,
            fromfile="手動型定義",
            tofile="生成型定義",
            lineterm="",
        )
    )

    if diff:
        log("差分詳細:")
        for line in diff[:20]:  # 最初の20行のみ表示
            log(f"  {line}")

        if len(diff) > 20:
            log(f"  ... (残り {len(diff) - 20} 行の差分)")

    return False


def check_models_modification():
    """Pydanticモデルファイルの最終更新時刻をチェック"""
    models_file = PROJECT_ROOT / "src" / "web" / "models.py"

    if not models_file.exists():
        log(f"❌ Pydanticモデルファイルが存在しません: {models_file}")
        return False

    models_mtime = models_file.stat().st_mtime

    if GENERATED_TYPES_FILE.exists():
        generated_mtime = GENERATED_TYPES_FILE.stat().st_mtime

        if models_mtime > generated_mtime:
            log("⚠️ Pydanticモデルが型定義よりも新しく更新されています")
            log("scripts/generate-types.py を実行して型定義を再生成してください")
            return False

    log("✅ ファイル更新日時チェックOK")
    return True


def main():
    """メイン処理"""
    log("=== 型同期チェック開始 ===")

    success = True

    # 1. ファイルの更新日時チェック
    if not check_models_modification():
        success = False

    # 2. 型定義の比較
    if not compare_types():
        success = False

    if success:
        log("✅ 全ての型同期チェックに合格しました")
        sys.exit(0)
    else:
        log("❌ 型同期チェックに失敗しました")
        log("推奨アクション:")
        log("1. scripts/generate-types.py を実行して最新の型定義を生成")
        log("2. 生成された型定義を確認して手動定義と統合")
        log("3. 再度このスクリプトを実行")
        sys.exit(1)


if __name__ == "__main__":
    main()
