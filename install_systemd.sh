#!/bin/bash

# Twix Saver systemd サービスインストールスクリプト

set -e

# 色付きメッセージ用の関数
print_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# 実行権限チェック
if [ "$EUID" -eq 0 ]; then
    print_error "このスクリプトはrootで実行しないでください"
    exit 1
fi

# プロジェクトルートディレクトリを取得
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="$(whoami)"
GROUP_NAME="$(id -gn)"

print_info "Twix Saver systemd サービスをインストールします..."
print_info "プロジェクトルート: $PROJECT_ROOT"
print_info "実行ユーザー: $USER_NAME"
print_info "実行グループ: $GROUP_NAME"

# 必要なディレクトリの存在確認
if [ ! -f "$PROJECT_ROOT/backend/main.py" ]; then
    print_error "main.py が見つかりません: $PROJECT_ROOT/backend/"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    print_error "venv ディレクトリが見つかりません: $PROJECT_ROOT/venv"
    print_error "先に backend/setup_env.sh を実行してください"
    exit 1
fi

# .env ファイルの確認
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    print_warning "backend/.env ファイルが見つかりません"
    print_warning "systemd サービス実行前に必要な環境変数を設定してください"
fi

# 新しいデータベース駆動モードの説明
print_info "データベース駆動モードを使用します"
print_info "WebUI (http://localhost:5173) からジョブを作成してください"

# systemdファイルのコピーと編集
print_info "systemd サービスファイルを設定中..."

# ユーザーのsystemdディレクトリを作成
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

# テンプレートファイルをコピーして編集
for service_file in twix-scraper.service twix-scraper.timer twix-ingest.service twix-ingest.timer twix-types-watch.service twix-types-generate.service twix-types-generate.timer; do
    print_info "設定中: $service_file"
    
    # テンプレートをコピー
    cp "$PROJECT_ROOT/backend/systemd/$service_file" "$USER_SYSTEMD_DIR/"
    
    # パス置換
    sed -i.bak \
        -e "s|your-user|$USER_NAME|g" \
        -e "s|your-group|$GROUP_NAME|g" \
        -e "s|/path/to/project|$PROJECT_ROOT|g" \
        "$USER_SYSTEMD_DIR/$service_file"
    
    # バックアップファイルを削除
    rm -f "$USER_SYSTEMD_DIR/$service_file.bak"
done

# systemd デーモンリロード
print_info "systemd デーモンをリロード中..."
systemctl --user daemon-reload

print_info "サービスの状態確認..."
systemctl --user status twix-scraper.service --no-pager || true
systemctl --user status twix-ingest.service --no-pager || true

# サービス有効化の確認
echo ""
read -p "サービスを有効化して開始しますか？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "タイマーサービスを有効化中..."
    
    systemctl --user enable twix-scraper.timer
    systemctl --user enable twix-ingest.timer
    
    systemctl --user start twix-scraper.timer
    systemctl --user start twix-ingest.timer
    
    print_info "サービスが正常に開始されました"
    
    echo ""
    echo "=== 次のコマンドでサービスを管理できます ==="
    echo "状態確認:"
    echo "  systemctl --user status twix-scraper.timer"
    echo "  systemctl --user status twix-ingest.timer"
    echo ""
    echo "ログ確認:"
    echo "  journalctl --user -u twix-scraper.service -f"
    echo "  journalctl --user -u twix-ingest.service -f"
    echo ""
    echo "サービス停止:"
    echo "  systemctl --user stop twix-scraper.timer"
    echo "  systemctl --user stop twix-ingest.timer"
    echo ""
    echo "手動実行:"
    echo "  systemctl --user start twix-scraper.service"
    echo "  systemctl --user start twix-ingest.service"
    echo ""
else
    print_info "サービスファイルのインストールが完了しました"
    print_info "後で以下のコマンドでサービスを開始してください:"
    echo "  systemctl --user enable --now twix-scraper.timer"
    echo "  systemctl --user enable --now twix-ingest.timer"
fi

echo ""
print_info "インストールが完了しました！"