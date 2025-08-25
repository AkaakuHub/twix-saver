#!/usr/bin/env python3
"""
Pydantic → TypeScript 簡易型生成テスト
pydantic-to-typescript を使わずに、基本的な型変換を実装
"""

import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import get_args, get_origin

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def python_to_typescript_type(py_type) -> str:
    """Python型をTypeScript型に変換"""
    if py_type is str:
        return "string"
    elif py_type is int:
        return "number"
    elif py_type is float:
        return "number"
    elif py_type is bool:
        return "boolean"
    elif py_type is type(None):
        return "null"
    elif py_type is datetime:
        return "string"  # ISO string として扱う
    elif hasattr(py_type, "__name__") and py_type.__name__ == "Any":
        return "unknown"

    # Generic types
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is list:
        if args:
            inner_type = python_to_typescript_type(args[0])
            return f"{inner_type}[]"
        return "unknown[]"

    if origin is dict:
        if len(args) == 2:
            key_type = python_to_typescript_type(args[0])
            value_type = python_to_typescript_type(args[1])
            return f"Record<{key_type}, {value_type}>"
        return "Record<string, unknown>"

    if origin is Union:
        # Optional型の処理
        if len(args) == 2 and type(None) in args:
            non_null_type = args[0] if args[1] is type(None) else args[1]
            return f"{python_to_typescript_type(non_null_type)} | null"
        # Union型の処理
        union_types = [python_to_typescript_type(arg) for arg in args]
        return " | ".join(union_types)

    # カスタムクラスやEnumの場合
    if hasattr(py_type, "__name__"):
        return py_type.__name__

    return "unknown"


def generate_interface(model_class) -> str:
    """Pydanticモデルクラスから TypeScript interface を生成"""
    interface_name = model_class.__name__

    # クラスのフィールドを取得
    if hasattr(model_class, "__annotations__"):
        annotations = model_class.__annotations__
    else:
        annotations = {}

    # PaginatedResponseの特別処理
    generic_params = ""
    if interface_name == "PaginatedResponse":
        generic_params = "<T = unknown>"

    # インターフェース開始
    lines = [f"export interface {interface_name}{generic_params} {{"]

    for field_name, field_type in annotations.items():
        # Optionalフィールドかどうかチェック
        is_optional = False
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union and len(args) == 2 and type(None) in args:
            is_optional = True

        # PaginatedResponseのitemsフィールドの特別処理
        if interface_name == "PaginatedResponse" and field_name == "items":
            ts_type = "T[]"
        else:
            ts_type = python_to_typescript_type(field_type)

        optional_marker = "?" if is_optional else ""

        lines.append(f"  {field_name}{optional_marker}: {ts_type}")

    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def generate_enum(enum_class) -> str:
    """Python Enum から TypeScript enum を生成"""
    enum_name = enum_class.__name__

    lines = [f"export enum {enum_name} {{"]

    for member in enum_class:
        # 文字列の場合は引用符で囲む
        if isinstance(member.value, str):
            lines.append(f"  {member.name} = '{member.value}',")
        else:
            lines.append(f"  {member.name} = {member.value},")

    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def main():
    """メイン処理"""
    print("=== 簡易型生成テスト ===")

    try:
        # models.py をインポート
        from pydantic import BaseModel

        import src.web.models as models

        output_lines = []

        # ファイルヘッダー
        output_lines.append("/**")
        output_lines.append(" * 自動生成されたAPI型定義（簡易版）")
        output_lines.append(" * 注意: このファイルは自動生成されます。直接編集しないでください。")
        output_lines.append(" */")
        output_lines.append("")

        # 全ての型を取得
        for name in dir(models):
            obj = getattr(models, name)

            # Enumの処理（基底Enumクラスは除外）
            if (
                isinstance(obj, type)
                and issubclass(obj, Enum)
                and obj != Enum
                and hasattr(obj, "__members__")
                and obj.__members__
            ):
                print(f"Enum発見: {name}")
                output_lines.append(generate_enum(obj))

            # Pydanticモデルの処理
            elif isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel:
                print(f"Pydanticモデル発見: {name}")
                output_lines.append(generate_interface(obj))

        # ファイルに出力（api.tsとapi.generated.tsの両方）
        output_file = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "api.ts"
        backup_file = PROJECT_ROOT.parent / "frontend" / "src" / "types" / "api.generated.ts"

        # ディレクトリ作成
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 両方のファイルに書き込み
        content = "\n".join(output_lines)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 型定義を生成しました: {output_file}")
        print(f"✅ バックアップを作成しました: {backup_file}")
        print(f"ファイルサイズ: {output_file.stat().st_size} bytes")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Union型のインポート
    from typing import Union

    main()
