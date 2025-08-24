#!/bin/bash

# X.com スクレイピングボット環境セットアップスクリプト
# Python 3.9+ が必要

set -e

echo "🚀 X.com スクレイピングボット環境をセットアップしています..."

# Python バージョンチェック
python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "✅ Python $python_version が見つかりました (3.9以上が必要)"
else
    echo "❌ Python 3.9以上が必要です。現在のバージョン: $python_version"
    exit 1
fi

# venv 環境作成
if [ ! -d "venv" ]; then
    echo "📦 Python仮想環境を作成しています..."
    python3 -m venv venv
    echo "✅ venv環境が作成されました"
else
    echo "✅ venv環境は既に存在します"
fi

# venv環境をアクティベート
echo "🔧 venv環境をアクティベートしています..."
source venv/bin/activate

# pip を最新版にアップグレード
echo "⬆️ pip を最新版にアップグレードしています..."
pip install --upgrade pip

# 依存関係をインストール
echo "📚 依存パッケージをインストールしています..."
pip install -r requirements.txt

# Playwright ブラウザをインストール
echo "🌐 Playwright ブラウザをインストールしています..."
playwright install

# Playwright システム依存関係をインストール (Linux用)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Linux システム依存関係をインストールしています..."
    playwright install-deps
fi

# プロジェクト構造を作成
echo "📁 プロジェクト構造を作成しています..."
mkdir -p src/scrapers
mkdir -p src/utils
mkdir -p data/raw
mkdir -p data/processed
mkdir -p logs
mkdir -p config

# .env テンプレートファイルを作成
if [ ! -f ".env" ]; then
    echo "⚙️ 設定ファイル(.env)のテンプレートを作成しています..."
    cat > .env << 'EOF'
# X.com スクレイピング設定

# MongoDB 接続設定
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=twitter_scraper

# プロキシ設定（レジデンシャルプロキシ推奨）
PROXY_SERVER=
PROXY_USERNAME=
PROXY_PASSWORD=

# X.com 認証情報（使い捨てアカウント用）
TWITTER_USERNAME=
TWITTER_PASSWORD=
TWITTER_EMAIL=

# CAPTCHA 解決サービス（オプション）
CAPTCHA_SERVICE_API_KEY=

# スクレイピング設定
SCRAPING_INTERVAL_MINUTES=15
RANDOM_DELAY_MAX_SECONDS=120
MAX_TWEETS_PER_SESSION=100

# ログレベル
LOG_LEVEL=INFO
EOF
    echo "✅ .env テンプレートが作成されました"
    echo "⚠️  .envファイルを編集して、必要な設定値を入力してください"
else
    echo "✅ .envファイルは既に存在します"
fi

echo ""
echo "🎉 セットアップが完了しました！"
echo ""
echo "次のステップ:"
echo "1. .envファイルを編集して設定を行ってください"
echo "2. venv環境をアクティベート: source venv/bin/activate"
echo "3. スクレイピングスクリプトを実行してください"
echo ""