#!/bin/bash
"""
型定義自動化システムのセットアップスクリプト
systemdサービスの設定とnpm scriptsの統合
"""

set -e

# プロジェクトディレクトリの設定
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="$PROJECT_ROOT/systemd"
SYSTEMD_SYSTEM_DIR="/etc/systemd/system"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_requirements() {
    log "必要な依存関係をチェック中..."
    
    # Python3の確認
    if ! command -v python3 &> /dev/null; then
        log "❌ python3 が見つかりません"
        exit 1
    fi
    
    # pip パッケージの確認とインストール
    python3 -c "import pydantic_to_typescript" 2>/dev/null || {
        log "pydantic-to-typescript をインストール中..."
        pip3 install pydantic-to-typescript>=2.0.0
    }
    
    python3 -c "import watchdog" 2>/dev/null || {
        log "watchdog をインストール中..."
        pip3 install watchdog
    }
    
    log "✅ 依存関係チェック完了"
}

setup_systemd_services() {
    log "systemdサービスをセットアップ中..."
    
    # 権限チェック
    if [[ $EUID -ne 0 ]]; then
        log "❌ systemdサービスのインストールには管理者権限が必要です"
        log "このスクリプトを sudo で実行してください"
        exit 1
    fi
    
    # サービスファイルをコピー
    for service_file in "$SYSTEMD_DIR"/*.service "$SYSTEMD_DIR"/*.timer; do
        if [[ -f "$service_file" ]]; then
            filename=$(basename "$service_file")
            log "コピー中: $filename"
            cp "$service_file" "$SYSTEMD_SYSTEM_DIR/"
        fi
    done
    
    # systemdの設定を再読み込み
    log "systemd設定を再読み込み中..."
    systemctl daemon-reload
    
    # サービスを有効化
    log "サービスを有効化中..."
    systemctl enable twix-types-generate.timer
    systemctl enable twix-types-watch.service
    
    # サービスを開始
    log "サービスを開始中..."
    systemctl start twix-types-generate.timer
    systemctl start twix-types-watch.service
    
    log "✅ systemdサービスのセットアップ完了"
}

setup_development_mode() {
    log "開発モードのセットアップ中..."
    
    # ファイル監視サービスをフォアグラウンドで開始
    log "開発用ファイル監視を開始..."
    log "Pydanticモデルファイルの変更を監視します (Ctrl+C で停止)"
    
    cd "$PROJECT_ROOT"
    python3 scripts/watch-models.py
}

test_type_generation() {
    log "型定義生成のテスト中..."
    
    cd "$PROJECT_ROOT"
    
    # 型定義を生成
    python3 scripts/generate-types.py
    
    # 同期チェック
    python3 scripts/check-type-sync.py
    
    log "✅ 型定義生成テスト完了"
}

show_status() {
    log "型定義自動化システムの状態:"
    
    if command -v systemctl &> /dev/null; then
        echo ""
        echo "== systemd サービス状態 =="
        systemctl status twix-types-generate.timer --no-pager -l || true
        systemctl status twix-types-watch.service --no-pager -l || true
    fi
    
    echo ""
    echo "== ファイル状態 =="
    ls -la "$PROJECT_ROOT/../frontend/src/types/" || true
}

show_help() {
    echo "使用法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  install-system    systemdサービスとしてインストール (要sudo)"
    echo "  dev-mode         開発モード (フォアグラウンドでファイル監視)"
    echo "  test             型定義生成をテスト"
    echo "  status           システム状態を表示"
    echo "  help             このヘルプを表示"
    echo ""
    echo "例:"
    echo "  sudo $0 install-system"
    echo "  $0 dev-mode"
    echo "  $0 test"
}

main() {
    case "${1:-help}" in
        "install-system")
            check_requirements
            setup_systemd_services
            ;;
        "dev-mode")
            check_requirements  
            setup_development_mode
            ;;
        "test")
            check_requirements
            test_type_generation
            ;;
        "status")
            show_status
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

main "$@"